from typing import Any, Dict, List, Optional

import requests


class NFLVerseAPIError(Exception):
    """Raised when an NFLverse request fails."""


class NFLVerseClient:
    BASE_URL = "https://github.com/nflverse/nfldata/raw/master/data"

    # Sleeper/NFLverse team-code differences.
    TEAM_ALIASES = {
        "LAR": "LA",
        "LA": "LA",
        "JAX": "JAX",
        "JAC": "JAX",
        "LV": "LV",
        "LVR": "LV",
        "WAS": "WAS",
        "WSH": "WAS",
    }

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # TEAM NORMALIZATION
    # ------------------------------------------------------------------

    @classmethod
    def normalize_team(cls, team: Optional[str]) -> Optional[str]:
        """
        Normalize NFL team abbreviations so Sleeper and NFLverse
        can be compared safely.

        Examples:
            LAR -> LA
            JAC -> JAX
            LVR -> LV
            WSH -> WAS
        """
        if not team:
            return None

        normalized = str(team).strip().upper()

        if not normalized:
            return None

        return cls.TEAM_ALIASES.get(
            normalized,
            normalized,
        )

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
                f"NFLverse returned HTTP "
                f"{response.status_code}: {url}"
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

    def get_schedule(
        self,
        season: int,
    ) -> List[Dict[str, Any]]:
        """
        Return the full NFL schedule for a season.
        """

        url = (
            f"{self.BASE_URL}/schedules/"
            f"schedule_{season}.json"
        )

        data = self._get_json(url)

        if not isinstance(data, list):
            raise NFLVerseAPIError(
                f"Unexpected NFLverse schedule format "
                f"for {season}."
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
        Return every regular-season NFL game for a week.
        """

        schedule = self.get_schedule(season)

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
        Find a team's NFL game for a specific week.

        Team abbreviations are normalized before comparison.
        """

        normalized_team = self.normalize_team(team)

        if not normalized_team:
            return None

        games = self.get_week(
            season=season,
            week=week,
        )

        for game in games:
            away_team = self.normalize_team(
                game.get("away_team")
            )

            home_team = self.normalize_team(
                game.get("home_team")
            )

            if normalized_team in {
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
        Build a normalized team -> game index.

        Example:

            {
                "LAR": game,
                "LA": game,
                "LV": game,
                "KC": game
            }
        """

        games = self.get_week(
            season=season,
            week=week,
        )

        team_index: Dict[str, Dict[str, Any]] = {}

        for game in games:
            away_team = self.normalize_team(
                game.get("away_team")
            )

            home_team = self.normalize_team(
                game.get("home_team")
            )

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

        normalized_team = self.normalize_team(team)

        if not normalized_team:
            return None

        game = self.get_team_game(
            season=season,
            week=week,
            team=normalized_team,
        )

        if not game:
            return None

        away_team = self.normalize_team(
            game.get("away_team")
        )

        home_team = self.normalize_team(
            game.get("home_team")
        )

        if away_team == normalized_team:
            return home_team

        if home_team == normalized_team:
            return away_team

        return None
