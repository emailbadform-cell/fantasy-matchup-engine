# Stage 1 — Pre-Calibration Audit Remediation

Version: **1.7.0-stage1-audited**

## Objective

Make the primary `PredictionEngine` structurally safe for statistical calibration before using historical games to tune it.

## Completed

- Separated offensive-scheme and defensive-scheme effects.
- Removed the previous shared scheme multiplier that could count the same signal twice.
- Made game script the owner of pace/directional volume; `play_volume` is now diagnostic rather than a second multiplier.
- Kept raw offensive-line and defensive-front values as diagnostics while the OL-vs-DL interaction owns the explicit trench interaction.
- Restricted replacement/depth-chart context to simulation uncertainty rather than silently changing fantasy-point medians.
- Restricted explosive-play information to uncertainty/dispersion rather than injecting an uncalibrated median boost.
- Restricted red-zone context to touchdown-rate expectation and clearly labels the current overall-TD/play proxy.
- Preserved coverage assignment as unavailable unless position-specific defensive assignment data exists.
- Preserved referee and coaching as metadata-only until historical penalty/coaching datasets are available.
- Added an explicit factor-ownership ledger to every player prediction.
- Added formula-slot collision detection so future layers cannot silently reuse the same formula slot without an explicit exception.
- Added calibration-readiness metadata and layer-impact provenance to the prediction payload.

## Ownership model

| Model component | Primary owner | Purpose |
|---|---|---|
| Game script | `game_script` | Pace and directional volume |
| Opportunity | `opportunity` | Player role/volume |
| Offensive scheme | `offensive_scheme` | Offensive distribution tendency |
| Defensive scheme | `defensive_scheme` | Pressure/efficiency |
| Position matchup | `position_matchup` | Position-specific opponent efficiency |
| OL/DL interaction | `trench_matchup` | Explicit trench interaction |
| Weather | `weather` | Weather effect |
| Surface | `surface` | Indoor/surface effect |
| Red zone | `red_zone` | TD-rate expectation only |
| Explosive plays | `explosive` | Distribution/uncertainty |
| Replacement | `replacement` | Distribution/uncertainty |
| QB dependency | `qb_correlation` | Skill-player QB dependency |
| Coverage | `coverage_assignment` | Receiver target adjustment when data exists |
| Referee | metadata | Not predictive until historical penalty data exists |
| Coaching | metadata | Not predictive until historical tendency data exists |

## Calibration gate

The engine is now ready for the **calibration implementation phase**, but calibration itself has not been performed. Historical predictions must be generated using a strict pregame cutoff and evaluated against the completed game's actual statistics.

The new `/api/v1/calibration/readiness` endpoint defines the required observations and evaluation dimensions.

## Validation

- `PYTHONPATH=. pytest -q` → **34 passed**
- `python -m compileall -q .` → **pass**
- Bundled Week 4-style roster smoke test → **11/11 projections**, **0 ownership collisions**, **0 propagation failures**, model gate `functional=true`, `audit_ready=true`.

## Remaining for Stage 2

- Build the walk-forward historical prediction runner.
- Build actual-vs-predicted stat reconciliation.
- Calculate calibration curves and interval coverage.
- Calibrate medians, TD probabilities, and uncertainty by position/context.
- Run out-of-sample validation and compare against simple baselines.
