"""BPS patch format (byuu's "beat" patches): create and apply."""
from __future__ import annotations

import zlib

MAGIC = b"BPS1"
_BLOCK = 1 << 16
_MIN_EQUAL_RUN = 16


class PatchError(Exception):
    """Raised for a malformed patch or a source file that does not match the patch."""


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(x | 0x80)
            return bytes(out)
        out.append(x)
        n -= 1


def _read_varint(patch: bytes, pos: int) -> tuple[int, int]:
    value, shift = 0, 1
    while True:
        if pos >= len(patch):
            raise PatchError("truncated patch")
        x = patch[pos]
        pos += 1
        value += (x & 0x7F) * shift
        if x & 0x80:
            return value, pos
        shift <<= 7
        value += shift


def _crc(data: bytes) -> bytes:
    return (zlib.crc32(data) & 0xFFFFFFFF).to_bytes(4, "little")


def _equal_run(a: bytes, b: bytes, pos: int, end: int) -> int:
    """Length of the run of equal bytes a[pos:] == b[pos:], capped at `end`."""
    start = pos
    while pos < end:
        step = min(_BLOCK, end - pos)
        if a[pos:pos + step] == b[pos:pos + step]:
            pos += step
            continue
        while a[pos] == b[pos]:
            pos += 1
        break
    return pos - start


def _different_run(a: bytes, b: bytes, pos: int, end: int) -> int:
    """Length of the run from `pos` up to `_MIN_EQUAL_RUN` consecutive equal bytes (or `end`)."""
    start, equal = pos, 0
    while pos < end:
        if a[pos] == b[pos]:
            equal += 1
            if equal >= _MIN_EQUAL_RUN:
                return pos - equal + 1 - start
        else:
            equal = 0
        pos += 1
    return end - start


def create(source: bytes, target: bytes) -> bytes:
    """Create a BPS patch with a simple linear diff (SourceRead for equal runs, TargetRead otherwise)."""
    out = bytearray(MAGIC + _varint(len(source)) + _varint(len(target)) + _varint(0))
    common = min(len(source), len(target))
    pos = 0
    while pos < len(target):
        if pos < common:
            n = _equal_run(source, target, pos, common)
            if n:
                out += _varint(((n - 1) << 2) | 0)
                pos += n
                continue
            n = _different_run(source, target, pos, common)
        else:
            n = len(target) - pos
        out += _varint(((n - 1) << 2) | 1) + target[pos:pos + n]
        pos += n
    out += _crc(source) + _crc(target)
    out += _crc(bytes(out))
    return bytes(out)


def apply(source: bytes, patch: bytes) -> bytes:
    """Apply a BPS patch; raise PatchError when it is malformed or `source` is the wrong file."""
    if len(patch) < 19 or patch[:4] != MAGIC:
        raise PatchError("not a BPS patch")
    if _crc(patch[:-4]) != patch[-4:]:
        raise PatchError("patch checksum mismatch (corrupt patch)")
    pos = 4
    source_size, pos = _read_varint(patch, pos)
    target_size, pos = _read_varint(patch, pos)
    meta_size, pos = _read_varint(patch, pos)
    pos += meta_size
    end = len(patch) - 12
    if source_size != len(source) or _crc(source) != patch[end:end + 4]:
        raise PatchError("source file does not match this patch (wrong ROM or already patched)")

    target = bytearray()
    source_rel = target_rel = 0
    while pos < end:
        data, pos = _read_varint(patch, pos)
        command, length = data & 3, (data >> 2) + 1
        if command == 0:
            offset = len(target)
            if offset + length > len(source):
                raise PatchError("SourceRead out of range")
            target += source[offset:offset + length]
        elif command == 1:
            if pos + length > end:
                raise PatchError("truncated TargetRead")
            target += patch[pos:pos + length]
            pos += length
        else:
            raw, pos = _read_varint(patch, pos)
            delta = -(raw >> 1) if raw & 1 else raw >> 1
            if command == 2:
                source_rel += delta
                if source_rel < 0 or source_rel + length > len(source):
                    raise PatchError("SourceCopy out of range")
                target += source[source_rel:source_rel + length]
                source_rel += length
            else:
                target_rel += delta
                if target_rel < 0 or target_rel >= len(target) + 1:
                    raise PatchError("TargetCopy out of range")
                for _ in range(length):  # may overlap its own output
                    target.append(target[target_rel])
                    target_rel += 1
    if len(target) != target_size or _crc(bytes(target)) != patch[end + 4:end + 8]:
        raise PatchError("result does not match the checksum stored in the patch")
    return bytes(target)
