# Black 2 FR: EXP routine search notes (Task 3, in progress)

Status: LOCATED (see the last section). The earlier sections record how the search went.

## Verified facts (ROM `IREF`)

- ARM9 loads at RAM `0x02004000`. After decompression it is 633,888 bytes. There are 344 overlays.
- The battle engine appears to be overlay 167 (RAM `0x021998E0`, 268,096 bytes decompressed). This is a hypothesis, not confirmed.
- Item data is in NARC `/a/0/2/4` (639 files, 36 bytes each). Byte 2 of an entry is the hold effect:
  Exp. Share (item 216) has hold effect `0x33`, Lucky Egg (item 231) has `0x42`.
- Battle text is in NARC `/a/0/0/2`, files 17 and 19. Message 42 is "<name> a gagne <n> points Exp.!"
  and message 43 is the "bonus" variant ("un bonus de ...").
- Gen 5 text format: entries `(offset u32, length u16, unk u16)` at block start + 4 + 8*i. Entry `i` is encrypted
  with a 16-bit key starting at `0x7C89 + 0x2983*i`, rotated left by 3 after each character, terminated by `0xFFFF`.

## Approaches tried without success

1. Looking for an x^2.5 lookup table for the Gen 5 level-scaled formula: none found.
2. Looking for Thumb loads of message ids 42/43 close to each other: many hits, all in UI or switch-table code.
3. Looking for compares against the Exp. Share (`0x33`) and Lucky Egg (`0x42`) hold effects close together:
   hits are event variable ids in overlay 167, not hold effect tests.
4. Looking for the 170 / 150 percent multipliers: hits are switch tables.

## Progress with approach 3 (static, from the PP "exp" and "level" accessors)

Arm9 `0x0201CCF8` is a Pokemon-param getter `get(pp, paramId, buf)`; `0x0201CD1C` is the matching setter `put(pp, paramId, value)`.
Param ids seen: `8` = EXP, `0xA0` = level, `0xA1`..`0xA6` = HP and stats.

Found in overlay 167:
- `0x021BC1D8`: `bool BPP_AddExp(bpp r0, u32 *exp r1, out r2)`. Level >= 100 returns early; otherwise it adds `*exp` to the
  stored EXP (`bpp+8`), writes it with `put(pp, 8, ...)`, and on a level-up recomputes level and stats.
  Only two callers: `0x021B7EC0` and `0x021A8F1A`.
- `0x021A8E88`: client handler for the "gain EXP" command. It chooses message 42 or 43 from a flag byte (`[args+4]`),
  prints it, then loops `BPP_AddExp`. Its arguments hold `exp` (u32 at `+0`), the bonus flag (`+4`) and stat gains.
  It is entered from `0x021A8E0C`, called by the command dispatcher at `0x021A8DA2`.

So the client only applies EXP amounts. The decision of who earns what is made by the server side, which has not been found.
The dispatcher reaches several functions through ARM veneers (`ldr ip,[pc]; bx ip`) whose literal targets are
`0x0689D2FD`, `0x0689D329` and `0x0689D30D`. Those addresses are in VRAM (LCDC), not in any overlay: part of the
battle code seems to be loaded from a file into VRAM at run time. That code is the likely home of the EXP distribution.
It has not been found in the ROM files yet.

## Correction and savestate findings

- Overlay 169 is a small shared library loaded in VRAM at `0x06898020`. It is not the server. It holds accessors for a
  4-party record of `0x31` bytes per entry (count byte, then two 24-byte arrays).
- melonDS has no breakpoints, but its savestate (`.ml1`) holds the whole main RAM. Main RAM starts 36 bytes into the file.
  In a wild battle at the command menu the loaded overlays are 12, 27, 30, 31, 33, 35, 149, 167, 168 and 170.
  The battle code is therefore in overlays 167 (client/UI and shared logic) and 168. The EXP distribution is most likely in one of them.
- The client "gain EXP" handler picks message 42 or 43 from a flag byte, so the server does not mention those ids.
  The server only sends `(exp, bonus flag, stat gains)` per recipient. Finding the sender needs the command id or the server flow code.

## Suggested next step

Static search alone is not converging. A debugger-capable emulator (DeSmuME with its memory watch/breakpoints, or
melonDS) would let us put a write breakpoint on a party Pokemon's EXP field and read the writer's address directly.

## RESULT: the EXP distribution routine (Black 2 FR, overlay 167, RAM `0x021998E0`)

Found by transposing the community Action Replay "EXP share" cheat for White 2
(`521AEF84 42819903` / `121AEF88 000046C0`): the same code is at `+0x20` in the French Black 2 overlay 167.

`0x021AEE2C CalcExp(server r0, party r1, foeBPP r2, out r3)`; `out` is `Entry[6]` of 12 bytes (`u32 exp`, `u8 boosted` at +4).
Stack slots: `[sp+4]` party, `[sp+8]` foe, `[sp+0x24]` party size, `[sp+0x28]` base EXP E (after the x1.5 trainer boost).

1. `0x21AEE74`: clear `out[6]`.
2. `0x21AEE90..0x21AEF16`: count alive members holding item `0xD8` (Exp. Share) in `r7`; if any, E is halved
   (participants keep `ceil(E/2)`) and each holder gets `floor(E/2)/holders` (min 1).
3. `0x21AEF18..0x21AEF52`: `r7 = foe participant count` (`0x21BC624`), `r6 =` number of alive participants.
4. `0x21AEF54..0x21AEF66`: `[sp+0x20] = max(1, E / r6)`, the per participant share.
5. `0x21AEF66..0x21AEFCB`: for each alive party member `i`, for each participant id `k` (`0x21BC62C(foe,k)`), if it equals the member's
   poke id (`0x21BAC60`) then `out[i].exp += share`.
6. `0x21AEFCC..0x21AF0AB`: for each `out[i].exp != 0`: level scaling (`0x21AF0EC`), Lucky Egg (item `0xE7`, sets boosted), cap.
7. `0x21AF0AC..`: for each non zero entry call `0x21AF18C` (EV gain) then the client command is built.

Helpers: `0x219D514(party,i)` member BPP; `0x21BB388(bpp)` returns 1 if fainted; `0x21BAC60(bpp)` poke id; `0x21BB360(bpp)` held item;
`0x21BB1D4(bpp, 0xF)` level; `0x208D878` is the division routine (`r0 / r1`).

Consequence for the patch: replace `0x21AEE90..0x21AEFCB` (316 bytes) with new code that skips the Exp. Share halving, computes the
participant share, and gives each alive non participant below level 100 `max(1, share / 2)`. Steps 6 and 7 then apply their own level
scaling, Lucky Egg and EVs to each recipient. Note that step 7 also gives EVs to anyone with a non zero entry, so non participants will
earn EVs too (as Exp. Share holders did in Gen 5); the design doc said participants only. Ledgered as a ruling.
