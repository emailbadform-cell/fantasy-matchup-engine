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


@app.get("/api/v1/sleeper/leagues/{username}/{season}")
def sleeper_leagues(username: str, season: str):
    client = SleeperClient()

    try:
        user = client.get_user(username)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Sleeper user not found",
            )

        leagues = client.get_leagues(
            user_id=user["user_id"],
            season=season,
            sport="nfl",
        )

    except SleeperAPIError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        "platform": "sleeper",
        "username": user.get("username"),
        "user_id": user.get("user_id"),
        "season": season,
        "league_count": len(leagues),
        "leagues": leagues,
    }


@app.get("/api/v1/sleeper/league/{league_id}/rosters")
def sleeper_rosters(league_id: str):
    client = SleeperClient()

    try:
        rosters = client.get_rosters(league_id)
        users = client.get_users(league_id)

    except SleeperAPIError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    user_map = {
        user.get("user_id"): user
        for user in users
        if user.get("user_id")
    }

    enriched_rosters = []

    for roster in rosters:
        owner_id = roster.get("owner_id")
        owner = user_map.get(owner_id)

        enriched_rosters.append(
            {
                "roster_id": roster.get("roster_id"),
                "owner_id": owner_id,
                "owner_username": (
                    owner.get("display_name")
                    if owner
                    else None
                ),
                "owner_username_normalized": (
                    owner.get("username")
                    if owner
                    else None
                ),
                "players": roster.get("players", []),
                "starters": roster.get("starters", []),
                "reserve": roster.get("reserve", []),
                "settings": roster.get("settings", {}),
                "metadata": roster.get("metadata", {}),
            }
        )

    return {
        "platform": "sleeper",
        "league_id": league_id,
        "roster_count": len(enriched_rosters),
        "rosters": enriched_rosters,
    }


@app.get("/api/v1/sleeper/players")
def sleeper_players():
    client = SleeperClient()

    try:
        players = client.get_players()
    except SleeperAPIError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        "platform": "sleeper",
        "player_count": len(players),
        "players": players,
    }
