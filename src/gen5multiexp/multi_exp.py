"""Build the Gen 6/7 style Multi EXP edit for the CalcExp function of the battle overlay."""
from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

from . import asm, patcher

_TEMPLATE = Path(__file__).resolve().parent.parent / "asm" / "multi_exp.s"
NOP = b"\xC0\x46"  # mov r8, r8 (Thumb nop)
REGION_SIZE = 0x13C


@dataclass(frozen=True)
class Layout:
    """Addresses and stack slots of one ROM version. Addresses are RAM addresses of the battle overlay."""
    overlay_id: int
    func_start: int         # CalcExp
    region_start: int       # first byte replaced
    foe_part_count: int     # (foe) -> number of participant entries                  (Thumb)
    foe_part_id: int        # (foe, k) -> poke id of the k-th participant            (Thumb)
    client_member: int      # (obj, poke id) -> BPP of that poke id                  (Thumb)
    party_member: int       # (party, i) -> BPP of the i-th member                   (Thumb)
    is_fainted: int         # (bpp) -> 1 if HP is 0, else 0                          (Thumb)
    poke_id: int            # (bpp) -> poke id                                       (Thumb)
    get_value: int          # (bpp, id) -> value; id 0xF is the level                (Thumb)
    divide: int             # ARM routine: r0 / r1 -> r0
    s_psize: int            # stack slot (offset from sp) of the party size
    s_exp: int              # stack slot of the base EXP E
    s_share: int            # temporaries, free while the region runs
    s_i: int
    s_poke: int
    s_bpp: int
    region_size: int = REGION_SIZE

    @property
    def region_end(self) -> int:
        return self.region_start + self.region_size


# Two families of code: Black 2 / White 2 and Black / White. Stack slots differ per family, addresses per ROM.
_B2W2 = dict(overlay_id=167, s_psize=0x24, s_exp=0x28, s_share=0x20, s_i=0x10, s_poke=0xC, s_bpp=0x14)
_BW1 = dict(overlay_id=93, s_psize=0x1C, s_exp=0x20, s_share=0x18, s_i=0x10, s_poke=0xC, s_bpp=0x14)

LAYOUTS: dict[str, Layout] = {
    "IREF": Layout(func_start=0x021AEE2C, region_start=0x021AEE90, foe_part_count=0x021BC624,
                   foe_part_id=0x021BC62C, client_member=0x0219D230, party_member=0x0219D514,
                   is_fainted=0x021BB388, poke_id=0x021BAC60, get_value=0x021BB1D4, divide=0x0208D878, **_B2W2),
    "IRDF": Layout(func_start=0x021AEE4C, region_start=0x021AEEB0, foe_part_count=0x021BC644,
                   foe_part_id=0x021BC64C, client_member=0x0219D250, party_member=0x0219D534,
                   is_fainted=0x021BB3A8, poke_id=0x021BAC80, get_value=0x021BB1F4, divide=0x0208D8A4, **_B2W2),
    "IREO": Layout(func_start=0x021AEE0C, region_start=0x021AEE70, foe_part_count=0x021BC604,
                   foe_part_id=0x021BC60C, client_member=0x0219D210, party_member=0x0219D4F4,
                   is_fainted=0x021BB368, poke_id=0x021BAC40, get_value=0x021BB1B4, divide=0x0208D868, **_B2W2),
    "IRDO": Layout(func_start=0x021AEE4C, region_start=0x021AEEB0, foe_part_count=0x021BC644,
                   foe_part_id=0x021BC64C, client_member=0x0219D250, party_member=0x0219D534,
                   is_fainted=0x021BB3A8, poke_id=0x021BAC80, get_value=0x021BB1F4, divide=0x0208D894, **_B2W2),
    "IRBF": Layout(func_start=0x021CB254, region_start=0x021CB2A8, foe_part_count=0x021D6D84,
                   foe_part_id=0x021D6D8C, client_member=0x021B98B4, party_member=0x021B9B80,
                   is_fainted=0x021D5AE8, poke_id=0x021D53C0, get_value=0x021D5934, divide=0x0209C230, **_BW1),
    "IRAF": Layout(func_start=0x021CB274, region_start=0x021CB2C8, foe_part_count=0x021D6DA4,
                   foe_part_id=0x021D6DAC, client_member=0x021B98D4, party_member=0x021B9BA0,
                   is_fainted=0x021D5B08, poke_id=0x021D53E0, get_value=0x021D5954, divide=0x0209C248, **_BW1),
    "IRBO": Layout(func_start=0x021CB2D4, region_start=0x021CB328, foe_part_count=0x021D6E04,
                   foe_part_id=0x021D6E0C, client_member=0x021B9934, party_member=0x021B9C00,
                   is_fainted=0x021D5B68, poke_id=0x021D5440, get_value=0x021D59B4, divide=0x0209C2B0, **_BW1),
    "IRAO": Layout(func_start=0x021CB2F4, region_start=0x021CB348, foe_part_count=0x021D6E24,
                   foe_part_id=0x021D6E2C, client_member=0x021B9954, party_member=0x021B9C20,
                   is_fainted=0x021D5B88, poke_id=0x021D5460, get_value=0x021D59D4, divide=0x0209C2C8, **_BW1),
}


def source(layout: Layout) -> str:
    values = {f.name: f"{getattr(layout, f.name):#x}" for f in fields(layout)}
    return _TEMPLATE.read_text(encoding="utf-8").format(**values)


def code(layout: Layout) -> bytes:
    """Assemble the routine and pad it with nops to exactly `layout.region_size` bytes."""
    body = asm.assemble(source(layout), base=layout.region_start, thumb=True)
    if len(body) > layout.region_size:
        raise patcher.OutOfSpaceError(
            f"routine is {len(body)} bytes but the region only has {layout.region_size}")
    return body + NOP * ((layout.region_size - len(body)) // 2)


def check_original(layout: Layout, overlay_ram: int, overlay: bytes) -> bytes:
    """Verify that the overlay really has CalcExp where the layout says; return the original region bytes.

    Checks the prologue, the end of the clear loop right before the region and the start of the final loop
    right after it, so a wrong layout cannot silently overwrite unrelated code.
    """
    def at(addr: int, n: int) -> bytes:
        lo = addr - overlay_ram
        if lo < 0 or lo + n > len(overlay):
            raise patcher.OverwriteError(f"{addr:#x} is outside overlay {layout.overlay_id}")
        return overlay[lo:lo + n]

    prologue = at(layout.func_start, 4)
    if prologue not in (bytes.fromhex("f0b58db0"), bytes.fromhex("f8b58cb0")):
        raise patcher.OverwriteError(f"no CalcExp prologue at {layout.func_start:#x}: {prologue.hex()}")
    if at(layout.region_start - 8, 6) != bytes.fromhex("0004060c062e"):
        raise patcher.OverwriteError("code before the region is not the expected clear loop")
    ldr_psize = (0x9800 | (layout.s_psize // 4)).to_bytes(2, "little")
    if at(layout.region_end, 4) != ldr_psize + bytes.fromhex("0026"):
        raise patcher.OverwriteError("code after the region is not the expected final loop")
    return at(layout.region_start, layout.region_size)


def build(layout: Layout, original_region: bytes) -> list[patcher.Edit]:
    """Return the edit replacing the original region (`original_region` is checked against the ROM)."""
    if len(original_region) != layout.region_size:
        raise ValueError("original_region has the wrong length")
    return [patcher.Edit(layout.overlay_id, layout.region_start, code(layout), original_region)]
