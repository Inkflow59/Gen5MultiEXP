import os
import random
import zlib

import pytest

from gen5multiexp import bps


def _varint(n):
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(x | 0x80)
            return bytes(out)
        out.append(x)
        n -= 1


def test_roundtrip_small_buffers():
    src = bytes(range(256)) * 4
    tgt = bytearray(src)
    tgt[10:14] = b"ABCD"
    tgt[900] = 0
    patch = bps.create(src, bytes(tgt))
    assert patch[:4] == b"BPS1"
    assert bps.apply(src, patch) == bytes(tgt)


def test_roundtrip_identical_buffers_is_tiny():
    src = os.urandom(5000)
    patch = bps.create(src, src)
    assert len(patch) < 40
    assert bps.apply(src, patch) == src


def test_roundtrip_with_insertions_and_deletions():
    rng = random.Random(1)
    src = bytes(rng.randrange(256) for _ in range(3000))
    tgt = src[:500] + b"INSERTED-BYTES" + src[500:1500] + src[1600:] + b"tail"
    assert bps.apply(src, bps.create(src, tgt)) == tgt


def test_roundtrip_target_longer_and_shorter():
    src = b"a" * 100
    assert bps.apply(src, bps.create(src, b"a" * 150)) == b"a" * 150
    assert bps.apply(src, bps.create(src, b"a" * 40)) == b"a" * 40
    assert bps.apply(b"", bps.create(b"", b"xyz")) == b"xyz"


def test_apply_rejects_wrong_source_crc():
    src = b"hello world" * 10
    patch = bps.create(src, b"hello there" * 10)
    with pytest.raises(bps.PatchError, match="source"):
        bps.apply(b"HELLO world" * 10, patch)


def test_apply_rejects_corrupt_patch():
    src = b"hello world" * 10
    patch = bytearray(bps.create(src, b"hello there" * 10))
    patch[8] ^= 0xFF
    with pytest.raises(bps.PatchError):
        bps.apply(src, bytes(patch))


def test_apply_rejects_non_bps_data():
    with pytest.raises(bps.PatchError):
        bps.apply(b"abc", b"IPS1garbagegarbagegarbage")


def test_apply_supports_source_copy_and_target_copy():
    # Hand-built patch: TargetRead "ab", TargetCopy 2 bytes from target offset 0, SourceCopy 3 bytes from offset 0.
    src = b"XYZ"
    body = bytearray(b"BPS1" + _varint(3) + _varint(7) + _varint(0))
    body += _varint(((2 - 1) << 2) | 1) + b"ab"
    body += _varint(((2 - 1) << 2) | 3) + _varint(0)
    body += _varint(((3 - 1) << 2) | 2) + _varint(0)
    body += zlib.crc32(src).to_bytes(4, "little") + zlib.crc32(b"ababXYZ").to_bytes(4, "little")
    body += zlib.crc32(bytes(body)).to_bytes(4, "little")
    assert bps.apply(src, bytes(body)) == b"ababXYZ"
