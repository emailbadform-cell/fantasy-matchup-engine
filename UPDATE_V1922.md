# FME v1.9.22 — Optimal Lineup Median–High

Apply over v1.9.21. Includes `backend/engine/optimizer.py`, `fantasy-matchup-dashboard/index.html`, and a targeted regression test.

The **Optimal Team Points** card now reports sum of median–sum of high fantasy-point projections for the *same optimized starting players*. The optimizer still selects players by median points and fills legal slots first. A missing high projection produces `N/A` rather than fabricating an upper bound. Unfilled slots contribute zero. All existing other cards, slot assignments, waivers, and model projections are unchanged.

After extracting into the existing project, run `python -m unittest backend.tests.test_v1922_optimal_range -v`, commit and push to GitHub, then `git pull --ff-only origin main && sudo systemctl restart fme` on Oracle. Hard-refresh the browser.
