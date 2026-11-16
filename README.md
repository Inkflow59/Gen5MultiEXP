# Gen5MultiEXP

A patch that brings the always-on "Exp. Share" of Gen 6/7 to Pokemon Black/White and Black 2/White 2 (Gen 5).
Every living party member earns EXP: participants as usual, the others 50% of that amount (then the Gen 5 level
scaling applies to each Pokemon as usual).

**No ROM is stored in this repository.** The patches are BPS files that apply to a clean dump of your own cartridge.

## Patches

| Game | Game code | Patch | Tested in an emulator |
|------|-----------|-------|-----------------------|
| Pokemon Version Noire 2 (FR) | `IREF` | `patches/black2-fr-multi-exp.bps` | yes (melonDS) |
| Pokemon Version Blanche 2 (FR) | `IRDF` | `patches/white2-fr-multi-exp.bps` | no |
| Pokemon Black Version 2 (USA, Europe) | `IREO` | `patches/black2-us-multi-exp.bps` | no |
| Pokemon White Version 2 (USA, Europe) | `IRDO` | `patches/white2-us-multi-exp.bps` | no |
| Pokemon Version Noire (FR) | `IRBF` | `patches/black-fr-multi-exp.bps` | no |
| Pokemon Version Blanche (FR) | `IRAF` | `patches/white-fr-multi-exp.bps` | no |
| Pokemon Black Version (USA, Europe) | `IRBO` | `patches/black-us-multi-exp.bps` | no |
| Pokemon White Version (USA, Europe) | `IRAO` | `patches/white-us-multi-exp.bps` | no |

The untested ones are built the same way and pass the automated checks (the routine is run in an emulated CPU for
every game and the patched code is compared with the original), but they have not been played.

## Usage

```
python tools/apply_patch.py "Pokémon - Version Noire 2.nds" patches/black2-fr-multi-exp.bps Noire2_multiexp.nds
```

The ROM must be the clean dump of the matching game (the patch checks it and refuses anything else, including an
already patched ROM). Copy your save next to the patched ROM with the same base name.
To rebuild the patches from the ROMs placed in the repository root: `python tools/build_patches.py`.
Run the tests with `python -m pytest -q` (tests that need a ROM are skipped when it is missing).
See `docs/TESTING.md` for the manual emulator checklist.

See `docs/superpowers/specs/` for the design and `docs/superpowers/plans/` for the plan.
