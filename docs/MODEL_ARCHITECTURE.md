# Complete Unified Prediction Architecture v1.1.0

The engine is designed as a dependency graph, not six independent projection calculators.

## Data
Sleeper identity/rosters -> NFLverse schedule -> player weekly stats -> team stats -> participation/PBP when available.

## Feature layers
1. Leakage-safe player rolling history (3/6/12 games).
2. QB environment: volume, efficiency, turnovers, scoring impact, rushing.
3. Offensive environment: play volume, pass/rush tendency, scoring and explosive proxies.
4. Defensive environment: run/pass defense, pressure, coverage, positional defense.
5. Usage: player opportunity baselines.
6. Position matchup: QB pressure/coverage, RB front/receiving, WR outside/slot, TE coverage, K red-zone, DEF opposing QB.
7. Game environment: total, spread, home/away, rest.
8. Explosive-play adjustment.
9. TD environment.
10. Opportunity/efficiency split.

## QB upstream dependency
The projected team's QB is resolved from the game's away/home QB identity. WR/TE receiving, RB receiving, K scoring and other dependent environments use that QB. DEF uses the opposing QB. The projected player's own stats are never silently substituted for the team's QB.

## Position outputs
QB, RB, WR, TE, K and DEF each have position-specific stat projections and fantasy scoring.

## Validation gate
Do not audit final accuracy until all position outputs are populated from real historical data, QB volume metrics are correctly mapped, and regression tests pass.
