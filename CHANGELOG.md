## 1.9.9 ESPN slot-ID fix
- Decodes ESPN football lineup slot 3 as RB/WR, slot 5 as WR/TE, and slot 7 as OP/Superflex before shared optimization.
- Prevents ESPN numeric flex slots from surfacing as unknown SLOT_3/SLOT_5 rows.
- Sleeper optimizer behavior is unchanged.

## 1.9.8-superflex-slot-fix
- Normalizes ESPN/Sleeper SUPER_FLEX, SUPERFLEX, OP, QB/RB/WR/TE and Q/W/R/T aliases to one shared SUPER_FLEX slot.
- SUPER_FLEX accepts QB/RB/WR/TE and the optimizer always maximizes filled legal slots before median points.
- Optimal Lineup now names any genuinely unfillable open slot instead of hiding its identity.

# Changelog

## 1.9.2 ESPN scoring + lineup fix
- Corrected ESPN FFL scoring IDs: receiving yards=42, receiving TD=43, receptions=53.
- Added ESPN-ID-first player crosswalk with name/team fallback.
- Added D/ST team-based crosswalk.
- Added configured starter-count validation; partial ESPN lineups now fail closed instead of showing misleading team totals.
- Preserved v1.9.1 authenticated browser-compatible ESPN request path.

# v0.2.2

## Fixed
- Corrected LA/LAR side detection. A Sleeper LAR player now correctly resolves to NFLverse LA without incorrectly becoming the home team.
- Opponent roster is now joined back to Sleeper users so username/display_name are populated.

## Added
- GameContext contract.
- TeamContext and PlayerContext contracts.
- QB engine.
- Offense engine.
- Defense engine.
- Position-neutral engines for QB/RB/WR/TE/K/DEF.
- Shared factor engine.
- Unified model pipeline.
- Architecture documentation.

## Development policy
Future patches should fix bugs and build missing model architecture in parallel whenever dependencies allow it.

## Important
The engines are architecture contracts at this stage. They do not claim to be trained predictive models yet.

## 1.7.0-stage1-audited

- Completed Stage 1 pre-calibration audit remediation.
- Separated offensive and defensive scheme factors.
- Added factor ownership and formula-slot collision auditing.
- Removed duplicate play-volume multiplier behavior.
- Moved replacement and explosive context to uncertainty rather than uncalibrated median adjustments.
- Added calibration-readiness endpoint and documentation.

## 1.9.0-espn-integration
- Added ESPN Fantasy Football as a selectable dashboard source alongside Sleeper.
- Added read-only ESPN league/team roster ingestion using the active ESPN Fantasy v3 read endpoint.
- Public ESPN leagues work without credentials; private leagues use server-side ESPN_S2 and ESPN_SWID environment variables.
- ESPN players are cross-walked into the existing Sleeper/NFL player identity space so the authoritative FME projection path remains unchanged.
- Added common ESPN scoring-setting translation and preserves existing NFLverse/model/Monte Carlo architecture.

## 1.9.1 - ESPN authentication request fix
- Use a browser-compatible User-Agent for ESPN Fantasy API requests. Direct authenticated ESPN tests can return 200 while the prior custom FME User-Agent is rejected by ESPN request filtering.
- Accept either URL-encoded or decoded `espn_s2` cookie exports by decoding once before the request.
- Stop labeling every authenticated ESPN 401/403 as missing/expired credentials; error now distinguishes loaded credentials from missing authentication.
- Added regression coverage for cookie decoding, browser User-Agent, and authenticated 403 diagnostics.

## 1.9.6-bench-lineup-optimizer
- ESPN prediction responses now include projected bench and IR players in addition to current starters.
- Dashboard adds a Bench table with Low / Median / High and data freshness status.
- Dashboard adds an Optimize Lineup button for the loaded week.
- Optimizer uses the league's configured ESPN starter slots and the entire projected roster, including bench players.
- Exact memoized optimizer maximizes legal filled slots and then total median projected fantasy points; supports QB, RB, WR, TE, K, D/ST, FLEX and SUPERFLEX.
- Optimal lineup is advisory only; it does not modify the user's ESPN lineup.

## 1.9.7-unified-lineup-optimizer
- Added Sleeper bench projection capture and shared lineup optimization payloads.
- Sleeper optimizer now uses league roster_positions and excludes bench/IR slots.
- Preserves platform player eligibility and supports common FLEX/SUPERFLEX aliases.
- Optimizer prioritizes filling every legally fillable starter slot before maximizing median projected points.

## 1.9.10
- Universal ESPN player identity resolver: ESPN ID -> nflverse GSIS -> Sleeper GSIS, suffix-insensitive exact matching, team/position constrained fuzzy fallback, fail-closed ambiguity handling.

## v1.9.17 — Consolidated bye-aware waivers and Sleeper multi-FLEX validation
- Combines the v1.9.15 bye-protected waiver safeguards with v1.9.16 Sleeper FLEX/SUPER_FLEX slot auditing.
- Confirms the existing exact lineup optimizer independently fills two regular FLEX and one QB-eligible SUPER_FLEX slots, choosing the maximum legal projected lineup.
- Adds end-to-end regression tests for the three FLEX slots, no second QB, bye QB protection, and post-waiver point reconciliation.
- Does not implement rest-of-season projections; waiver recommendations remain current-week focused.
