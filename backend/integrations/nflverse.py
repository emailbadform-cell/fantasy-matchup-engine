from csv import DictReader
from io import StringIO
from typing import Any, Dict, List, Optional

import requests


class NFLVerseAPIError(Exception):
    """Raised when an NFLverse request fails."""


class NFLVerseClient:
    """
    Client for NFLverse schedule/game data.

    NFLverse's current schedule data is maintained in the
    nflverse/nfldata repository as data/games.csv.
    """

    BASE_URL = (
        "https://raw.githubusercontent.com/"
        "nflverse/nfldata/master/data/games.csv"
    )

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # INTERNAL REQUEST
    # ------------------------------------------------------------------

    def _get_csv(self, url: str) -> List[Dict[str, Any]]:
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
                f"NFLverse returned HTTP "
                f"{response.status_code}: {url}"
            )

        try:
            text = response.text
            reader = DictReader(StringIO(text))
            return list(reader)
        except Exception as exc:
            raise NFLVerseAPIError(
                f"NFLverse returned invalid CSV: {url}"
            ) from exc

    # ------------------------------------------------------------------
    # SCHEDULE
    # ------------------------------------------------------------------

    def get_schedule(self, season: int) -> List[Dict[str, Any]]:
        """
        Return the NFL schedule for a season.

        NFLverse currently maintains the schedule in the
        consolidated games.csv dataset.
        """

        rows = self._get_csv(self.BASE_URL)

        season_string = str(season)

        games: List[Dict[str, Any]] = []

        for row in rows:
            row_season = str(
                row.get("season", "")
            ).strip()

            if row_season != season_string:
                continue

            games.append(
                dict(row)
            )

        return games

    # ------------------------------------------------------------------
    # WEEK
    # ------------------------------------------------------------------

    def get_week(
        self,
        season: int,
        week: int,
    ) -> List[Dict[str, Any]]:
        """
        Return every regular-season NFL game
        for a specific week.
        """

        schedule = self.get_schedule(
            season=season
        )

        week_string = str(week)

        games: List[Dict[str, Any]] = []

        for game in schedule:
            game_week = str(
                game.get("week", "")
            ).strip()

            game_type = str(
                game.get("game_type", "")
            ).strip().upper()

            if (
                game_week == week_string
                and game_type == "REG"
            ):
                games.append(
                    game
                )

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
        Find a team's NFL game during a specific week.
        """

        team = str(team).upper().strip()

        if not team:
            return None

        games = self.get_week(
            season=season,
            week=week,
        )

        for game in games:
            away_team = str(
                game.get("away_team", "")
            ).upper().strip()

            home_team = str(
                game.get("home_team", "")
            ).upper().strip()

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
        Build a team -> game lookup index.

        Example:

            {
                "LV": {...},
                "KC": {...},
                "DET": {...},
                ...
            }
        """

        games = self.get_week(
            season=season,
            week=week,
        )

        team_index: Dict[str, Dict[str, Any]] = {}

        for game in games:
            away_team = str(
                game.get("away_team", "")
            ).upper().strip()

            home_team = str(
                game.get("home_team", "")
            ).upper().strip()

            if away_team:
                team_index[away_team] = game

            if home_team:
                team_index[home_team] = game

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

        team = str(team).upper().strip()

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
        ).upper().strip()

        home_team = str(
            game.get("home_team", "")
        ).upper().strip()

        if away_team == team:
            return home_team or None

        if home_team == team:
            return away_team or None

        return None
