import csv, io, urllib.request
from pathlib import Path

CACHE = Path(__file__).resolve().parents[2] / "data_cache"
CACHE.mkdir(exist_ok=True)

class NFLVerseAPIError(RuntimeError):
    pass

class NFLVerseClient:
    SCHEDULE_URLS = [
        "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
        "https://github.com/nflverse/nflverse-data/releases/download/schedules/schedules.csv",
    ]
    PLAYER_STATS = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{season}.csv"
    PLAYER_IDS = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
    TEAM_STATS = "https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_{season}.csv"

    def __init__(self, timeout=60):
        self.timeout = timeout
        self._stats_cache = {}
        self._team_stats_cache = {}
        self._schedule_cache = {}
        self._player_ids_cache = None
        self._player_refresh_attempted = set()
        self._team_refresh_attempted = set()
        self._published_team_weeks = {}

    def _download(self, url, cache_name, force_refresh=False):
        p = CACHE / cache_name
        if not force_refresh and p.exists() and p.stat().st_size > 100:
            return p.read_bytes()
        # Support both cache layouts shipped by earlier builds, but never let an
        # alternate shipped cache defeat an explicit force_refresh. v1.8.1
        # accidentally returned the alternate cache even when force_refresh=True.
        alt = Path(__file__).resolve().parents[2] / "data" / "cache" / cache_name
        if not force_refresh and alt.exists() and alt.stat().st_size > 100:
            return alt.read_bytes()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fantasy-matchup-engine/1.4"})
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = r.read()
            p.write_bytes(data)
            return data
        except Exception as exc:
            raise NFLVerseAPIError(f"NFLverse download failed: {url}: {exc}") from exc

    @staticmethod
    def _rows(data):
        return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig", errors="replace"))))

    def schedules(self, season):
        if season in self._schedule_cache:
            return self._schedule_cache[season]
        last = None
        for i, url in enumerate(self.SCHEDULE_URLS):
            try:
                rows = self._rows(self._download(url, f"schedules_{i}.csv"))
                filtered = [r for r in rows if str(r.get("season", "")) == str(season)]
                if filtered:
                    self._schedule_cache[season] = filtered
                    return filtered
            except Exception as exc:
                last = exc
        if last:
            raise NFLVerseAPIError(str(last))
        return []

    def week_games(self, season, week):
        return [r for r in self.schedules(season) if str(r.get("week", "")) == str(week) and str(r.get("game_type", "REG")) == "REG"]

    def team_game(self, season, week, team):
        team = str(team).upper()
        aliases = {"LAR": "LA", "LVR": "LV", "OAK": "LV", "STL": "LA"}
        team = aliases.get(team, team)
        for r in self.week_games(season, week):
            if r.get("home_team") == team or r.get("away_team") == team:
                return r
        return None

    def player_stats(self, season, force_refresh=False):
        if season in self._stats_cache and not force_refresh:
            return self._stats_cache[season]
        data = self._download(
            self.PLAYER_STATS.format(season=season),
            f"stats_player_week_{season}.csv",
            force_refresh=force_refresh,
        )
        rows = self._rows(data)
        self._stats_cache[season] = rows
        self._published_team_weeks.pop(season, None)
        return rows

    @staticmethod
    def _max_week(rows):
        weeks = []
        for r in rows:
            try:
                weeks.append(int(r.get("week", 0) or 0))
            except (ValueError, TypeError):
                pass
        return max(weeks) if weeks else 0

    def _player_refresh_key(self, season, player_id=None, player_name=None, required_week=None):
        ident = str(player_id or "").strip() or str(player_name or "").strip().lower() or "dataset"
        return (int(season), ident, int(required_week or 0))

    def _ensure_player_history_fresh(self, season, through_week):
        # Dataset-level freshness is only a cheap first pass. A partially published
        # nflverse week can have max_week == required while most players are absent.
        # Player-specific verification happens in player_history below.
        if through_week is None:
            return
        required = max(0, int(through_week) - 1)
        rows = self.player_stats(season)
        key = self._player_refresh_key(season, required_week=required)
        if self._max_week(rows) >= required or key in self._player_refresh_attempted:
            return
        self._player_refresh_attempted.add(key)
        try:
            self.player_stats(season, force_refresh=True)
        except NFLVerseAPIError:
            pass

    def player_history(self, season, player_id=None, team=None, through_week=None, player_name=None):
        self._ensure_player_history_fresh(season, through_week)

        def select(rows):
            team_norm = str(team or "").upper()
            aliases = {"LAR": "LA", "LVR": "LV", "OAK": "LV", "STL": "LA"}
            team_norm = aliases.get(team_norm, team_norm)
            out = []
            for r in rows:
                rid = str(r.get("player_id", ""))
                gsis = str(r.get("gsis_id", ""))
                if player_id and str(player_id) not in {rid, gsis}:
                    continue
                if team_norm:
                    rteam = str(r.get("recent_team") or r.get("team") or "").upper()
                    if aliases.get(rteam, rteam) != team_norm:
                        continue
                if player_name:
                    # nflverse can use an abbreviated player_name (for example
                    # "D.Samuel") while player_display_name contains the full
                    # fantasy-platform name ("Deebo Samuel Sr."). Search both
                    # fields instead of letting the abbreviated field mask the
                    # display name via `or`.
                    needle = str(player_name).strip().lower()
                    names = " | ".join(str(r.get(k) or "") for k in ("player_name", "player_display_name", "display_name", "name")).lower()
                    if needle not in names:
                        continue
                try:
                    if through_week is not None and int(r.get("week", 0) or 0) >= int(through_week):
                        continue
                except (ValueError, TypeError):
                    continue
                out.append(r)
            return out

        rows = self.player_stats(season)
        out = select(rows)
        if through_week is not None and (player_id or player_name):
            required = max(0, int(through_week) - 1)
            key = self._player_refresh_key(season, player_id, player_name, required)
            if self._max_week(out) < required and key not in self._player_refresh_attempted:
                self._player_refresh_attempted.add(key)
                try:
                    rows = self.player_stats(season, force_refresh=True)
                    out = select(rows)
                except NFLVerseAPIError:
                    pass
        return out

    def player_history_status(self, season, team, rows, through_week):
        required = max(0, int(through_week or 0) - 1)
        latest = self._max_week(rows)
        if required <= 0:
            return {"status":"complete", "required_week":required, "latest_week":latest, "complete":True}
        game = self.team_game(season, required, team) if team else None
        if not game:
            # No scheduled team game in the required week: a bye is not stale data.
            return {"status":"complete_bye", "required_week":required, "latest_week":latest, "complete":True}
        complete = latest >= required
        if not complete:
            # A missing individual stat row is not proof the feed is stale.
            # Confirm the required week was published for this player's TEAM.
            # This avoids assigning DATA PENDING to inactive/DNP players while
            # retaining a fail-closed state for genuinely unpublished weeks.
            try:
                team_norm = self.normalize_team(team)
                if season not in self._published_team_weeks:
                    self._published_team_weeks[season] = {
                        (str(r.get("week") or ""), self.normalize_team(r.get("recent_team") or r.get("team")))
                        for r in self.player_stats(season)
                    }
                team_week_published = (str(required), team_norm) in self._published_team_weeks[season]
            except NFLVerseAPIError:
                team_week_published = False
            if team_week_published:
                return {"status":"player_week_unrecorded", "required_week":required,
                        "latest_week":latest, "complete":True,
                        "note":"Team weekly statistics are published, but this player has no recorded stats. May be inactive/DNP or have no qualifying production; participation not independently verified."}
        return {
            "status":"complete" if complete else "data_pending",
            "required_week":required,
            "latest_week":latest,
            "complete":complete,
            "note":None if complete else f"Team Week {required} statistics not confirmed as published; projection uses player history through Week {latest}."
        }

    @staticmethod
    def normalize_team(team):
        aliases = {"LAR":"LA", "LVR":"LV", "OAK":"LV", "STL":"LA", "SD":"LAC", "SDG":"LAC", "JAC":"JAX", "WSH":"WAS"}
        t = str(team or "").upper()
        return aliases.get(t, t)

    def team_stats(self, season, force_refresh=False):
        if season in self._team_stats_cache and not force_refresh:
            return self._team_stats_cache[season]
        data = self._download(
            self.TEAM_STATS.format(season=season),
            f"stats_team_week_{season}.csv",
            force_refresh=force_refresh,
        )
        rows = self._rows(data)
        self._team_stats_cache[season] = rows
        return rows

    def _ensure_team_history_fresh(self, season, through_week):
        if through_week is None:
            return
        required = max(0, int(through_week) - 1)
        rows = self.team_stats(season)
        if self._max_week(rows) >= required or season in self._team_refresh_attempted:
            return
        self._team_refresh_attempted.add(season)
        try:
            self.team_stats(season, force_refresh=True)
        except NFLVerseAPIError:
            pass

    def team_history(self, season, team, through_week=None):
        self._ensure_team_history_fresh(season, through_week)
        target = self.normalize_team(team)
        out=[]
        for r in self.team_stats(season):
            if self.normalize_team(r.get("team")) != target: continue
            try:
                if through_week is not None and int(r.get("week",0) or 0) >= int(through_week): continue
            except (ValueError,TypeError): continue
            out.append(r)
        return out

    def defense_history(self, season, team, through_week=None):
        target = self.normalize_team(team)
        offense = self.team_stats(season)
        player = self.player_stats(season)
        schedules = {str(r.get("game_id")): r for r in self.schedules(season)}
        defensive = {}
        for r in player:
            t=self.normalize_team(r.get("recent_team") or r.get("team"))
            if t != target: continue
            try: wk=int(r.get("week",0) or 0)
            except (ValueError,TypeError): continue
            if through_week is not None and wk >= int(through_week): continue
            k=(str(r.get("game_id")),wk)
            d=defensive.setdefault(k,{"week":wk,"game_id":str(r.get("game_id")),"def_sacks":0.0,"def_interceptions":0.0,"def_fumbles":0.0,"def_tds":0.0,"def_qb_hits":0.0,"def_pass_defended":0.0})
            for outk, ink in (("def_sacks","def_sacks"),("def_interceptions","def_interceptions"),("def_fumbles","def_fumbles"),("def_tds","def_tds"),("def_qb_hits","def_qb_hits"),("def_pass_defended","def_pass_defended")):
                try: d[outk]+=float(r.get(ink) or 0)
                except (ValueError,TypeError): pass
        rows=[]
        for r in offense:
            try: wk=int(r.get("week",0) or 0)
            except (ValueError,TypeError): continue
            if through_week is not None and wk >= int(through_week): continue
            opp=self.normalize_team(r.get("opponent_team"));
            if opp != target: continue
            # This row is the opponent's offense against the target defense.
            key=(str(r.get("game_id")),wk); d=defensive.get(key,{})
            attempts=float(r.get("attempts") or 0); carries=float(r.get("carries") or 0)
            pass_yards=float(r.get("passing_yards") or 0); rush_yards=float(r.get("rushing_yards") or 0)
            plays=max(attempts+carries,1)
            sacks=float(d.get("def_sacks",0)); ints=float(d.get("def_interceptions",0))
            rows.append({"week":wk,"game_id":str(r.get("game_id")),"opponent_team":opp,
                "passing_yards_allowed":pass_yards,"rushing_yards_allowed":rush_yards,
                "attempts_allowed":attempts,"carries_allowed":carries,"offensive_plays_allowed":plays,
                "def_sacks":sacks,"def_interceptions":ints,"def_fumbles":float(d.get("def_fumbles",0)),
                "def_tds":float(d.get("def_tds",0)),"def_qb_hits":float(d.get("def_qb_hits",0)),
                "def_pass_defended":float(d.get("def_pass_defended",0))})
        return sorted(rows,key=lambda x:x["week"])[-6:]

    def player_id_map(self):
        if self._player_ids_cache is not None: return self._player_ids_cache
        data = self._download(self.PLAYER_IDS, "players.csv")
        self._player_ids_cache = self._rows(data)
        return self._player_ids_cache

    @staticmethod
    def num(row, *names):
        for name in names:
            v = row.get(name)
            if v not in (None, ""):
                try:
                    return float(v)
                except ValueError:
                    pass
        return 0.0
