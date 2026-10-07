from statistics import mean


def f(x, d=0.0):
    try:
        if x in (None, "", "NA", "nan"): return d
        return float(x)
    except (TypeError, ValueError):
        return d


def first(row, names, default=0.0):
    for n in names:
        if n in row and row.get(n) not in (None, ""):
            return f(row.get(n), default)
    return default


PLAYER_ALIASES = {
    "player_id": ["player_id", "gsis_id"],
    "team": ["recent_team", "team", "posteam"],
    "attempts": ["attempts", "passing_attempts", "pass_attempts"],
    "completions": ["completions"],
    "passing_yards": ["passing_yards", "pass_yards"],
    "passing_tds": ["passing_tds", "pass_tds"],
    "interceptions": ["interceptions", "passing_interceptions", "pass_interceptions"],
    "carries": ["carries", "rushing_attempts", "rush_attempts"],
    "rushing_yards": ["rushing_yards", "rush_yards"],
    "rushing_tds": ["rushing_tds", "rush_tds"],
    "targets": ["targets", "receiving_targets"],
    "receptions": ["receptions", "rec"],
    "receiving_yards": ["receiving_yards", "rec_yards"],
    "receiving_tds": ["receiving_tds", "rec_tds"],
    "receiving_air_yards": ["receiving_air_yards", "air_yards"],
    "target_share": ["target_share"],
    "air_yards_share": ["air_yards_share"],
    "sacks": ["sacks"],
    "fumbles_lost": ["fumbles_lost", "receiving_fumbles_lost", "rushing_fumbles_lost"],
    "fantasy_points": ["fantasy_points", "fantasy_points_ppr"],
    "field_goals": ["field_goals", "fg_made", "fgm", "field_goal_made"],
    "field_goal_attempts": ["field_goal_attempts", "fg_attempts", "fga"],
    "extra_points": ["extra_points", "xp_made", "xpm", "extra_points_made"],
    "extra_point_attempts": ["extra_point_attempts", "xp_attempts", "xpa"],
}


def normalize_player_row(r):
    out = dict(r)
    for key, aliases in PLAYER_ALIASES.items():
        out[key] = first(r, aliases, 0.0)
    out["player_id"] = str(r.get("player_id") or r.get("gsis_id") or "")
    out["team"] = str(r.get("recent_team") or r.get("team") or r.get("posteam") or "").upper()
    out["season"] = int(f(r.get("season"), 0))
    out["week"] = int(f(r.get("week"), 0))
    return out


class FeatureStore:
    def normalize_player_rows(self, rows):
        return [normalize_player_row(r) for r in (rows or []) if isinstance(r, dict)]

    def _history(self, rows, player_id, season, through_week):
        out=[]
        for raw in rows:
            r = normalize_player_row(raw)
            if str(r.get("player_id")) != str(player_id): continue
            rs = r.get("season", 0); rw = r.get("week", 0)
            if rs == int(season) and rw < int(through_week): out.append(r)
            elif rs < int(season): out.append(r)
        return sorted(out,key=lambda x:(x.get("season",0),x.get("week",0)))

    def rolling_player(self,rows,player_id,season,through_week,windows=(3,6,12)):
        h=self._history(rows,player_id,season,through_week)
        keys=[
            "attempts","completions","passing_yards","passing_tds","interceptions",
            "targets","receptions","receiving_yards","receiving_tds","receiving_air_yards",
            "target_share","air_yards_share","carries","rushing_yards","rushing_tds",
            "field_goals","field_goal_attempts","extra_points","extra_point_attempts",
            "fantasy_points","sacks","fumbles_lost"
        ]
        out={}
        for w in windows:
            x=h[-w:]
            out[w]={k:(mean(f(r.get(k)) for r in x) if x else 0.0) for k in keys}
            out[w]["games"] = len(x)
            # Derived efficiency metrics are computed after aggregation, not averaged incorrectly.
            attempts=sum(f(r.get("attempts")) for r in x)
            out[w]["yards_per_attempt"] = (sum(f(r.get("passing_yards")) for r in x)/attempts) if attempts else 0.0
            out[w]["catch_rate"] = (sum(f(r.get("receptions")) for r in x)/sum(f(r.get("targets")) for r in x)) if sum(f(r.get("targets")) for r in x) else 0.0
            out[w]["yards_per_target"] = (sum(f(r.get("receiving_yards")) for r in x)/sum(f(r.get("targets")) for r in x)) if sum(f(r.get("targets")) for r in x) else 0.0
            out[w]["yards_per_carry"] = (sum(f(r.get("rushing_yards")) for r in x)/sum(f(r.get("carries")) for r in x)) if sum(f(r.get("carries")) for r in x) else 0.0
        return out

    def latest_player(self,rows,player_id,season,through_week):
        h=self._history(rows,player_id,season,through_week)
        return h[-1] if h else {}

    def team_games(self,rows,team,season,through_week,windows=(3,6,12)):
        t=str(team).upper(); t={"LAR":"LA","LVR":"LV","JAC":"JAX","WSH":"WAS"}.get(t,t)
        normalized=self.normalize_player_rows(rows)
        weekly={}
        for r in normalized:
            if r.get("team") != t: continue
            rs,rw=r.get("season",0),r.get("week",0)
            if rs > int(season) or (rs == int(season) and rw >= int(through_week)): continue
            key=(rs,rw)
            d=weekly.setdefault(key,{"plays":0,"attempts":0,"carries":0,"targets":0,"passing_yards":0,"rushing_yards":0,"receiving_yards":0,"passing_tds":0,"rushing_tds":0,"receiving_tds":0,"points_for":0})
            d["attempts"] += f(r.get("attempts")); d["carries"] += f(r.get("carries")); d["targets"] += f(r.get("targets"))
            d["passing_yards"] += f(r.get("passing_yards")); d["rushing_yards"] += f(r.get("rushing_yards")); d["receiving_yards"] += f(r.get("receiving_yards"))
            d["passing_tds"] += f(r.get("passing_tds")); d["rushing_tds"] += f(r.get("rushing_tds")); d["receiving_tds"] += f(r.get("receiving_tds"))
        keys=sorted(weekly)
        for k,d in weekly.items():
            d["plays"] = d["attempts"] + d["carries"]
            d["pass_rate"] = d["attempts"]/d["plays"] if d["plays"] else .58
            d["rush_rate"] = d["carries"]/d["plays"] if d["plays"] else .42
            d["explosive_rate"] = 1.0
            d["red_zone_rate"] = 1.0
        out={}
        for w in windows:
            x=[weekly[k] for k in keys[-w:]]
            out[w]={k:(mean(f(r.get(k)) for r in x) if x else 0.0) for k in ["plays","pass_rate","rush_rate","points_for","explosive_rate","red_zone_rate"]}
            out[w]["pace"] = out[w]["plays"] / 60 if x else 1.0
            out[w]["target_concentration"] = 1.0
        return out

    def rolling_team(self,rows,team,season,through_week,window=6):
        t=str(team).upper(); t={"LAR":"LA","LVR":"LV","JAC":"JAX","WSH":"WAS"}.get(t,t)
        normalized=[]
        for raw in rows or []:
            if not isinstance(raw,dict): continue
            r=dict(raw)
            rt=str(r.get("team") or r.get("defteam") or "").upper(); rt={"LAR":"LA","LVR":"LV","JAC":"JAX","WSH":"WAS"}.get(rt,rt)
            if rt!=t: continue
            rs,rw=int(f(r.get("season"),0)),int(f(r.get("week"),0))
            if rs==int(season) and rw>=int(through_week): continue
            normalized.append(r)
        normalized=sorted(normalized,key=lambda x:(f(x.get("season")),f(x.get("week"))))[-window:]
        keys=["sacks","interceptions","fumble_recoveries","fumbles_lost","def_tds","points_against","points_for"]
        return {k:(mean(f(r.get(k)) for r in normalized) if normalized else 0.0) for k in keys}
