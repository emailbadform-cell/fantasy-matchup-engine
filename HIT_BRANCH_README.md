# Hit Projection experimental implementation

This is an **offline working-copy implementation**, not a commit to the GitHub repository or a production deployment.

- Adds independent Hit stat projections for QB passing yards/TD and WR/TE receiving yards/TD.
- Uses pre-target-week player data and opposing position allowances. Starts from 50/50 player/defense averages, applies a conservative 20% strength-of-hit-rate-index correction. **The correction is an uncalibrated hypothesis**, not a proven improvement or true probability.
- Adds per-stat historical season/recent and defense-over-line hit rates. Without a user-specified prop line, the model uses its own estimated line, so these are diagnostic rates, not bookmaker prop hit rates.
- Hit points use configured league scoring and retain baseline for other scoring stats.
- Adds Hit to roster/bench/optimizer/waiver UI and separate team Hit totals; non-QB/WR/TE use existing median as carry-through so team totals can be compared.
- Optimizer still selects on median, not Hit. Waiver recommendations still rank by median gain; the Low/Median/High/Hit columns refer to the **new starter**, not the team-wide gain.
- No explicit Project Players screen was found in this archived dashboard; the underlying `project_candidate` predictor returns Hit, but an independent Project Players UI cannot be verified here.
- The source archive may differ from the current live GitHub dashboard; review before merging. No live API data or calibration backtest was run.

Tests: `python -m unittest discover -s backend/tests -q`.
