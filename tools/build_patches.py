"""Build the Multi EXP BPS patch for each clean ROM found next to this repository (or the ones given).

python tools/build_patches.py                 # every known ROM in the repository root
python tools/build_patches.py "path/to.nds"   # specific ROMs
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from gen5multiexp import build, rom  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("roms", nargs="*", type=Path)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "patches")
    args = parser.parse_args()

    candidates = args.roms or sorted(ROOT.glob("*.nds"))
    built = 0
    for path in candidates:
        try:
            spec = rom.identify(path)
        except rom.WrongRomError as exc:
            print(f"skip {path.name}: {exc}")
            continue
        out = build.build_patch(path, args.out_dir / build.patch_name(spec))
        print(f"{spec.game_code} {spec.title}: wrote {out.name} ({out.stat().st_size} bytes)")
        built += 1
    return 0 if built else 1


if __name__ == "__main__":
    raise SystemExit(main())
