"""Sleeper API integration."""

from __future__ import annotations

from typing import Any

import requests


BASE_URL = "https://api.sleeper.app/v1"


class SleeperAPIError(Exception):
    """Raised when a Sleeper API request fails."""


class SleeperClient:
    """Read-only client for the Sleeper fantasy API."""

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    def _get(self, endpoint: str) -> Any:
        url = f"{BASE_URL}{endpoint}"

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SleeperAPIError(
                f"Sleeper API request failed: {endpoint}"
            ) from exc

        return response.json()

    def get_user(self, username: str) -> dict[str, Any]:
        """Resolve a Sleeper username to its user information."""
        return self._get(f"/user/{username}")

    def get_leagues(
        self,
        user_id: str,
        season: str,
        sport: str = "nfl",
    ) -> list[dict[str, Any]]:
        """Return the user's leagues for a season."""
        return self._get(f"/user/{user_id}/leagues/{sport}/{season}")

    def get_league(self, league_id: str) -> dict[str, Any]:
        """Return league information."""
        return self._get(f"/league/{league_id}")

    def get_rosters(self, league_id: str) -> list[dict[str, Any]]:
        """Return all rosters in a league."""
        return self._get(f"/league/{league_id}/rosters")

    def get_users(self, league_id: str) -> list[dict[str, Any]]:
        """Return all users in a league."""
        return self._get(f"/league/{league_id}/users")

    def get_matchups(
        self,
        league_id: str,
        week: int,
    ) -> list[dict[str, Any]]:
        """Return matchup information for a week."""
        return self._get(f"/league/{league_id}/matchups/{week}")
