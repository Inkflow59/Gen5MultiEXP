"""End to end checks on the real ROMs (skipped for the ROMs that are not present)."""
import struct
from pathlib import Path

import pytest

from gen5multiexp import bps, build, multi_exp, patcher, rom

ROOT = Path(__file__).resolve().parent.parent


def _find_roms() -> dict[str, Path]:
    found = {}
    for path in sorted(ROOT.glob("*.nds")):
        try:
            with path.open("rb") as f:
                code = f.read(16)[12:16].decode("ascii", errors="replace")
        except OSError:
            continue
        if code in rom.KNOWN_ROMS:
            found[code] = path
    return found


ROMS = _find_roms()
CODES = sorted(rom.KNOWN_ROMS)
needs_rom = lambda code: pytest.mark.skipif(code not in ROMS, reason=f"{code} ROM not present")  # noqa: E731


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    cache = {}

    def get(code):
        if code not in cache:
            out = tmp_path_factory.mktemp(code) / "a.bps"
            build.build_patch(ROMS[code], out)
            cache[code] = out
        return cache[code]
    return get


@pytest.mark.parametrize("code", [pytest.param(c, marks=needs_rom(c)) for c in CODES])
def test_patch_applies_to_the_clean_rom_and_only_to_it(built, code):
    source = ROMS[code].read_bytes()
    patch = built(code).read_bytes()
    result = bps.apply(source, patch)
    assert len(result) == len(source) and result != source
    changed = bytearray(source)
    changed[0x1000] ^= 0xFF
    with pytest.raises(bps.PatchError):
        bps.apply(bytes(changed), patch)
    with pytest.raises(bps.PatchError):
        bps.apply(result, patch)  # applying twice is refused


@pytest.mark.parametrize("code", [pytest.param(c, marks=needs_rom(c)) for c in CODES])
def test_only_the_overlay_slot_and_its_table_entries_differ(built, code):
    L = multi_exp.LAYOUTS[code]
    source = ROMS[code].read_bytes()
    result = bps.apply(source, built(code).read_bytes())
    header = source[:0x200]
    ovt_off = struct.unpack_from("<I", header, 0x50)[0]
    fat_off = struct.unpack_from("<I", header, 0x48)[0]
    entry_pos = ovt_off + L.overlay_id * 32
    entry = struct.unpack_from("<8I", source, entry_pos)
    slot_start, slot_end = struct.unpack_from("<II", source, fat_off + entry[6] * 8)
    allowed = [(entry_pos, entry_pos + 32), (fat_off + entry[6] * 8, fat_off + entry[6] * 8 + 8),
               (slot_start, slot_end)]
    assert result[:0x200] == source[:0x200], "the header must not change when the overlay fits its slot"
    pos = 0
    while pos < len(source):
        end = min(pos + (1 << 20), len(source))
        if source[pos:end] != result[pos:end]:
            for i in range(pos, end):
                if source[i] != result[i]:
                    assert any(lo <= i < hi for lo, hi in allowed), f"unexpected change at {i:#x}"
        pos = end


@pytest.mark.parametrize("code", [pytest.param(c, marks=needs_rom(c)) for c in CODES])
def test_patched_overlay_contains_the_new_routine(built, code, tmp_path):
    L = multi_exp.LAYOUTS[code]
    out = tmp_path / "patched.nds"
    out.write_bytes(bps.apply(ROMS[code].read_bytes(), built(code).read_bytes()))
    ram, data = patcher.read_overlay(out, L.overlay_id)
    lo = L.region_start - ram
    assert data[lo:lo + L.region_size] == multi_exp.code(L)
    ref_ram, ref = patcher.read_overlay(ROMS[code], L.overlay_id)
    assert data[:lo] == ref[:lo] and data[lo + L.region_size:] == ref[lo + L.region_size:]


@needs_rom("IREF")
def test_build_is_deterministic(built, tmp_path):
    second = tmp_path / "b.bps"
    build.build_patch(ROMS["IREF"], second)
    assert second.read_bytes() == built("IREF").read_bytes()


@pytest.mark.parametrize("code", [pytest.param(c, marks=needs_rom(c)) for c in CODES])
def test_every_layout_matches_its_real_rom(code):
    L = multi_exp.LAYOUTS[code]
    ram, data = patcher.read_overlay(ROMS[code], L.overlay_id)
    assert len(multi_exp.check_original(L, ram, data)) == L.region_size


def test_wrong_rom_is_refused(tmp_path):
    other = tmp_path / "other.nds"
    data = bytearray(0x400)
    data[12:16] = b"IRBF"
    other.write_bytes(bytes(data))
    with pytest.raises(rom.WrongRomError):
        build.build_patch(other, tmp_path / "x.bps")


@needs_rom("IREF")
def test_a_layout_of_another_rom_is_refused(tmp_path):
    wrong = multi_exp.LAYOUTS["IRBF"]  # Black 1 addresses applied to the Black 2 ROM
    with pytest.raises((patcher.OverwriteError, patcher.PatchError)):
        build.build_patch(ROMS["IREF"], tmp_path / "x.bps", layout=wrong)
