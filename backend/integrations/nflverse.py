from csv import DictReader
from io import StringIO
from typing import Any, Dict, List, Optional

import requests


class NFLVerseAPIError(Exception):
    """Raised when an NFLverse request fails."""


class NFLVerseClient:
    """
    Client for NFLverse schedule/game data.

    NFLverse maintains schedule information in games.csv.
    """

    BASE_URL = (
        "https://raw.githubusercontent.com/"
        "nflverse/nfldata/master/data/games.csv"
    )

    # ------------------------------------------------------------------
    # NFL TEAM CODE NORMALIZATION
    # ------------------------------------------------------------------

    TEAM_ALIASES = {
        # Sleeper commonly uses LAR.
        # NFLverse games data can use LA.
        "LAR": "LA",

        # Keep this extensible for other data-source differences.
        "JAC": "JAX",
    }

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # INTERNAL REQUEST
    # ------------------------------------------------------------------

    def _get_csv(
        self,
        url: str,
    ) -> List[Dict[str, Any]]:
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
            reader = DictReader(
                StringIO(response.text)
            )

            return list(reader)

        except Exception as exc:
            raise NFLVerseAPIError(
                f"NFLverse returned invalid CSV: {url}"
            ) from exc

    # ------------------------------------------------------------------
    # TEAM NORMALIZATION
    # ------------------------------------------------------------------

    def normalize_team(
        self,
        team: str,
    ) -> str:
        """
        Convert a team abbreviation from an external source
        into the abbreviation used by the NFLverse games dataset.

        Examples:

            LAR -> LA
            JAC -> JAX
            KC  -> KC
            LV  -> LV
        """

        team = str(team).upper().strip()

        return self.TEAM_ALIASES.get(
            team,
            team,
        )

    # ------------------------------------------------------------------
    # SCHEDULE
    # ------------------------------------------------------------------

    def get_schedule(
        self,
        season: int,
    ) -> List[Dict[str, Any]]:
        """
        Return the NFL schedule for a season.
        """

        rows = self._get_csv(
            self.BASE_URL
        )

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
        Find a team's game during a specific NFL week.

        External sources such as Sleeper may use a different
        abbreviation than NFLverse. Team aliases are normalized
        before searching.
        """

        requested_team = str(
            team
        ).upper().strip()

        if not requested_team:
            return None

        normalized_team = self.normalize_team(
            requested_team
        )

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
        Build a team -> game lookup index.

        The index contains both the NFLverse team code and
        supported external aliases.

        Example:

            {
                "LA": game,
                "LAR": game,
                "LV": game,
                "KC": game,
                ...
            }
        """

        games = self.get_week(
            season=season,
            week=week,
        )

        team_index: Dict[
            str,
            Dict[str, Any],
        ] = {}

        for game in games:
            away_team = str(
                game.get("away_team", "")
            ).upper().strip()

            home_team = str(
                game.get("home_team", "")
            ).upper().strip()

            if away_team:
                team_index[
                    away_team
                ] = game

            if home_team:
                team_index[
                    home_team
                ] = game

            # Add reverse aliases so callers can use
            # Sleeper-style abbreviations.
            for external_team, nflverse_team in (
                self.TEAM_ALIASES.items()
            ):
                if away_team == nflverse_team:
                    team_index[
                        external_team
                    ] = game

                if home_team == nflverse_team:
                    team_index[
                        external_team
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

        The returned team code is normalized for the external
        caller, so LAR is returned as LAR rather than LA.
        """

        requested_team = str(
            team
        ).upper().strip()

        if not requested_team:
            return None

        normalized_team = self.normalize_team(
            requested_team
        )

        game = self.get_team_game(
            season=season,
            week=week,
            team=requested_team,
        )

        if not game:
            return None

        away_team = str(
            game.get("away_team", "")
        ).upper().strip()

        home_team = str(
            game.get("home_team", "")
        ).upper().strip()

        opponent = None

        if away_team == normalized_team:
            opponent = home_team

        elif home_team == normalized_team:
            opponent = away_team

        if not opponent:
            return None

        # Convert NFLverse code back to the caller's
        # preferred external code.
        for external_team, nflverse_team in (
            self.TEAM_ALIASES.items()
        ):
            if opponent == nflverse_team:
                return external_team

        return opponent
