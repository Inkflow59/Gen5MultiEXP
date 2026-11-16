import struct
from pathlib import Path

import ndspy.codeCompression
import pytest

from conftest import OV_ID, OV_RAM, TOTAL_SIZE, crc16, overlay_payload
from gen5multiexp import patcher

MARKER_OFF = 128  # offset of b"MARKER__" in the payload
REAL_ROM = Path(__file__).resolve().parent.parent / "Pokémon - Version Noire 2.nds"


def _read_overlay(rom: bytes) -> bytes:
    flags = struct.unpack_from("<I", rom, 0x200 + 0x1C)[0]
    start, end = struct.unpack_from("<II", rom, 0x400)
    raw = rom[start:end]
    return ndspy.codeCompression.decompress(raw) if flags & 0x01000000 else raw


def test_edit_changes_only_the_requested_bytes(fake_rom_path, tmp_path):
    out = tmp_path / "out.nds"
    edit = patcher.Edit(OV_ID, OV_RAM + MARKER_OFF, b"PATCHED!", expected=b"MARKER__")
    patcher.patch_rom(fake_rom_path, out, [edit])
    new = _read_overlay(out.read_bytes())
    old = overlay_payload()
    assert new[MARKER_OFF:MARKER_OFF + 8] == b"PATCHED!"
    assert new[:MARKER_OFF] == old[:MARKER_OFF]
    assert new[MARKER_OFF + 8:] == old[MARKER_OFF + 8:]


def test_rom_size_is_unchanged_and_header_is_consistent(fake_rom_path, tmp_path):
    out = tmp_path / "out.nds"
    patcher.patch_rom(fake_rom_path, out, [patcher.Edit(OV_ID, OV_RAM + MARKER_OFF, b"PATCHED!", b"MARKER__")])
    rom = out.read_bytes()
    assert len(rom) == TOTAL_SIZE
    assert struct.unpack_from("<H", rom, 0x15E)[0] == crc16(rom[0:0x15E])
    used = struct.unpack_from("<I", rom, 0x80)[0]
    start, end = struct.unpack_from("<II", rom, 0x400)
    assert end <= used


def test_wrong_expected_bytes_raise_overwrite_error(fake_rom_path, tmp_path):
    edit = patcher.Edit(OV_ID, OV_RAM + MARKER_OFF, b"PATCHED!", expected=b"NOT_IT__")
    with pytest.raises(patcher.OverwriteError):
        patcher.patch_rom(fake_rom_path, tmp_path / "out.nds", [edit])


def test_edit_outside_the_overlay_raises_out_of_space(fake_rom_path, tmp_path):
    edit = patcher.Edit(OV_ID, OV_RAM + len(overlay_payload()) - 2, b"1234", expected=b"\0\0\0\0")
    with pytest.raises(patcher.OutOfSpaceError):
        patcher.patch_rom(fake_rom_path, tmp_path / "out.nds", [edit])


def test_unknown_overlay_raises(fake_rom_path, tmp_path):
    with pytest.raises(patcher.PatchError):
        patcher.patch_rom(fake_rom_path, tmp_path / "out.nds", [patcher.Edit(5, OV_RAM, b"xx", b"xx")])


INCOMPRESSIBLE = bytes((i * 167 + 13) % 251 for i in range(100))  # defeats BLZ so the overlay cannot stay in its slot


def test_small_edit_keeps_the_overlay_compressed_in_its_original_slot(fake_rom_path, tmp_path):
    out = tmp_path / "out.nds"
    patcher.patch_rom(fake_rom_path, out, [patcher.Edit(OV_ID, OV_RAM + MARKER_OFF, b"PATCHED!", b"MARKER__")])
    rom = out.read_bytes()
    flags = struct.unpack_from("<I", rom, 0x200 + 0x1C)[0]
    start, end = struct.unpack_from("<II", rom, 0x400)
    assert start == 0x600 and flags & 0x01000000 and (flags & 0xFFFFFF) == end - start


def test_overlay_that_no_longer_fits_its_slot_moves_to_the_free_tail_uncompressed(fake_rom_path, tmp_path):
    out = tmp_path / "out.nds"
    expected = overlay_payload()[:100]
    patcher.patch_rom(fake_rom_path, out, [patcher.Edit(OV_ID, OV_RAM, INCOMPRESSIBLE, expected)])
    rom = out.read_bytes()
    flags = struct.unpack_from("<I", rom, 0x200 + 0x1C)[0]
    start, end = struct.unpack_from("<II", rom, 0x400)
    assert not flags & 0x01000000 and start != 0x600 and end - start == len(overlay_payload())
    assert _read_overlay(rom)[:100] == INCOMPRESSIBLE
    assert struct.unpack_from("<H", rom, 0x15E)[0] == crc16(rom[0:0x15E])


def test_no_room_at_the_end_of_the_rom_raises_out_of_space(tmp_path):
    from conftest import build_fake_rom
    data = bytearray(build_fake_rom()[:0x700])
    struct.pack_into("<I", data, 0x80, len(data) - 0x10)
    struct.pack_into("<H", data, 0x15E, crc16(bytes(data[0:0x15E])))
    src = tmp_path / "full.nds"
    src.write_bytes(bytes(data))
    expected = overlay_payload()[:100]
    with pytest.raises(patcher.OutOfSpaceError):
        patcher.patch_rom(src, tmp_path / "o.nds", [patcher.Edit(OV_ID, OV_RAM, INCOMPRESSIBLE, expected)])


@pytest.mark.skipif(not REAL_ROM.exists(), reason="clean ROM not present")
def test_header_crc16_matches_real_rom():
    with REAL_ROM.open("rb") as f:
        h = f.read(0x200)
    assert struct.unpack_from("<H", h, 0x15E)[0] == patcher.header_crc16(h)


@pytest.mark.skipif(not REAL_ROM.exists(), reason="clean ROM not present")
def test_real_rom_overlay_167_edit_leaves_everything_else_identical(tmp_path):
    import ndspy.rom

    before = ndspy.rom.NintendoDSRom.fromFile(str(REAL_ROM))
    ov_before = before.loadArm9Overlays()[167]
    orig = ndspy.codeCompression.decompress(bytes(ov_before.data)) if ov_before.compressed else bytes(ov_before.data)
    addr = 0x021AEE90
    lo = addr - ov_before.ramAddress
    out = tmp_path / "patched.nds"
    patcher.patch_rom(REAL_ROM, out, [patcher.Edit(167, addr, b"\xC0\x46\xC0\x46", orig[lo:lo + 4])])

    after = ndspy.rom.NintendoDSRom.fromFile(str(out))
    ov_after = after.loadArm9Overlays()[167]
    new = ndspy.codeCompression.decompress(bytes(ov_after.data)) if ov_after.compressed else bytes(ov_after.data)
    assert new[lo:lo + 4] == b"\xC0\x46\xC0\x46"
    assert new[:lo] == orig[:lo] and new[lo + 4:] == orig[lo + 4:]
    assert bytes(after.arm9) == bytes(before.arm9)
    for oid in (166, 168, 169):
        assert bytes(after.loadArm9Overlays()[oid].data) == bytes(before.loadArm9Overlays()[oid].data)
    assert out.stat().st_size == REAL_ROM.stat().st_size
