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
    "IRDS": Layout(func_start=0x021aedec, region_start=0x021aee50, foe_part_count=0x021bc5e4,
                   foe_part_id=0x021bc5ec, client_member=0x0219d1f0, party_member=0x0219d4d4,
                   is_fainted=0x021bb348, poke_id=0x021bac20, get_value=0x021bb194, divide=0x0208d864, **_B2W2),
    "IRBS": Layout(func_start=0x021cb294, region_start=0x021cb2e8, foe_part_count=0x021d6dc4,
                   foe_part_id=0x021d6dcc, client_member=0x021b98f4, party_member=0x021b9bc0,
                   is_fainted=0x021d5b28, poke_id=0x021d5400, get_value=0x021d5974, divide=0x0209c280, **_BW1),
    "IRAI": Layout(func_start=0x021cb1f4, region_start=0x021cb248, foe_part_count=0x021d6d24,
                   foe_part_id=0x021d6d2c, client_member=0x021b9854, party_member=0x021b9b20,
                   is_fainted=0x021d5a88, poke_id=0x021d5360, get_value=0x021d58d4, divide=0x0209c248, **_BW1),
    "IRDI": Layout(func_start=0x021aed4c, region_start=0x021aedb0, foe_part_count=0x021bc544,
                   foe_part_id=0x021bc54c, client_member=0x0219d150, party_member=0x0219d434,
                   is_fainted=0x021bb2a8, poke_id=0x021bab80, get_value=0x021bb0f4, divide=0x0208d814, **_B2W2),
    "IRBI": Layout(func_start=0x021cb1d4, region_start=0x021cb228, foe_part_count=0x021d6d04,
                   foe_part_id=0x021d6d0c, client_member=0x021b9834, party_member=0x021b9b00,
                   is_fainted=0x021d5a68, poke_id=0x021d5340, get_value=0x021d58b4, divide=0x0209c230, **_BW1),
    "IREI": Layout(func_start=0x021aed0c, region_start=0x021aed70, foe_part_count=0x021bc504,
                   foe_part_id=0x021bc50c, client_member=0x0219d110, party_member=0x0219d3f4,
                   is_fainted=0x021bb268, poke_id=0x021bab40, get_value=0x021bb0b4, divide=0x0208d7e8, **_B2W2),
    "IRDD": Layout(func_start=0x021aed6c, region_start=0x021aedd0, foe_part_count=0x021bc564,
                   foe_part_id=0x021bc56c, client_member=0x0219d170, party_member=0x0219d454,
                   is_fainted=0x021bb2c8, poke_id=0x021baba0, get_value=0x021bb114, divide=0x0208d814, **_B2W2),
    "IRES": Layout(func_start=0x021aedcc, region_start=0x021aee30, foe_part_count=0x021bc5c4,
                   foe_part_id=0x021bc5cc, client_member=0x0219d1d0, party_member=0x0219d4b4,
                   is_fainted=0x021bb328, poke_id=0x021bac00, get_value=0x021bb174, divide=0x0208d838, **_B2W2),
    "IRBD": Layout(func_start=0x021cb214, region_start=0x021cb268, foe_part_count=0x021d6d44,
                   foe_part_id=0x021d6d4c, client_member=0x021b9874, party_member=0x021b9b40,
                   is_fainted=0x021d5aa8, poke_id=0x021d5380, get_value=0x021d58f4, divide=0x0209c230, **_BW1),
    "IRED": Layout(func_start=0x021aed4c, region_start=0x021aedb0, foe_part_count=0x021bc544,
                   foe_part_id=0x021bc54c, client_member=0x0219d150, party_member=0x0219d434,
                   is_fainted=0x021bb2a8, poke_id=0x021bab80, get_value=0x021bb0f4, divide=0x0208d7e8, **_B2W2),
    "IRAD": Layout(func_start=0x021cb234, region_start=0x021cb288, foe_part_count=0x021d6d64,
                   foe_part_id=0x021d6d6c, client_member=0x021b9894, party_member=0x021b9b60,
                   is_fainted=0x021d5ac8, poke_id=0x021d53a0, get_value=0x021d5914, divide=0x0209c248, **_BW1),
    "IRAS": Layout(func_start=0x021cb294, region_start=0x021cb2e8, foe_part_count=0x021d6dc4,
                   foe_part_id=0x021d6dcc, client_member=0x021b98f4, party_member=0x021b9bc0,
                   is_fainted=0x021d5b28, poke_id=0x021d5400, get_value=0x021d5974, divide=0x0209c298, **_BW1),
    "IRBJ": Layout(func_start=0x021cb12c, region_start=0x021cb180, foe_part_count=0x021d6c44,
                   foe_part_id=0x021d6c4c, client_member=0x021b97d4, party_member=0x021b9aa0,
                   is_fainted=0x021d59a8, poke_id=0x021d5280, get_value=0x021d57f4, divide=0x0209c1bc, **_BW1),
    "IRAJ": Layout(func_start=0x021cb14c, region_start=0x021cb1a0, foe_part_count=0x021d6c64,
                   foe_part_id=0x021d6c6c, client_member=0x021b97f4, party_member=0x021b9ac0,
                   is_fainted=0x021d59c8, poke_id=0x021d52a0, get_value=0x021d5814, divide=0x0209c1d4, **_BW1),
    "IREJ": Layout(func_start=0x021ae7ec, region_start=0x021ae850, foe_part_count=0x021bbfe4,
                   foe_part_id=0x021bbfec, client_member=0x0219cbf0, party_member=0x0219ced4,
                   is_fainted=0x021bad48, poke_id=0x021ba620, get_value=0x021bab94, divide=0x0208d548, **_B2W2),
    "IRDJ": Layout(func_start=0x021ae80c, region_start=0x021ae870, foe_part_count=0x021bc004,
                   foe_part_id=0x021bc00c, client_member=0x0219cc10, party_member=0x0219cef4,
                   is_fainted=0x021bad68, poke_id=0x021ba640, get_value=0x021babb4, divide=0x0208d574, **_B2W2),
    "IRBK": Layout(func_start=0x021cb9d4, region_start=0x021cba28, foe_part_count=0x021d7504,
                   foe_part_id=0x021d750c, client_member=0x021ba034, party_member=0x021ba300,
                   is_fainted=0x021d6268, poke_id=0x021d5b40, get_value=0x021d60b4, divide=0x0209c94c, **_BW1),
    "IRAK": Layout(func_start=0x021cb9d4, region_start=0x021cba28, foe_part_count=0x021d7504,
                   foe_part_id=0x021d750c, client_member=0x021ba034, party_member=0x021ba300,
                   is_fainted=0x021d6268, poke_id=0x021d5b40, get_value=0x021d60b4, divide=0x0209c964, **_BW1),
    "IREK": Layout(func_start=0x021af54c, region_start=0x021af5b0, foe_part_count=0x021bcd44,
                   foe_part_id=0x021bcd4c, client_member=0x0219d950, party_member=0x0219dc34,
                   is_fainted=0x021bbaa8, poke_id=0x021bb380, get_value=0x021bb8f4, divide=0x0208df54, **_B2W2),
    "IRDK": Layout(func_start=0x021af56c, region_start=0x021af5d0, foe_part_count=0x021bcd64,
                   foe_part_id=0x021bcd6c, client_member=0x0219d970, party_member=0x0219dc54,
                   is_fainted=0x021bbac8, poke_id=0x021bb3a0, get_value=0x021bb914, divide=0x0208df80, **_B2W2),
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
