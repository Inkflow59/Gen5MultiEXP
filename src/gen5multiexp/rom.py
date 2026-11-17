"""ROM identity helpers: make sure we only ever touch the clean, known ROMs."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


class WrongRomError(Exception):
    """Raised when a file is not one of the known clean ROMs."""


@dataclass(frozen=True)
class RomInfo:
    game_code: str
    size: int
    sha1: str


@dataclass(frozen=True)
class RomSpec:
    game_code: str
    slug: str       # used in patch file names
    title: str
    size: int
    sha1: str       # SHA-1 of the clean dump
    alt_sha1: tuple[str, ...] = ()   # other known clean dumps of the same game (same code)


KNOWN_ROMS: dict[str, RomSpec] = {s.game_code: s for s in (
    RomSpec("IRBF", "black-fr", "Pokemon Version Noire (French)", 268435456,
            "a559da54839663d8f8f3f03382e5665a61873d22"),
    RomSpec("IRAF", "white-fr", "Pokemon Version Blanche (French)", 268435456,
            "28f075915dd445cbfd902f1e1a94d5048b03a095"),
    RomSpec("IREF", "black2-fr", "Pokemon Version Noire 2 (French)", 536870912,
            "0722de9fe5b2f36301f37097481982afecd64fe5",
            ("971ccee9a738d5d172220a45dce1e9c40e49e563",)),
    RomSpec("IRDF", "white2-fr", "Pokemon Version Blanche 2 (French)", 536870912,
            "c228793d63cf43edca3285f42a6f91abaec90247"),
    RomSpec("IRBO", "black-us", "Pokemon Black Version (USA, Europe)", 268435456,
            "26ad0b9967aa279c4a266ee69f52b9b2332399a5"),
    RomSpec("IRAO", "white-us", "Pokemon White Version (USA, Europe)", 268435456,
            "bc696a0dfb448c7b3a8a206f0f8214411a039208"),
    RomSpec("IREO", "black2-us", "Pokemon Black Version 2 (USA, Europe)", 536870912,
            "e51e6dfb8678a3d19dcd2a10691b96a569ca0abb"),
    RomSpec("IRDO", "white2-us", "Pokemon White Version 2 (USA, Europe)", 536870912,
            "b5d7490be7b415b8f1e672a53e978a9cc667e56a"),
    RomSpec("IRBS", "black-es", "Pokemon Edicion Negra (Spanish)", 268435456,
            "68b55b82f5a033f9e9666c232f429e31ed658e54"),
    RomSpec("IRBI", "black-it", "Pokemon Versione Nera (Italian)", 268435456,
            "699f8c6a8390b5e30236b6c386bc3c4bd7bdc44e"),
    RomSpec("IRAI", "white-it", "Pokemon Versione Bianca (Italian)", 268435456,
            "2e33164d26236dd499f75d1de3123d85e822d502"),
    RomSpec("IREI", "black2-it", "Pokemon Versione Nera 2 (Italian)", 536870912,
            "68ec308db75d470f3c1499cc04117fe68fb4e942"),
    RomSpec("IRDI", "white2-it", "Pokemon Versione Bianca 2 (Italian)", 536870912,
            "b787bdd69fa79d270d08f334b188a61e3454405e"),
    RomSpec("IRDS", "white2-es", "Pokemon Edicion Blanca 2 (Spanish)", 536870912,
            "072749c9517f8d2a65f688b6f4ac5f30889fb559"),
    RomSpec("IRDD", "white2-de", "Pokemon Weisse Edition 2 (German)", 536870912,
            "60665d23a12a0ad4fbff75a4d4f287a9cec73b40"),
    RomSpec("IRES", "black2-es", "Pokemon Edicion Negra 2 (Spanish)", 536870912,
            "b69a30d5f0456ad1a3a1b52a945729f686b0299b"),
    RomSpec("IRBD", "black-de", "Pokemon Schwarze Edition (German)", 268435456,
            "f5688bd617be7e67a150732f42cfae6ae104b2cb"),
    RomSpec("IRED", "black2-de", "Pokemon Schwarze Edition 2 (German)", 536870912,
            "f43dd2e26f48163f11721bd1e3b2e6f9a73be636"),
    RomSpec("IRAD", "white-de", "Pokemon Weisse Edition (German)", 268435456,
            "fb752b211351f8480e3e1949e11a1d7741f05f5a"),
    RomSpec("IRAS", "white-es", "Pokemon Edicion Blanca (Spanish)", 268435456,
            "4cc963ca925409ff0f12f3c417d1cbe1094bf934"),
    RomSpec("IRBJ", "black-jp", "Pocket Monsters Black (Japanese)", 268435456,
            "4ce46933ab795fc8bfc94acb7a853206b0c20b60"),
    RomSpec("IRAJ", "white-jp", "Pocket Monsters White (Japanese)", 268435456,
            "e392548c1a59e4cafd7ba7a502770369410b2358"),
    RomSpec("IREJ", "black2-jp", "Pocket Monsters Black 2 (Japanese, Rev 1)", 536870912,
            "c55fe4412427e63ef28186af53ec114c7fdd9a0a"),
    RomSpec("IRDJ", "white2-jp", "Pocket Monsters White 2 (Japanese, Rev 1)", 536870912,
            "01666f87838c57dc0a65930a916982ad8941d8fb"),
    RomSpec("IRBK", "black-kr", "Pocket Monsters Black (Korean)", 268435456,
            "ca64de49a4429346ca578c2b21c16c8bcf1cf497"),
    RomSpec("IRAK", "white-kr", "Pocket Monsters White (Korean)", 268435456,
            "560288596203f31d3f1de8fd2e205d0f4c65a9e5"),
    RomSpec("IREK", "black2-kr", "Pocket Monsters Black 2 (Korean)", 536870912,
            "19f99e4f0b7babdb98e3ece9c230c5b51d51170a"),
    RomSpec("IRDK", "white2-kr", "Pocket Monsters White 2 (Korean)", 536870912,
            "3bbb5ff5c443c776b1e59ba51e8b2cd118fb776b"),
)}


def read_info(path: Path) -> RomInfo:
    path = Path(path)
    sha1 = hashlib.sha1()
    with path.open("rb") as f:
        header = f.read(0x200)
        sha1.update(header)
        while chunk := f.read(1 << 24):
            sha1.update(chunk)
    game_code = header[12:16].decode("ascii", errors="replace")
    return RomInfo(game_code=game_code, size=path.stat().st_size, sha1=sha1.hexdigest())


def identify(path: Path) -> RomSpec:
    """Return the spec of a clean known ROM, or raise WrongRomError (unknown game, wrong size, modified dump)."""
    info = read_info(path)
    spec = KNOWN_ROMS.get(info.game_code)
    if spec is None:
        raise WrongRomError(f"unknown game code {info.game_code!r}")
    if info.size != spec.size:
        raise WrongRomError(f"{spec.game_code}: expected size {spec.size}, got {info.size}")
    if info.sha1 != spec.sha1 and info.sha1 not in spec.alt_sha1:
        raise WrongRomError(f"{spec.game_code}: not the clean dump (sha1 {info.sha1}, expected {spec.sha1})")
    return spec
