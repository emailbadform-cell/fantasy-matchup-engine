# FME v1.9.23 — Optimal high projection fix

Apply over v1.9.22. The production predictor emits P90 at `projection.high`, while v1.9.22's optimizer read only `projection.high_fantasy_points`. The optimizer now accepts either field and sums the highs of the SAME median-selected starters. Missing high values still produce null (N/A), rather than invented totals.

Changes: `backend/engine/optimizer.py`; targeted regression tests in `backend/tests/test_v1923_optimizer_high_source.py`.

No changes to lineup eligibility, median optimization, waiver logic or the frontend.
