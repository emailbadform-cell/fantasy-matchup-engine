# v1.9.5 — NFLverse name-ingestion fix

- Fixed player-history fallback matching when nflverse `player_name` is abbreviated but `player_display_name` contains the full player name.
- Regression coverage uses Deebo Samuel Sr. / D.Samuel, GSIS 00-0035719, Week 4.
- Preserves player-history freshness checks; no DATA PENDING gate was weakened.

# Model Changelog

## v1.1.0 — Complete prediction build / QB upstream correction
- Normalized NFLverse weekly player-stat column names into a canonical schema.
- Fixed passing attempts/yards-per-attempt mapping.
- Added derived catch rate, yards/target and yards/carry calculations from totals.
- Added field-goal and extra-point aliases.
- Rebuilt QB environment from the actual game QB identity rather than the player being projected.
- DEF uses the opposing QB environment.
- Added position-specific opportunity/efficiency projections.
- Preserved QB dependency for WR/TE/RB/K without applying a blanket multiplier to rushing production.
- Added explosive-play and TD environment factors.
- Added regression test for upstream QB resolution.
- Updated architecture version to 1.1.0.

## 1.8.0-qb-corrected
- Preserves strict chronology: Week N only consumes player/team history before Week N.
- QB pass-attempt center now uses recency-weighted player volume blended 80/20 with team passing volume.
- Dampens schedule-derived directional pass tendency by 50% before applying the existing pace factor.
- Removes the generic team TD-per-play red-zone proxy from QB passing-TD rate. RB/WR/TE TD logic is unchanged.
- Caps the combined QB passing-efficiency context stack (weather/surface/scheme/defense/matchup) to 0.85–1.15.
- Original non-QB projection branches remain unchanged.
- Adds QB stat-level Monte Carlo with coherent attempts/completions/YPA/TD/INT/rushing/fantasy distributions and common thresholds.
- QB stat Monte Carlo defaults to 1,000,000 draws; override with `FME_QB_STAT_MC_N` for faster local development/tests.

## 1.8.1-qb-data-integrity
- Added player-specific chronology completeness checks before target-week projections.
- If a player's target_week-1 row is missing from an otherwise current cache, NFLverse player stats are refreshed once before projection.
- Retains cached data as a fail-soft fallback if the upstream refresh is unavailable.
- Restored Low / Median / High fantasy-point columns in the dashboard; Median remains P50 and the primary ranking value.
- No QB formula coefficients were changed in this patch; investigation showed the v1.8 game-script pass tendency and pace components occupy separate intended roles.


## 1.8.2-data-integrity
- Fixed force_refresh so the legacy alternate cache can no longer intercept an explicit NFLverse download.
- Changed player refresh attempts from season-wide to player/week-specific keys.
- Added schedule-aware prior-week completeness (bye weeks are not treated as stale).
- Added history_freshness/history_complete/history_status to player data quality.
- Marks projections DATA PENDING when an expected prior-week player row remains unavailable after refresh.
- Model formulas are unchanged from v1.8.1.
