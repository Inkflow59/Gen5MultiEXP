"""Thin wrapper around Keystone to assemble ARM/Thumb code at a fixed address."""
from __future__ import annotations

import keystone


class AsmError(Exception):
    """Raised when the assembler rejects the source."""


def assemble(source: str, base: int, thumb: bool = True) -> bytes:
    """Assemble `source` as if it were placed at `base` (so `bl 0x...` targets resolve correctly)."""
    mode = keystone.KS_MODE_THUMB if thumb else keystone.KS_MODE_ARM
    ks = keystone.Ks(keystone.KS_ARCH_ARM, mode)
    try:
        encoding, _count = ks.asm(source, base)
    except keystone.KsError as exc:
        raise AsmError(str(exc)) from exc
    if encoding is None:
        raise AsmError("assembler produced no output")
    return bytes(encoding)
