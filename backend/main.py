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


@app.get("/api/v1/sleeper/league/{league_id}/rosters/enriched")
def sleeper_enriched_rosters(league_id: str):
    client = SleeperClient()

    try:
        rosters = client.get_rosters(league_id)
        users = client.get_users(league_id)
        players = client.get_players()

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

        enriched_players = []

        for player_id in roster.get("players", []):
            player = players.get(str(player_id))

            enriched_players.append(
                {
                    "player_id": player_id,
                    "name": player.get("full_name") if player else None,
                    "first_name": player.get("first_name") if player else None,
                    "last_name": player.get("last_name") if player else None,
                    "position": player.get("position") if player else None,
                    "team": player.get("team") if player else None,
                    "status": player.get("status") if player else None,
                    "injury_status": (
                        player.get("injury_status")
                        if player
                        else None
                    ),
                    "fantasy_positions": (
                        player.get("fantasy_positions", [])
                        if player
                        else []
                    ),
                    "active": player.get("active") if player else None,
                }
            )

        enriched_starters = []

        for player_id in roster.get("starters", []):
            player = players.get(str(player_id))

            enriched_starters.append(
                {
                    "player_id": player_id,
                    "name": player.get("full_name") if player else None,
                    "position": player.get("position") if player else None,
                    "team": player.get("team") if player else None,
                }
            )

        enriched_reserve = []

        for player_id in roster.get("reserve") or []:
            player = players.get(str(player_id))

            enriched_reserve.append(
                {
                    "player_id": player_id,
                    "name": player.get("full_name") if player else None,
                    "position": player.get("position") if player else None,
                    "team": player.get("team") if player else None,
                }
            )

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
                "players": enriched_players,
                "starters": enriched_starters,
                "reserve": enriched_reserve,
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


@app.get("/api/v1/sleeper/league/{league_id}/matchups/{week}")
def sleeper_matchups(league_id: str, week: int):
    client = SleeperClient()

    if week < 1 or week > 18:
        raise HTTPException(
            status_code=400,
            detail="NFL week must be between 1 and 18.",
        )

    try:
        matchups = client.get_matchups(
            league_id=league_id,
            week=week,
        )
    except SleeperAPIError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        "platform": "sleeper",
        "league_id": league_id,
        "week": week,
        "matchup_count": len(matchups),
        "matchups": matchups,
    }


@app.get("/api/v1/sleeper/league/{league_id}/matchups/{week}/enriched")
def sleeper_enriched_matchups(league_id: str, week: int):
    client = SleeperClient()

    if week < 1 or week > 18:
        raise HTTPException(
            status_code=400,
            detail="NFL week must be between 1 and 18.",
        )

    try:
        matchups = client.get_matchups(
            league_id=league_id,
            week=week,
        )
        users = client.get_users(league_id)
        rosters = client.get_rosters(league_id)

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

    roster_map = {
        roster.get("roster_id"): roster
        for roster in rosters
        if roster.get("roster_id") is not None
    }

    enriched_matchups = []

    for matchup in matchups:
        roster_id = matchup.get("roster_id")
        roster = roster_map.get(roster_id)

        owner_id = roster.get("owner_id") if roster else None
        owner = user_map.get(owner_id)

        enriched_matchups.append(
            {
                "matchup_id": matchup.get("matchup_id"),
                "roster_id": roster_id,
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
                "points": matchup.get("points"),
                "players_points": matchup.get("players_points"),
                "starters_points": matchup.get("starters_points"),
                "starters": matchup.get("starters"),
            }
        )

    return {
        "platform": "sleeper",
        "league_id": league_id,
        "week": week,
        "matchup_count": len(enriched_matchups),
        "matchups": enriched_matchups,
    }


@app.get(
    "/api/v1/sleeper/league/{league_id}/matchups/{week}/team/{username}"
)
def sleeper_team_matchup(
    league_id: str,
    week: int,
    username: str,
):
    client = SleeperClient()

    if week < 1 or week > 18:
        raise HTTPException(
            status_code=400,
            detail="NFL week must be between 1 and 18.",
        )

    try:
        user = client.get_user(username)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Sleeper user not found.",
            )

        rosters = client.get_rosters(league_id)
        users = client.get_users(league_id)
        matchups = client.get_matchups(
            league_id=league_id,
            week=week,
        )

    except SleeperAPIError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    user_id = user.get("user_id")

    user_map = {
        league_user.get("user_id"): league_user
        for league_user in users
        if league_user.get("user_id")
    }

    roster_map = {
        roster.get("roster_id"): roster
        for roster in rosters
        if roster.get("roster_id") is not None
    }

    target_roster = None

    for roster in rosters:
        if roster.get("owner_id") == user_id:
            target_roster = roster
            break

    if not target_roster:
        raise HTTPException(
            status_code=404,
            detail="User roster not found in this league.",
        )

    target_roster_id = target_roster.get("roster_id")

    target_matchup = None

    for matchup in matchups:
        if matchup.get("roster_id") == target_roster_id:
            target_matchup = matchup
            break

    if not target_matchup:
        raise HTTPException(
            status_code=404,
            detail="No matchup found for this roster and week.",
        )

    matchup_id = target_matchup.get("matchup_id")

    if matchup_id is None:
        raise HTTPException(
            status_code=404,
            detail="Roster does not currently have a matchup ID.",
        )

    opponent_matchup = None

    for matchup in matchups:
        if (
            matchup.get("matchup_id") == matchup_id
            and matchup.get("roster_id") != target_roster_id
        ):
            opponent_matchup = matchup
            break

    if not opponent_matchup:
        raise HTTPException(
            status_code=404,
            detail="Opponent matchup not found.",
        )

    opponent_roster_id = opponent_matchup.get("roster_id")
    opponent_roster = roster_map.get(opponent_roster_id)

    target_owner = user_map.get(target_roster.get("owner_id"))
    opponent_owner = (
        user_map.get(opponent_roster.get("owner_id"))
        if opponent_roster
        else None
    )

    return {
        "platform": "sleeper",
        "league_id": league_id,
        "week": week,
        "matchup_id": matchup_id,
        "team": {
            "roster_id": target_roster_id,
            "owner_id": target_roster.get("owner_id"),
            "username": (
                target_owner.get("username")
                if target_owner
                else username
            ),
            "display_name": (
                target_owner.get("display_name")
                if target_owner
                else None
            ),
            "points": target_matchup.get("points"),
            "players_points": target_matchup.get("players_points"),
            "starters": target_matchup.get("starters"),
            "starters_points": target_matchup.get(
                "starters_points"
            ),
        },
        "opponent": {
            "roster_id": opponent_roster_id,
            "owner_id": (
                opponent_roster.get("owner_id")
                if opponent_roster
                else None
            ),
            "username": (
                opponent_owner.get("username")
                if opponent_owner
                else None
            ),
            "display_name": (
                opponent_owner.get("display_name")
                if opponent_owner
                else None
            ),
            "points": opponent_matchup.get("points"),
            "players_points": opponent_matchup.get(
                "players_points"
            ),
            "starters": opponent_matchup.get("starters"),
            "starters_points": opponent_matchup.get(
                "starters_points"
            ),
        },
    }
