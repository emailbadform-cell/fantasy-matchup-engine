```python
from typing import Any, Dict, List, Optional

import requests


class NFLVerseAPIError(Exception):
    """Raised when an NFLverse request fails."""


class NFLVerseClient:
    BASE_URL = "https://github.com/nflverse/nfldata/raw/master/data"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # INTERNAL REQUEST
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # SCHEDULE
    # ------------------------------------------------------------------

    def get_schedule(self, season: int) -> List[Dict[str, Any]]:
        """
        Return the full NFL schedule for a season.

        NFLverse publishes the schedule as a JSON file.
        """
        url = (
            f"{self.BASE_URL}/schedules/schedule_{season}.json"
        )

        data = self._get_json(url)

        if not isinstance(data, list):
            raise NFLVerseAPIError(
                f"Unexpected NFLverse schedule format for {season}."
            )

        return data

    # ------------------------------------------------------------------
    # WEEK
    # ------------------------------------------------------------------

    def get_week(
        self,
        season: int,
        week: int,
    ) -> List[Dict[str, Any]]:
        """
        Return every NFL game for a specific regular-season week.
        """
        schedule = self.get_schedule(season)

        week_string = str(week)

        games = []

        for game in schedule:
            game_week = str(game.get("week", ""))

            game_type = str(
                game.get("game_type", "")
            ).upper()

            if (
                game_week == week_string
                and game_type == "REG"
            ):
                games.append(game)

        return games

    # ------------------------------------------------------------------
    # TEAM GAME
    # ------------------------------------------------------------------

    def get_team_game(
        self,
        season: int,
        week: int,
        team: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a team's game during a specific NFL week.

        This intentionally searches the complete weekly schedule
        rather than relying on a team-specific endpoint.
        """

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

    # ------------------------------------------------------------------
    # TEAM SCHEDULE INDEX
    # ------------------------------------------------------------------

    def get_week_team_index(
        self,
        season: int,
        week: int,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build:

            {
                "LAR": game,
                "LV": game,
                "KC": game,
                ...
            }

        This allows the fantasy engine to resolve all players'
        opponents from one schedule download.
        """

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

    # ------------------------------------------------------------------
    # TEAM OPPONENT
    # ------------------------------------------------------------------

    def get_team_opponent(
        self,
        season: int,
        week: int,
        team: str,
    ) -> Optional[str]:
        """
        Return the opposing NFL team code.
        """

        team = team.upper().strip()

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
```
