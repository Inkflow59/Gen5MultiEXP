"""Patch overlay code inside a Nintendo DS ROM without rebuilding the whole file.

The patched overlay is recompressed and written back into its original file slot when it fits (the usual
case, since a small edit barely changes the compressed size). Otherwise it is stored uncompressed in the unused
0xFF area after the ROM's used size. Either way only the FAT entry, the overlay table entry and, for the fallback,
the header (used size and CRC16) change, so the output keeps its size and the BPS patch stays small.
"""
from __future__ import annotations

import shutil
import struct
from dataclasses import dataclass
from pathlib import Path

import ndspy.codeCompression

OVERLAY_ENTRY_SIZE = 32
FLAG_COMPRESSED = 0x01000000
SIZE_MASK = 0x00FFFFFF
ALIGN = 0x200


class PatchError(Exception):
    """Base class for patching problems."""


class OutOfSpaceError(PatchError):
    """The edit lies outside its overlay, or there is no free space left to store the patched overlay."""


class OverwriteError(PatchError):
    """The bytes being replaced are not the ones expected (wrong ROM version, or already patched)."""


@dataclass(frozen=True)
class Edit:
    overlay_id: int
    ram_addr: int
    data: bytes
    expected: bytes


def header_crc16(header: bytes) -> int:
    """CRC16 (poly 0xA001, init 0xFFFF) over header bytes 0..0x15D."""
    crc = 0xFFFF
    for b in header[:0x15E]:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def _align(value: int) -> int:
    return (value + ALIGN - 1) & ~(ALIGN - 1)


def _load_overlay(f, header: bytes, overlay_id: int):
    """Return (ram_addr, decompressed code, overlay table entry, entry position, FAT entry position)."""
    fat_off = struct.unpack_from("<I", header, 0x48)[0]
    ovt_off, ovt_size = struct.unpack_from("<II", header, 0x50)
    if (overlay_id + 1) * OVERLAY_ENTRY_SIZE > ovt_size:
        raise PatchError(f"overlay {overlay_id} not in the overlay table")
    entry_pos = ovt_off + overlay_id * OVERLAY_ENTRY_SIZE
    f.seek(entry_pos)
    entry = list(struct.unpack("<8I", f.read(OVERLAY_ENTRY_SIZE)))
    fat_pos = fat_off + entry[6] * 8
    f.seek(fat_pos)
    start, end = struct.unpack("<II", f.read(8))
    f.seek(start)
    raw = f.read(end - start)
    code = ndspy.codeCompression.decompress(raw) if entry[7] & FLAG_COMPRESSED else raw
    return entry[1], bytearray(code), entry, entry_pos, fat_pos


def _compress_if_it_fits(code: bytearray, entry: list, f, fat_pos: int):
    """Recompress `code`; return (data, slot_start, slot_end) when it fits the overlay's current file slot."""
    f.seek(fat_pos)
    slot_start, slot_end = struct.unpack("<II", f.read(8))
    packed = ndspy.codeCompression.compress(bytes(code), False)
    if len(packed) > slot_end - slot_start or ndspy.codeCompression.decompress(packed) != bytes(code):
        return None
    return packed, slot_start, slot_end


def read_overlay(path: Path, overlay_id: int) -> tuple[int, bytes]:
    """Return (RAM address, decompressed bytes) of an overlay."""
    with Path(path).open("rb") as f:
        header = f.read(0x200)
        ram_addr, code, *_ = _load_overlay(f, header, overlay_id)
    return ram_addr, bytes(code)


def patch_rom(src: Path, dst: Path, edits: list[Edit]) -> None:
    """Copy `src` to `dst` and apply `edits`; `dst` is removed again if anything fails."""
    dst = Path(dst)
    shutil.copyfile(src, dst)
    try:
        _apply(dst, edits)
    except BaseException:
        dst.unlink(missing_ok=True)
        raise


def _apply(path: Path, edits: list[Edit]) -> None:
    with path.open("r+b") as f:
        header = bytearray(f.read(0x200))
        used = struct.unpack_from("<I", header, 0x80)[0]
        total = f.seek(0, 2)

        by_overlay: dict[int, list[Edit]] = {}
        for edit in edits:
            by_overlay.setdefault(edit.overlay_id, []).append(edit)

        for overlay_id, group in by_overlay.items():
            ram_addr, code, entry, entry_pos, fat_pos = _load_overlay(f, header, overlay_id)
            flags = entry[7]

            for edit in group:
                lo = edit.ram_addr - ram_addr
                hi = lo + len(edit.data)
                if lo < 0 or hi > len(code) or len(edit.expected) != len(edit.data):
                    raise OutOfSpaceError(
                        f"edit at {edit.ram_addr:#x}+{len(edit.data)} is outside overlay {overlay_id}")
                if bytes(code[lo:hi]) != edit.expected:
                    raise OverwriteError(
                        f"overlay {overlay_id} at {edit.ram_addr:#x}: found {bytes(code[lo:hi]).hex()}, "
                        f"expected {edit.expected.hex()}")
                code[lo:hi] = edit.data

            packed = _compress_if_it_fits(code, entry, f, fat_pos) if flags & FLAG_COMPRESSED else None
            if packed is not None:
                slot_start, slot_end = packed[1], packed[2]
                f.seek(slot_start)
                f.write(packed[0] + b"\xFF" * (slot_end - slot_start - len(packed[0])))
                f.seek(fat_pos)
                f.write(struct.pack("<II", slot_start, slot_start + len(packed[0])))
                entry[7] = (flags & 0xFE000000) | FLAG_COMPRESSED | len(packed[0])
                f.seek(entry_pos)
                f.write(struct.pack("<8I", *entry))
                continue

            new_start = _align(used)
            new_end = new_start + len(code)
            if new_end > total:
                raise OutOfSpaceError("not enough room after the used area of the ROM")
            f.seek(new_start)
            if f.read(len(code)) != b"\xFF" * len(code):
                raise OutOfSpaceError("the area after the used ROM size is not free (not all 0xFF)")
            f.seek(new_start)
            f.write(code)
            f.seek(fat_pos)
            f.write(struct.pack("<II", new_start, new_end))
            entry[7] = (flags & 0xFE000000 & ~FLAG_COMPRESSED) | len(code)
            f.seek(entry_pos)
            f.write(struct.pack("<8I", *entry))
            used = new_end

        struct.pack_into("<I", header, 0x80, _align(used))
        struct.pack_into("<H", header, 0x15E, header_crc16(bytes(header)))
        f.seek(0)
        f.write(header)
