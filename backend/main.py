from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.integrations.sleeper import SleeperAPIError, SleeperClient


app = FastAPI(
    title="Fantasy Matchup Engine",
    version="0.1.0",
    description="Fantasy football matchup, projection, and lineup optimization API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/status")
def status():
    return {
        "app": "fantasy-matchup-engine",
        "version": "0.1.0",
        "projection_models": [
            "original",
            "cb_challenger",
            "full_cb_challenger",
        ],
        "status": "foundation_ready",
    }


@app.get("/api/v1/sleeper/user/{username}")
def sleeper_user(username: str):
    client = SleeperClient()

    try:
        user = client.get_user(username)
    except SleeperAPIError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Sleeper user not found",
        )

    return {
        "platform": "sleeper",
        "user": user,
    }
