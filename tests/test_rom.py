from pathlib import Path

import pytest

from gen5multiexp import rom

ROOT = Path(__file__).resolve().parent.parent
REAL_ROM = ROOT / "Pokémon - Version Noire 2.nds"


def _fake_rom(path: Path, code: bytes, size: int = 0x200) -> Path:
    data = bytearray(size)
    data[0:12] = b"POKEMON B2\0\0"
    data[12:16] = code
    path.write_bytes(bytes(data))
    return path


def test_read_info_reports_game_code_and_size(tmp_path):
    info = rom.read_info(_fake_rom(tmp_path / "a.nds", b"IRBF"))
    assert info.game_code == "IRBF"
    assert info.size == 0x200
    assert len(info.sha1) == 40


def test_identify_rejects_unknown_game_code(tmp_path):
    with pytest.raises(rom.WrongRomError, match="unknown"):
        rom.identify(_fake_rom(tmp_path / "a.nds", b"ABCD"))


def test_identify_rejects_wrong_size(tmp_path):
    with pytest.raises(rom.WrongRomError, match="size"):
        rom.identify(_fake_rom(tmp_path / "a.nds", b"IREF"))


def test_known_roms_cover_the_eight_games_with_distinct_slugs():
    assert sorted(rom.KNOWN_ROMS) == sorted(
        ["IRBF", "IRAF", "IREF", "IRDF", "IRBO", "IRAO", "IREO", "IRDO"])
    assert len({s.slug for s in rom.KNOWN_ROMS.values()}) == 8


@pytest.mark.skipif(not REAL_ROM.exists(), reason="clean ROM not present")
def test_identify_accepts_real_rom_and_rejects_a_modified_copy(tmp_path):
    spec = rom.identify(REAL_ROM)
    assert spec.game_code == "IREF" and spec.slug == "black2-fr"
    with REAL_ROM.open("rb") as f:
        data = bytearray(f.read(0x1000))
    data[0x800] ^= 0xFF
    # a truncated copy has the wrong size; this checks the size path on a real header
    bad = tmp_path / "bad.nds"
    bad.write_bytes(bytes(data))
    with pytest.raises(rom.WrongRomError):
        rom.identify(bad)
