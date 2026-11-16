# Testing the Black 2 FR patch in an emulator

Automated tests (`python -m pytest -q`) check the routine in an emulated CPU against a fake battle state, the ROM patcher,
the BPS tools and the final patch. They cannot play the game, so these manual checks are still needed.

## Setup

1. Apply the patch of your game (see the table in `README.md`) to its clean ROM, for example Noire 2 (FR):
   `python tools/apply_patch.py "Pokémon - Version Noire 2.nds" patches/black2-fr-multi-exp.bps Noire2_multiexp.nds`
   Only the Noire 2 (FR) patch has been played so far. Black/White (overlay 93) are the least checked: please report any
   crash at the start or at the end of a battle.
2. Copy your normal save next to it with the same base name (`Noire2_multiexp.sav`).
3. Start the game from the save. **Do not load a savestate made with the unpatched ROM**: it contains the old code in RAM.
   Use a battle started after loading the in-game save.

The patched overlay is recompressed and written back into its original slot, so the ROM keeps its size and layout.
(An earlier build stored it uncompressed at the end of the ROM; the game crashed when a battle started, so that was dropped.)

## Checklist

1. Wild battle with a 3+ member party, only the first member fights: every living member gains EXP. The fighter gets the same
   amount as in the unpatched game, the others about half (before the level scaling the game applies to each Pokémon).
2. Trainer battle: same behaviour, with the usual 1.5x trainer bonus.
3. A fainted party member gains nothing and no message appears for it.
4. A level 100 party member gains nothing.
5. A benched Pokémon close to its next level levels up from shared EXP: level-up message, stat screen, new move prompt.
6. A benched Pokémon that reaches its evolution level evolves normally after the battle.
7. Party of a single Pokémon: behaves exactly like the unpatched game.
8. Double battle: both fighters are paid once, the others get half.
9. Lucky Egg on a benched Pokémon gives it the boosted message; a held Exp. Share does nothing special.
10. EVs: benched Pokémon also receive the EVs of the defeated Pokémon (see "Known behaviour").

## Known behaviour

- A held Exp. Share has no extra effect: every living party member already shares EXP.
- Non-participants also earn EVs, because the game's existing per-recipient code applies EVs to every recipient.
- Benched Pokémon still go through the Gen 5 level scaling, so a higher-level Pokémon earns less than a lower-level one from the
  same battle. This is intended (the 50% applies before the scaling).
- The ROM keeps its size, but DSi-mode signature checks of a real console are not satisfied; use an emulator or a flashcart in DS mode.
