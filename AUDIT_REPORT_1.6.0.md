# Fantasy Matchup Engine — Functional Audit

## Build
- Version: 1.6.0-audited-core
- Authoritative prediction path: `backend.engine.predictor.PredictionEngine`
- Automated tests: 32 passed

## Findings fixed
1. Defensive matchup data was previously sourced from offensive player/team rows in a way that could label default values as data-backed. Added a dedicated `NFLVerseClient.defense_history()` that joins opponent team offense with target-defense player statistics and enforces the pregame cutoff.
2. The bundled project contained two cache layouts. NFLverse loading now checks both, preventing unnecessary network failures when the required cache is already shipped.
3. `NFLVerseClient.normalize_team()` was missing even though a repository test expected it. Restored it and expanded aliases.
4. Opportunity propagation previously had no numeric impact evidence. It now reports a position-appropriate opportunity factor for QB/RB/WR/TE and remains neutral for K/DEF.
5. Red-zone inputs are not present in the bundled NFLverse weekly team stats. The model now explicitly labels this layer as a proxy based on team touchdown rate per offensive play instead of claiming red-zone data.
6. Coverage assignment remains explicitly unavailable unless position-specific coverage data exists; the model no longer converts generic passing yards allowed into a false player-level coverage assignment.
7. DEF is evaluated using defensive context rather than requiring a player identity/history record.
8. Architecture reporting now distinguishes the primary wired prediction path from legacy contract modules that are not wired into prediction.
9. QB touchdown-rate calculation is bounded and no longer has an unbounded red-zone multiplier.
10. Audit identity warnings exclude team DEF entries, for which player identity is not applicable.

## Remaining limitations (truthfully exposed)
- Player-level coverage assignment/receiver alignment from charting data is not available in the bundled NFLverse files.
- Referee tendencies are not currently modeled from historical penalty data; referee name presence is metadata only.
- Coaching tendencies are not currently modeled independently of offensive scheme; coach identity is metadata.
- Red-zone opportunity is not directly available and therefore uses an explicit scoring-environment proxy.
- Early-season players with fewer than three historical games remain limited-confidence cases.
- The model is not considered statistically validated merely because unit tests pass. Calibration against actual completed games is still required.

## Audit standard
A layer is not considered data-backed merely because a function exists. The authoritative path must execute it, expose its status/impact, and identify proxy/fallback/unavailable states.
