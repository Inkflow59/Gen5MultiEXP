"""Apply a BPS patch to a ROM: python tools/apply_patch.py ROM.nds PATCH.bps OUT.nds"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from gen5multiexp import bps  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("patch", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    try:
        result = bps.apply(args.rom.read_bytes(), args.patch.read_bytes())
    except bps.PatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    args.out.write_bytes(result)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
