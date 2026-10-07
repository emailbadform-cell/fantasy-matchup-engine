from statistics import mean

ALIASES = {"LAR":"LA","LA":"LA","LVR":"LV","LV":"LV","JAC":"JAX","JAX":"JAX","WSH":"WAS","WAS":"WAS","OAK":"LV","SD":"LAC","STL":"LA"}

def norm_team(team):
    t=str(team or "").strip().upper()
    return ALIASES.get(t,t)

def _avg(rows, key, default):
    vals=[]
    for r in rows or []:
        if not isinstance(r,dict):
            continue
        try:
            vals.append(float(r.get(key, default)))
        except (TypeError,ValueError):
            continue
    return mean(vals) if vals else default

class SchemeEngine:
    """Builds offense/defense environment features from historical team rows or aggregates."""
    def offense(self, team_data, team, season=None, week=None):
        # FeatureStore.team_games returns {3:{...},6:{...},12:{...}}.  Accept that
        # directly; also accept raw rows for compatibility with older callers.
        if isinstance(team_data, dict) and any(k in team_data for k in (3,6,12)):
            a = team_data.get(6) or team_data.get(3) or team_data.get(12) or {}
            if not isinstance(a,dict): a={}
            return {
                "plays": _safe(a.get("plays"),62),
                "pass_rate": _safe(a.get("pass_rate"),.58),
                "rush_rate": _safe(a.get("rush_rate"),.42),
                "pace": _safe(a.get("plays"),62)/60,
                "target_concentration": _safe(a.get("target_concentration"),1),
                "red_zone_rate": _safe(a.get("red_zone_rate"),1),
                "explosive_rate": _safe(a.get("explosive_rate"),1),
            }
        rows=[]
        target=norm_team(team)
        for r in team_data or []:
            if not isinstance(r,dict): continue
            rt=norm_team(r.get("team") or r.get("posteam"))
            if rt!=target: continue
            if week is not None and r.get("week"):
                try:
                    if float(r.get("week"))>=float(week): continue
                except (TypeError,ValueError): pass
            rows.append(r)
        rows=sorted(rows,key=lambda x:_safe(x.get("week"),0))[-6:]
        return {
            "plays":_avg(rows,"plays",62),"pass_rate":_avg(rows,"pass_rate",.58),"rush_rate":_avg(rows,"rush_rate",.42),
            "pace":_avg(rows,"plays",62)/60,"target_concentration":_avg(rows,"target_concentration",1),
            "red_zone_rate":_avg(rows,"red_zone_rate",1),"explosive_rate":_avg(rows,"explosive_rate",1)
        }

    def defense(self, team_rows, team, season=None, week=None):
        rows=[]; target=norm_team(team)
        for r in team_rows or []:
            if not isinstance(r,dict): continue
            rt=norm_team(r.get("team") or r.get("defteam"))
            if rt!=target: continue
            if week is not None and r.get("week"):
                try:
                    if float(r.get("week"))>=float(week): continue
                except (TypeError,ValueError): pass
            rows.append(r)
        rows=sorted(rows,key=lambda x:_safe(x.get("week"),0))[-6:]
        return {"run_defense":_avg(rows,"run_defense",1),"pass_defense":_avg(rows,"pass_defense",1),
                "pressure":_avg(rows,"pressure_rate",1),"coverage":_avg(rows,"coverage",1),
                "slot":_avg(rows,"slot",1),"outside":_avg(rows,"outside",1),"te":_avg(rows,"te",1),
                "rb_receiving":_avg(rows,"rb_receiving",1),"red_zone":_avg(rows,"red_zone",1),
                "explosive_allowed":_avg(rows,"explosive_allowed",1)}

    def position_matchup(self,pos,defense):
        defense = defense if isinstance(defense,dict) else {}
        key={"QB":"pass_defense","WR":"outside","TE":"te","RB":"run_defense","K":"red_zone","DEF":"pass_defense"}.get(pos,"pass_defense")
        try:return float(defense.get(key,1))
        except (TypeError,ValueError):return 1.0

def _safe(value, default):
    try:return float(value)
    except (TypeError,ValueError):return default
