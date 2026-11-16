"""Build the BPS patch for a clean ROM."""
from __future__ import annotations

import tempfile
from pathlib import Path

from . import bps, multi_exp, patcher, rom


def patch_name(spec: rom.RomSpec) -> str:
    return f"{spec.slug}-multi-exp.bps"


def build_patch(clean_rom: Path, out_bps: Path, layout: multi_exp.Layout | None = None) -> Path:
    """Patch `clean_rom` in a temporary file, diff it against the original, and write the BPS file.

    Raises rom.WrongRomError unless `clean_rom` is one of the known clean ROMs, and patcher.OverwriteError
    if the code at the hook site is not the expected original code.
    """
    clean_rom, out_bps = Path(clean_rom), Path(out_bps)
    spec = rom.identify(clean_rom)
    layout = layout or multi_exp.LAYOUTS[spec.game_code]

    ram_addr, code = patcher.read_overlay(clean_rom, layout.overlay_id)
    original = multi_exp.check_original(layout, ram_addr, code)
    edits = multi_exp.build(layout, original)

    with tempfile.TemporaryDirectory() as tmp:
        patched_path = Path(tmp) / "patched.nds"
        patcher.patch_rom(clean_rom, patched_path, edits)
        source = clean_rom.read_bytes()
        target = patched_path.read_bytes()
    patch = bps.create(source, target)
    if bps.apply(source, patch) != target:
        raise patcher.PatchError("internal error: the BPS patch does not reproduce the patched ROM")
    out_bps.parent.mkdir(parents=True, exist_ok=True)
    out_bps.write_bytes(patch)
    return out_bps
