# FME 100K + nflverse refresh and freshness diagnostics

Based on FME_HIT_100K_NFLVERSE_REFRESH_FIX.zip. Keeps the 100K QB default and dataset-level refresh fix.

## Root cause of the previous failing regression

The historical test created a 3-week player history but did not isolate the source dataset. `player_history_status()` inspected the installed 2026 nflverse cache, which contained a DET Week 4 row, and correctly returned `player_week_unrecorded` / complete. The test expected `data_pending` / incomplete, so it was fixture contamination, not evidence that nflverse was behind.

## Diagnostic fields

`source_status` now distinguishes `team_week_present`, `publication_unverified`, `player_record_present`, and `not_required` (bye or first week). `publication_unverified` does NOT claim that nflverse is behind; confirming remote publication vs local sync requires an independent source check.

## Testing

Run `python -m pytest -q tests/test_nflverse_data_integrity_v182.py tests/test_nflverse_player_freshness.py`. Tests use isolated source fixtures and do not need network.

## Full test suite

134 passed, 1 failed. The remaining failure is `tests/test_superflex_v198.py::test_open_slot_is_named_when_truly_unfillable`: expected `['QB','RB']`, actual `['QB','SUPER_FLEX']`. Confirmed the exact same failure exists in the unmodified previous ZIP. It is unrelated to this nflverse freshness update and is left unchanged rather than altering lineup behavior without a separate review.
