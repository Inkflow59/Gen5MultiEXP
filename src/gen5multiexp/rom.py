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


KNOWN_ROMS: dict[str, RomSpec] = {s.game_code: s for s in (
    RomSpec("IRBF", "black-fr", "Pokemon Version Noire (French)", 268435456,
            "a559da54839663d8f8f3f03382e5665a61873d22"),
    RomSpec("IRAF", "white-fr", "Pokemon Version Blanche (French)", 268435456,
            "28f075915dd445cbfd902f1e1a94d5048b03a095"),
    RomSpec("IREF", "black2-fr", "Pokemon Version Noire 2 (French)", 536870912,
            "0722de9fe5b2f36301f37097481982afecd64fe5"),
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
    if info.sha1 != spec.sha1:
        raise WrongRomError(f"{spec.game_code}: not the clean dump (sha1 {info.sha1}, expected {spec.sha1})")
    return spec
