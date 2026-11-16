import capstone

from gen5multiexp import asm


def _dis(code: bytes, base: int):
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    return [(i.address, i.mnemonic, i.op_str) for i in md.disasm(code, base)]


def test_assemble_thumb_nop_is_two_bytes_and_decodes_as_nop():
    code = asm.assemble("nop", base=0x02000000, thumb=True)
    assert len(code) == 2
    assert _dis(code, 0x02000000)[0][1] == "nop"


def test_assemble_bl_to_absolute_target_uses_base_address():
    code = asm.assemble("bl 0x021bc624", base=0x021AEE90, thumb=True)
    assert len(code) == 4
    ((addr, mnem, op),) = _dis(code, 0x021AEE90)
    assert mnem == "bl" and int(op.lstrip("#"), 16) == 0x021BC624


def test_assemble_labels_and_branches_resolve_inside_the_block():
    src = """
        movs r0, #0
    loop:
        adds r0, r0, #1
        cmp r0, #3
        blt loop
    """
    code = asm.assemble(src, base=0x1000, thumb=True)
    assert len(code) == 8


def test_assemble_error_is_reported():
    try:
        asm.assemble("notaninstruction r0", base=0, thumb=True)
    except asm.AsmError:
        return
    raise AssertionError("AsmError expected")
