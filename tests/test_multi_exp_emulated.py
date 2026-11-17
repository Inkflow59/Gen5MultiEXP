"""Run the new routine in Unicorn against a fake battle state (helpers are small stubs at the real addresses).

Every layout (8 ROMs, two code families with different stack frames) is exercised."""
import struct

import unicorn
from unicorn import arm_const as arm

import pytest

from gen5multiexp import asm, multi_exp

CODE_BASE, CODE_SIZE = 0x02000000, 0x00400000
STACK_BASE = 0x03000000
SP = STACK_BASE + 0x8000
BPP_BASE = 0x03020000
OUT_BASE = 0x03030000
FOE = 0x03040000
SERVER = 0x03050000
PARTY = 0x03060000
BPP_STRIDE = 0x20

DIVIDE_ARM = "mov r2, #0\nloop:\ncmp r0, r1\nbcc end\nsub r0, r0, r1\nadd r2, r2, #1\nb loop\nend:\nmov r0, r2\nbx lr"
MEMBER = "lsls r1, r1, #5\nmovs r0, #3\nlsls r0, r0, #24\nmovs r2, #2\nlsls r2, r2, #16\nadds r0, r0, r2\nadds r0, r0, r1\nbx lr"


def stubs(L):
    return {
        L.foe_part_count: "ldrb r0, [r0, #0xd0]\nbx lr",
        L.foe_part_id: "adds r0, r0, r1\nadds r0, #0xd1\nldrb r0, [r0]\nbx lr",
        L.client_member: MEMBER,
        L.party_member: MEMBER,
        L.is_fainted: "ldrh r0, [r0]\ncmp r0, #0\nbeq f\nmovs r0, #0\nbx lr\nf:\nmovs r0, #1\nbx lr",
        L.poke_id: "ldrb r0, [r0, #4]\nbx lr",
        L.get_value: "ldrb r0, [r0, #2]\nbx lr",
    }


@pytest.fixture(params=sorted(multi_exp.LAYOUTS))
def L(request):
    return multi_exp.LAYOUTS[request.param]


def run_calc(L, members, participants, exp):
    """members: list of (hp, level); member i has poke id i. Returns the 6 exp values written to `out`."""
    uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_THUMB)
    uc.mem_map(CODE_BASE, CODE_SIZE)
    uc.mem_map(STACK_BASE, 0x100000)
    uc.mem_write(L.region_start, multi_exp.code(L))
    for addr, src in stubs(L).items():
        uc.mem_write(addr, asm.assemble(src, base=addr, thumb=True))
    uc.mem_write(L.divide, asm.assemble(DIVIDE_ARM, base=L.divide, thumb=False))
    for i, (hp, level) in enumerate(members):
        uc.mem_write(BPP_BASE + i * BPP_STRIDE, struct.pack("<HBBB", hp, level, 0, i))
    uc.mem_write(FOE + 0xD0, bytes([len(participants)]) + bytes(participants))
    uc.mem_write(SERVER + 8, struct.pack("<I", PARTY))
    uc.mem_write(OUT_BASE, b"\0" * 72)
    frame = {0: SERVER, 4: PARTY, 8: FOE, L.s_psize: len(members), L.s_exp: exp}
    for off, value in frame.items():
        uc.mem_write(SP + off, struct.pack("<I", value))
    uc.reg_write(arm.UC_ARM_REG_SP, SP)
    uc.reg_write(arm.UC_ARM_REG_R5, OUT_BASE)
    end = L.region_start + L.region_size
    uc.emu_start(L.region_start | 1, end, count=200000)
    assert uc.reg_read(arm.UC_ARM_REG_PC) == end
    return [struct.unpack("<I", uc.mem_read(OUT_BASE + 12 * i, 4))[0] for i in range(6)]


def test_code_fills_the_region_exactly(L):
    assert len(multi_exp.code(L)) == L.region_size


def test_one_participant_gets_the_unpatched_amount(L):
    out = run_calc(L, [(50, 30), (50, 30), (50, 30)], participants=[0], exp=300)
    assert out[0] == 300


def test_non_participants_get_a_full_participant_share(L):
    out = run_calc(L, [(50, 30), (50, 30), (50, 30)], participants=[0, 1], exp=300)
    assert out[:3] == [150, 150, 150]
    assert out[3:] == [0, 0, 0]


def test_party_of_one_is_unchanged(L):
    assert run_calc(L, [(50, 30)], participants=[0], exp=100) == [100, 0, 0, 0, 0, 0]


def test_fainted_non_participant_earns_nothing_and_fainted_participant_is_not_counted(L):
    out = run_calc(L, [(50, 30), (0, 30), (50, 30)], participants=[0, 1], exp=300)
    assert out[0] == 300          # only one alive participant, so the full share
    assert out[1] == 0            # fainted participant
    assert out[2] == 300          # alive non participant gets the full share


def test_level_100_member_earns_nothing(L):
    out = run_calc(L, [(50, 30), (50, 100), (50, 30)], participants=[0], exp=300)
    assert out[1] == 0 and out[2] == 300


def test_tiny_exp_gives_at_least_one_point_to_each_recipient(L):
    out = run_calc(L, [(50, 30), (50, 30), (50, 30)], participants=[0], exp=1)
    assert out[:3] == [1, 1, 1]


def test_no_alive_participant_does_not_crash_and_still_shares(L):
    out = run_calc(L, [(0, 30), (50, 30), (50, 30)], participants=[0], exp=100)
    assert out[0] == 0 and out[1] == 100 and out[2] == 100


def test_slots_beyond_the_party_size_are_untouched(L):
    out = run_calc(L, [(50, 30), (50, 30)], participants=[0], exp=100)
    assert out[2:] == [0, 0, 0, 0]


def test_each_recipient_has_one_entry_with_nonzero_exp(L):
    out = run_calc(L, [(50, 30)] * 6, participants=[0, 1, 2], exp=600)
    assert sum(1 for v in out if v) == 6
    assert out == [200] * 6
