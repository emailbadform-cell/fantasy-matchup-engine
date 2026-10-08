# FME v1.9.25 — Individual Player Projections

Adds POST `/api/v1/players/project` and a multi-player dashboard input (up to 20 names). Uses the existing `PredictionEngine.project_candidate` path, the same model as waiver candidate evaluation. Supports standard/PPR/half-PPR without a league; when a league projection has been loaded, the dashboard passes its platform and league scoring context. ESPN requires a valid team ID. Names must resolve uniquely; ambiguity fails closed. Input accepts one player per line or semicolon separated; optional `(DEN)` team disambiguation. No roster modifications.

Apply on top of v1.9.24. Reload the page after deployment. The model still has the scoring coverage limitations noted in v1.9.24.
