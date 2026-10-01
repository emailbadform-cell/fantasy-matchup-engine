# Fantasy Matchup Engine

Clean foundation for the fantasy football matchup and lineup optimization application.

## Initial scope

- Backend API foundation
- Frontend foundation
- Projection-engine interfaces
- Lineup-optimizer interfaces
- Tests
- Render deployment configuration
- Secret/data hygiene

## Data hygiene

User credentials, ESPN/Sleeper session data, raw datasets, caches, logs, databases, uploads, and build artifacts are not committed to this repository.

## Development

Backend:

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Tests:

```bash
pytest
```
