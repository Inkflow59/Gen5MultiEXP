"""Search and disassembly helpers used to locate the EXP routine in extracted code."""
from __future__ import annotations

import capstone


def find_pattern(data: bytes, pattern: bytes, mask: bytes) -> list[int]:
    """Return every offset where data matches pattern under mask (mask byte 0 = wildcard)."""
    assert len(pattern) == len(mask)
    first = [i for i, m in enumerate(mask) if m]
    hits = []
    n = len(pattern)
    for off in range(len(data) - n + 1):
        if all(data[off + i] & mask[i] == pattern[i] & mask[i] for i in first):
            hits.append(off)
    return hits


def disassemble(data: bytes, base: int, offset: int, count: int, thumb: bool) -> list[str]:
    """Disassemble `count` instructions starting at data[offset]; addresses start from base+offset."""
    mode = capstone.CS_MODE_THUMB if thumb else capstone.CS_MODE_ARM
    md = capstone.Cs(capstone.CS_ARCH_ARM, mode)
    out = []
    for insn in md.disasm(data[offset:offset + count * 4], base + offset):
        out.append(f"0x{insn.address:x}: {insn.mnemonic} {insn.op_str}".rstrip())
        if len(out) == count:
            break
    return out
