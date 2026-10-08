# FME v1.9.20 — Lineup Order & Team Projection Range

Dashboard-only patch on top of v1.9.19. No prediction model, optimizer or waiver code is changed.

- Starting lineup rows sort in lineup-slot order: QB, RB, WR, TE, FLEX, SUPER_FLEX, K, DEF. Repeated positions stay in their original relative order.
- ESPN slot IDs are used for starting-slot labels; Sleeper uses ordered roster slots if their count matches occupied starter rows, falling back to player positions otherwise.
- Projected Team Points now displays sum of median starter projections – sum of high starter projections. These are **sums of marginal player percentiles**, not a modeled team-level outcome interval.
- Individual player low / median / high remain unchanged.
