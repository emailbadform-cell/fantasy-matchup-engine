# Fantasy Matchup Engine 1.4.0 — Full Model

This release promotes the project from a functional architecture into a complete executable model stack.

## Included engines

- Sleeper league/roster/scoring integration
- nflverse schedule/stat ingestion
- player identity crosswalk with ID/name fallback
- historical player and team aggregation
- injury/availability and replacement logic
- offensive line / defensive front / trench matchup
- game script and play volume
- opportunity/share modeling
- route/alignment and coverage proxies
- weather / surface / referee / coaching context
- red-zone and explosive-play features
- QB correlation
- position-specific projection models
- league-specific scoring
- Monte Carlo distribution
- confidence and uncertainty
- start/sit ranking
- lineup optimization
- static model audit
- calibration metrics endpoint
- data cutoff and feature provenance
- explicit model/version registry

## API

- `/health`
- `/api/v1/status`
- `/api/v1/architecture`
- `/api/v1/fantasy/league/{league_id}/team/{username}/week/{week}/prediction`
- `/api/v1/fantasy/league/{league_id}/team/{username}/week/{week}/validation`
- `/api/v1/fantasy/league/{league_id}/team/{username}/week/{week}/start-sit`
- `/api/v1/fantasy/league/{league_id}/team/{username}/week/{week}/audit`
- `POST /api/v1/calibration/evaluate`
- `POST /api/v1/lineup/optimize`

## Important model behavior

A missing historical sample no longer means a trustworthy projection. The model explicitly reports:

- identity resolution
- historical row count
- fallback usage
- confidence
- projection status
- provenance
- audit readiness

The model remains `audit_ready=false` until real historical coverage and calibration evidence satisfy the gate.
