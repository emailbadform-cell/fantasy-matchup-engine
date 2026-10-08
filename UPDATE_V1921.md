# FME v1.9.21 — Sleeper Starting Slot Identity Fix

Apply on top of v1.9.20. This corrects a UI/data association bug; projection and waiver calculations are not changed.

- Root cause: v1.9.20 zipped the roster-order projection array to Sleeper's lineup-order slot array. When those orders differ, a TE could appear as QB and a K as RB.
- Backend now maps Sleeper `matchups[].starters` IDs to league `roster_positions` indices, before projecting and assembling the roster results. Each starter has `starting_slot` and `starting_slot_index` fields.
- Dashboard assigns labels using each player's `starting_slot`; no longer infers slots from its position in the projected roster array. Unknown slot associations fall back to the player's actual position rather than inventing a slot.
- ESPN continues using its per-player `espn_lineup_slot_id` mapping.
- Median–high card from v1.9.20 is retained unchanged.
- Automated tests include shuffled roster position, blank starters, mismatch/duplicate rejection, JS row mapping and prior multi-FLEX optimization.

## Deploy

Copy the patch files into the project, commit and push, then `git pull --ff-only` on the Oracle VM and restart the fme systemd service. Hard refresh the website.
