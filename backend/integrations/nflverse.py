from typing import Any, Dict, List, Optional

import requests


class NFLVerseAPIError(Exception):
    """Raised when an NFLverse request fails."""


class NFLVerseClient:
    BASE_URL = "https://github.com/nflverse/nfldata/raw/master/data"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()

    def _get_json(self, url: str) -> Any:
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise NFLVerseAPIError(
                f"NFLverse request failed: {exc}"
            ) from exc

        if response.status_code != 200:
            raise NFLVerseAPIError(
                f"NFLverse returned HTTP {response.status_code}: {url}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise NFLVerseAPIError(
                f"NFLverse returned invalid JSON: {url}"
            ) from exc

    def get_schedule(
        self,
        season: int,
    ) -> List[Dict[str, Any]]:
        """Return the full NFL schedule for a season."""
        url = f"{self.BASE_URL}/schedules/schedule_{season}.json"

        data = self._get_json(url)

        if not isinstance(data, list):
            raise NFLVerseAPIError(
                f"Unexpected NFLverse schedule format for {season}."
            )

        return data

    def get_week(
        self,
        season: int,
        week: int,
    ) -> List[Dict[str, Any]]:
        """Return every regular-season NFL game for a specific week."""
        schedule = self.get_schedule(
            season=season,
        )

        week_string = str(week)

        games: List[Dict[str, Any]] = []

        for game in schedule:
            game_week = str(
                game.get("week", "")
            )

            game_type = str(
                game.get("game_type", "")
            ).upper()

            if (
                game_week == week_string
                and game_type == "REG"
            ):
                games.append(game)

        return games

    def get_team_game(
        self,
        season: int,
        week: int,
        team: str,
    ) -> Optional[Dict[str, Any]]:
        """Find a team's game during a specific NFL week."""
        team = team.upper().strip()

        if not team:
            return None

        games = self.get_week(
            season=season,
            week=week,
        )

        for game in games:
            away_team = str(
                game.get("away_team", "")
            ).upper()

            home_team = str(
                game.get("home_team", "")
            ).upper()

            if team in {
                away_team,
                home_team,
            }:
                return game

        return None

    def get_week_team_index(
        self,
        season: int,
        week: int,
    ) -> Dict[str, Dict[str, Any]]:
        """Build a team-code-to-game index for a specific week."""
        games = self.get_week(
            season=season,
            week=week,
        )

        team_index: Dict[str, Dict[str, Any]] = {}

        for game in games:
            away_team = game.get("away_team")
            home_team = game.get("home_team")

            if away_team:
                team_index[
                    str(away_team).upper()
                ] = game

            if home_team:
                team_index[
                    str(home_team).upper()
                ] = game

        return team_index

    def get_team_opponent(
        self,
        season: int,
        week: int,
        team: str,
    ) -> Optional[str]:
        """Return the opposing NFL team code."""
        team = team.upper().strip()

        if not team:
            return None

        game = self.get_team_game(
            season=season,
            week=week,
            team=team,
        )

        if not game:
            return None

        away_team = str(
            game.get("away_team", "")
        ).upper()

        home_team = str(
            game.get("home_team", "")
        ).upper()

        if away_team == team:
            return home_team

        if home_team == team:
            return away_team

        return None
