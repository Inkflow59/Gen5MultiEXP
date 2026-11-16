import find_exp


def test_find_pattern_exact_and_masked():
    data = bytes.fromhex("00 11 22 33 44 11 99 33 44")
    assert find_exp.find_pattern(data, bytes.fromhex("11 22 33"), b"\xff\xff\xff") == [1]
    # mask 0x00 on the middle byte makes it a wildcard
    assert find_exp.find_pattern(data, bytes.fromhex("11 00 33"), b"\xff\x00\xff") == [1, 5]


def test_disassemble_thumb_and_arm():
    thumb = bytes.fromhex("00bf7047")  # nop ; bx lr
    lines = find_exp.disassemble(thumb, base=0x02000000, offset=0, count=2, thumb=True)
    assert lines[0].split()[0] == "0x2000000:" and "nop" in lines[0]
    assert "bx" in lines[1]
    arm = bytes.fromhex("1eff2fe1")  # bx lr
    lines = find_exp.disassemble(arm, base=0x02000000, offset=0, count=1, thumb=False)
    assert "bx" in lines[0]
