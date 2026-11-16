"""Shared fixtures: a tiny synthetic NDS-like image so patcher tests do not need the real ROM."""
import struct

import ndspy.codeCompression
import pytest

OV_RAM = 0x02100000
OV_ID = 0
TOTAL_SIZE = 0x20000
OVT_OFF, FAT_OFF, FILE_OFF = 0x200, 0x400, 0x600


def overlay_payload() -> bytes:
    # Repetitive so BLZ compresses it, with a recognisable marker.
    return (b"\x11\x22\x33\x44" * 32) + b"MARKER__" + (b"\xAA\xBB" * 40)


def build_fake_rom(compressed: bool = True) -> bytes:
    rom = bytearray(b"\xFF" * TOTAL_SIZE)
    rom[0:0x200] = b"\0" * 0x200
    rom[0x0C:0x10] = b"IREF"
    payload = overlay_payload()
    stored = ndspy.codeCompression.compress(payload, False) if compressed else payload
    flags = len(stored) | (0x01000000 if compressed else 0) | 0x02000000
    rom[OVT_OFF:OVT_OFF + 32] = struct.pack("<8I", OV_ID, OV_RAM, len(payload), 0, 0, 0, 0, flags)
    rom[FAT_OFF:FAT_OFF + 8] = struct.pack("<II", FILE_OFF, FILE_OFF + len(stored))
    rom[FILE_OFF:FILE_OFF + len(stored)] = stored
    used = (FILE_OFF + len(stored) + 0x1FF) & ~0x1FF
    rom[used:TOTAL_SIZE] = b"\xFF" * (TOTAL_SIZE - used)
    struct.pack_into("<II", rom, 0x48, FAT_OFF, 8)
    struct.pack_into("<II", rom, 0x50, OVT_OFF, 32)
    struct.pack_into("<I", rom, 0x80, used)
    struct.pack_into("<H", rom, 0x15E, crc16(bytes(rom[0:0x15E])))
    return bytes(rom)


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


@pytest.fixture
def fake_rom_path(tmp_path):
    p = tmp_path / "fake.nds"
    p.write_bytes(build_fake_rom())
    return p
