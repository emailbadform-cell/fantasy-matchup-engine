# Fantasy Matchup Dashboard

A lightweight responsive frontend for the Fantasy Matchup Engine.

## What it does
- Calls the existing `/api/v1/fantasy/.../prediction` endpoint.
- Converts the raw JSON into a dashboard.
- Shows projected lineup total, player projections, confidence, and expandable factor details.
- Requires no npm/node build step.

## Integration
Place `index.html` in a FastAPI static/frontend directory and mount it with FastAPI's StaticFiles, or copy the HTML into the existing frontend route.

The dashboard expects the API endpoint:
`/api/v1/fantasy/league/{league_id}/team/{username}/week/{week}/prediction`

Default test values are the current Week 4 Sleeper test league.
