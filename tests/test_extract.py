import json
from pathlib import Path

import pytest

from gen5multiexp import extract

REAL_ROM = Path(__file__).resolve().parent.parent / "Pokémon - Version Noire 2.nds"


@pytest.mark.skipif(not REAL_ROM.exists(), reason="clean ROM not present")
def test_extract_writes_arm9_and_all_overlays(tmp_path):
    index = extract.extract(REAL_ROM, tmp_path)
    assert (tmp_path / "arm9.bin").stat().st_size == 633888
    assert len(index["overlays"]) == 344
    on_disk = json.loads((tmp_path / "index.json").read_text())
    assert len(on_disk["overlays"]) == 344
    assert index["arm9_ram"] == 0x2000000 or index["arm9_ram"] > 0
    first = next(iter(index["overlays"].values()))
    assert (tmp_path / "ov" / "ov000.bin").exists()
    assert first["size"] > 0
