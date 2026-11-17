@ Gen 6/7 style Multi EXP: replacement for the Exp. Share logic and participant loop of CalcExp.
@
@ Placed at the start of the region (see Layout.region_start), Thumb, r5 = out array (Entry[6], 12 bytes
@ each: u32 exp, u8 boosted, ...). Stack slots of the CalcExp frame (offsets differ per game family):
@   [sp] server, [sp+4] party, [sp+8] foe BPP (same everywhere)
@   {s_psize} party size, {s_exp} base EXP E
@   {s_i}, {s_poke}, {s_bpp}, {s_share} are free temporaries (i, poke id, member BPP, participant share).
@ r4, r6, r7 are free. Execution falls through to the code that follows the region.
@
@ Behaviour: every alive participant gets share = max(1, E / aliveParticipants), exactly as the unpatched game does
@ without Exp. Share. Every other alive party member below level 100 gets the same share (100% EXP for the whole team).
@ The existing code after the region applies level scaling, Lucky Egg and EVs to each non zero entry.

    ldr   r0, [sp, #8]
    bl    {foe_part_count}
    adds  r7, r0, #0
    movs  r6, #0
    movs  r4, #0
    cmp   r7, #0
    ble   share
count_loop:
    lsls  r1, r4, #0x18
    ldr   r0, [sp, #8]
    lsrs  r1, r1, #0x18
    bl    {foe_part_id}
    adds  r1, r0, #0
    ldr   r0, [sp]
    ldr   r0, [r0, #8]
    bl    {client_member}
    bl    {is_fainted}
    cmp   r0, #0
    bne   count_next
    adds  r6, r6, #1
count_next:
    adds  r4, r4, #1
    cmp   r4, r7
    blt   count_loop
share:
    cmp   r6, #0
    bne   have_participants
    movs  r6, #1
have_participants:
    ldr   r0, [sp, #{s_exp}]
    adds  r1, r6, #0
    blx   {divide}
    str   r0, [sp, #{s_share}]
    cmp   r0, #0
    bne   have_share
    movs  r0, #1
    str   r0, [sp, #{s_share}]
have_share:
    movs  r0, #0
    str   r0, [sp, #{s_i}]
    ldr   r0, [sp, #{s_psize}]
    cmp   r0, #0
    bls   done
member_loop:
    ldr   r1, [sp, #{s_i}]
    ldr   r0, [sp, #4]
    lsls  r1, r1, #0x18
    lsrs  r1, r1, #0x18
    bl    {party_member}
    str   r0, [sp, #{s_bpp}]
    bl    {is_fainted}
    cmp   r0, #0
    bne   next_member
    ldr   r0, [sp, #{s_bpp}]
    bl    {poke_id}
    str   r0, [sp, #{s_poke}]
    ldr   r1, [sp, #{s_i}]
    movs  r0, #0xc
    adds  r6, r1, #0
    muls  r6, r0, r6
    movs  r4, #0
    cmp   r7, #0
    bls   not_participant
part_loop:
    ldr   r0, [sp, #8]
    adds  r1, r4, #0
    bl    {foe_part_id}
    ldr   r1, [sp, #{s_poke}]
    cmp   r1, r0
    bne   part_next
    ldr   r1, [r5, r6]
    ldr   r0, [sp, #{s_share}]
    adds  r0, r1, r0
    str   r0, [r5, r6]
part_next:
    adds  r0, r4, #1
    lsls  r0, r0, #0x18
    lsrs  r4, r0, #0x18
    cmp   r4, r7
    bcc   part_loop
not_participant:
    ldr   r0, [r5, r6]
    cmp   r0, #0
    bne   next_member
    ldr   r0, [sp, #{s_bpp}]
    movs  r1, #0xf
    bl    {get_value}
    cmp   r0, #0x64
    bcs   next_member
    ldr   r0, [sp, #{s_share}]
    str   r0, [r5, r6]
next_member:
    ldr   r0, [sp, #{s_i}]
    adds  r0, r0, #1
    lsls  r0, r0, #0x10
    lsrs  r1, r0, #0x10
    str   r1, [sp, #{s_i}]
    ldr   r0, [sp, #{s_psize}]
    cmp   r1, r0
    bcc   member_loop
done:
