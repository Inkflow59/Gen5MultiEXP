# Gen 5 Multi EXP

A patch that brings the always-on "Exp. Share" of Gen 6/7 to Pokemon Black/White and Black 2/White 2 (Gen 5).
Every living party member earns EXP: participants as usual, the others the same amount, i.e. 100% EXP for the
whole team (then the Gen 5 level scaling applies to each Pokemon as usual).

**No ROM is stored in this repository.** The patches are BPS files that apply to a clean dump of your own cartridge.

## Patches

### FR

| Game | Game code | Patch |
|------|-----------|-------|
| Pokemon Version Noire (FR) | `IRBF` | `patches/black-fr-multi-exp.bps` |
| Pokemon Version Blanche (FR) | `IRAF` | `patches/white-fr-multi-exp.bps` |
| Pokemon Version Noire 2 (FR) | `IREF` | `patches/black2-fr-multi-exp.bps` |
| Pokemon Version Blanche 2 (FR) | `IRDF` | `patches/white2-fr-multi-exp.bps` |

### US/EU

| Game | Game code | Patch |
|------|-----------|-------|
| Pokemon Black Version (USA, Europe) | `IRBO` | `patches/black-us-multi-exp.bps` |
| Pokemon White Version (USA, Europe) | `IRAO` | `patches/white-us-multi-exp.bps` |
| Pokemon Black Version 2 (USA, Europe) | `IREO` | `patches/black2-us-multi-exp.bps` |
| Pokemon White Version 2 (USA, Europe) | `IRDO` | `patches/white2-us-multi-exp.bps` |

### ES

| Game | Game code | Patch |
|------|-----------|-------|
| Pokemon Edicion Negra (ES) | `IRBS` | `patches/black-es-multi-exp.bps` |
| Pokemon Edicion Blanca (ES) | `IRAS` | `patches/white-es-multi-exp.bps` |
| Pokemon Edicion Negra 2 (ES) | `IRES` | `patches/black2-es-multi-exp.bps` |
| Pokemon Edicion Blanca 2 (ES) | `IRDS` | `patches/white2-es-multi-exp.bps` |

### IT

| Game | Game code | Patch |
|------|-----------|-------|
| Pokemon Versione Nera (IT) | `IRBI` | `patches/black-it-multi-exp.bps` |
| Pokemon Versione Bianca (IT) | `IRAI` | `patches/white-it-multi-exp.bps` |
| Pokemon Versione Nera 2 (IT) | `IREI` | `patches/black2-it-multi-exp.bps` |
| Pokemon Versione Bianca 2 (IT) | `IRDI` | `patches/white2-it-multi-exp.bps` |

### DE

| Game | Game code | Patch |
|------|-----------|-------|
| Pokemon Schwarze Edition (DE) | `IRBD` | `patches/black-de-multi-exp.bps` |
| Pokemon Weisse Edition (DE) | `IRAD` | `patches/white-de-multi-exp.bps` |
| Pokemon Schwarze Edition 2 (DE) | `IRED` | `patches/black2-de-multi-exp.bps` |
| Pokemon Weisse Edition 2 (DE) | `IRDD` | `patches/white2-de-multi-exp.bps` |

### JP

| Game | Game code | Patch |
|------|-----------|-------|
| Pocket Monsters Black (JP) | `IRBJ` | `patches/black-jp-multi-exp.bps` |
| Pocket Monsters White (JP) | `IRAJ` | `patches/white-jp-multi-exp.bps` |
| Pocket Monsters Black 2 (JP, Rev 1) | `IREJ` | `patches/black2-jp-multi-exp.bps` |
| Pocket Monsters White 2 (JP, Rev 1) | `IRDJ` | `patches/white2-jp-multi-exp.bps` |

### KR

| Game | Game code | Patch |
|------|-----------|-------|
| Pocket Monsters Black (KR) | `IRBK` | `patches/black-kr-multi-exp.bps` |
| Pocket Monsters White (KR) | `IRAK` | `patches/white-kr-multi-exp.bps` |
| Pocket Monsters Black 2 (KR) | `IREK` | `patches/black2-kr-multi-exp.bps` |
| Pocket Monsters White 2 (KR) | `IRDK` | `patches/white2-kr-multi-exp.bps` |

Only the French Black 2 (`IREF`) has been played in an emulator (melonDS). The others are built the same way and pass the
automated checks (the routine is run in an emulated CPU for every game and the patched code is compared with the original),
but they have not been played.

## Usage

```
python tools/apply_patch.py "Pokémon - Version Noire 2.nds" patches/black2-fr-multi-exp.bps Noire2_multiexp.nds
```

The ROM must be the clean dump of the matching game (the patch checks it and refuses anything else, including an
already patched ROM). Copy your save next to the patched ROM with the same base name.
To rebuild the patches from the ROMs placed in the repository root: `python tools/build_patches.py`.
Run the tests with `python -m pytest -q` (tests that need a ROM are skipped when it is missing).
See `docs/TESTING.md` for the manual emulator checklist.

## If the patch does not work on a ROM listed as compatible

A ROM marked as compatible can still fail to patch (different dump, header or revision, modified file, tool quirk). If that happens, do not give up. Try one of these instead:

- **Create the patch yourself** from your own ROM, with the tools in this repository.
- **Build the patched ROM directly** instead of applying a patch file.
- **Modify the code** to adapt it to your ROM.
