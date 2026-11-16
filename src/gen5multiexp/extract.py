"""Extract the decompressed ARM9 binary and overlays of a ROM for analysis."""
from __future__ import annotations

import json
from pathlib import Path

import ndspy.codeCompression
import ndspy.rom

from . import rom as rom_mod


def extract(rom_path: Path, out_dir: Path) -> dict:
    """Write arm9.bin, ov/ovNNN.bin and index.json under out_dir; return the index."""
    rom_mod.identify(rom_path)
    out_dir = Path(out_dir)
    (out_dir / "ov").mkdir(parents=True, exist_ok=True)

    nds = ndspy.rom.NintendoDSRom.fromFile(str(rom_path))
    arm9 = ndspy.codeCompression.decompress(bytes(nds.arm9))
    (out_dir / "arm9.bin").write_bytes(arm9)

    overlays = {}
    for ov_id, overlay in nds.loadArm9Overlays().items():
        data = bytes(overlay.data)
        if overlay.compressed:
            data = ndspy.codeCompression.decompress(data)
        (out_dir / "ov" / f"ov{ov_id:03d}.bin").write_bytes(data)
        overlays[ov_id] = {"ram": overlay.ramAddress, "size": len(data)}

    index = {"arm9_ram": nds.arm9RamAddress, "overlays": overlays}
    (out_dir / "index.json").write_text(json.dumps(index, indent=1))
    return index
