import time
import httpx

BASE = "https://api.sleeper.app/v1"

class SleeperAPIError(RuntimeError):
    pass

class SleeperClient:
    def __init__(self, timeout=30):
        self.timeout = timeout

    def _get(self, path):
        try:
            r = httpx.get(BASE + path, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise SleeperAPIError(f"Sleeper request failed: {path}: {exc}") from exc

    def get_user(self, username):
        return self._get(f"/user/{username}")

    def get_rosters(self, league_id):
        return self._get(f"/league/{league_id}/rosters")

    def get_users(self, league_id):
        return self._get(f"/league/{league_id}/users")

    def get_matchups(self, league_id, week):
        return self._get(f"/league/{league_id}/matchups/{week}")

    def get_players(self):
        return self._get("/players/nfl")

    def get_league(self, league_id):
        return self._get(f"/league/{league_id}")

    def get_scoring_settings(self, league_id):
        # Sleeper exposes scoring_settings as a field on the league object;
        # /league/{league_id}/scoring_settings is not a supported endpoint.
        league = self.get_league(league_id)
        settings = league.get("scoring_settings") if isinstance(league, dict) else None
        return settings if isinstance(settings, dict) else {}
