# FME v1.9.24 — League-scoring accuracy and coverage (incremental)

## Changed
- Applies more league-supplied aggregate scoring coefficients in the active `PredictionEngine` path, including custom PPR (including zero), passing attempts/completions/incompletions, rushing attempts, aggregate field goals/PAT and misses, defensive sacks/turnovers/TDs.
- Fixes Sleeper `int` (defense interceptions) vs `pass_int` (interceptions thrown).
- Uses updated coefficients in the QB stat-level Monte Carlo distribution.
- Preserves ESPN scoring categories not in the known ID mapping as `_espn_unmapped_stat_ids` instead of silently discarding them.
- Adds `scoring_coverage` to ESPN and Sleeper prediction responses and a dashboard warning if any nonzero configured league rules cannot be represented by current statistical forecasts.

## Important limitations
This is **not full ESPN/Sleeper custom-scoring parity**. Predictions cannot currently represent distance-specific field goals, points-allowed defensive tiers, turnover-return yards, yardage bonuses, first-down bonuses, and other categories lacking separate forecast event distributions. Such rules are reported under `scoring_coverage.unmodeled_configured_rules`. Ordinary fantasy-point totals, optimizer ranks and waiver gains remain **partial** when that list is nonempty. The existing ESPN statId dictionary needs fixture-validated expansion for additional rule IDs.

Neither the league scoring settings nor scoring accuracy have been validated against your **actual** private ESPN/Sleeper leagues on Oracle. Do not deploy before reviewing the scoring warning for each league and regression-testing both sites.

## Files
- `backend/scoring/league_rules.py` — new shared scoring evaluator and coverage report
- `backend/engine/features.py` — active scorer delegation
- `backend/engine/qb_monte_carlo.py` — matching pass attempt/completion rules in QB MC
- `backend/integrations/espn.py` — capture unknown nonzero ESPN stat IDs
- `backend/engine/predictor.py` — attach scoring coverage to predictions
- `fantasy-matchup-dashboard/index.html` — show coverage warning
- `backend/tests/test_v1924_league_scoring.py` — regression tests

This is an incremental scoring correction, not a claim of complete scoring parity.
