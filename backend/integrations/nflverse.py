"""NFL schedule integration using the live nflverse schedule dataset."""

from __future__ import annotations

import csv
import io
from typing import Any

import requests


SCHEDULE_URL = (
    "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
)


class NFLVerseAPIError(Exception):
    """Raised when the nflverse schedule cannot be retrieved."""


class NFLVerseClient:
    """Read-only client for the nflverse NFL schedule."""

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout

    def get_schedule(self, season: int | None = None) -> list[dict[str, Any]]:
        try:
            response = requests.get(
                SCHEDULE_URL,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise NFLVerseAPIError(
                "Unable to retrieve the nflverse NFL schedule."
            ) from exc

        try:
            rows = list(
                csv.DictReader(
                    io.StringIO(response.text)
                )
            )
        except (csv.Error, TypeError, ValueError) as exc:
            raise NFLVerseAPIError(
                "Unable to parse the nflverse schedule."
            ) from exc

        if season is not None:
            rows = [
                row
                for row in rows
                if str(row.get("season", "")) == str(season)
            ]

        return rows

    def get_week(
        self,
        season: int,
        week: int,
    ) -> list[dict[str, Any]]:
        rows = self.get_schedule(season)

        return [
            row
            for row in rows
            if str(row.get("week", "")) == str(week)
            and row.get("game_type") == "REG"
        ]

    def get_team_game(
        self,
        season: int,
        week: int,
        team: str,
    ) -> dict[str, Any] | None:
        team = team.upper()

        games = self.get_week(
            season=season,
            week=week,
        )

        for game in games:
            if (
                game.get("away_team", "").upper() == team
                or game.get("home_team", "").upper() == team
            ):
                return game

        return None

    def get_team_opponent(
        self,
        season: int,
        week: int,
        team: str,
    ) -> str | None:
        game = self.get_team_game(
            season=season,
            week=week,
            team=team,
        )

        if not game:
            return None

        team = team.upper()

        away_team = game.get("away_team", "").upper()
        home_team = game.get("home_team", "").upper()

        if away_team == team:
            return home_team

        if home_team == team:
            return away_team

        return None
