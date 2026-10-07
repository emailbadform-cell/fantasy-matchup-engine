import math
from collections import defaultdict
from statistics import fmean, median

STAT_MAP = {
    "QB": ["pass_attempts","completions","passing_yards","passing_tds","interceptions","rushing_yards","rushing_tds"],
    "RB": ["carries","rushing_yards","targets","receptions","receiving_yards","rushing_tds","receiving_tds"],
    "WR": ["targets","receptions","receiving_yards","receiving_tds"],
    "TE": ["targets","receptions","receiving_yards","receiving_tds"],
    "K": ["field_goal_attempts","field_goals","extra_point_attempts","extra_points"],
    "DEF": ["sacks","interceptions","fumble_recoveries","def_tds"],
}


def _metric(rows):
    errors=[float(x["predicted"])-float(x["actual"]) for x in rows]
    if not errors: return {"sample_size":0,"mae":None,"rmse":None,"bias":None,"median_error":None}
    return {"sample_size":len(errors),"mae":fmean(abs(e) for e in errors),"rmse":math.sqrt(fmean(e*e for e in errors)),"bias":fmean(errors),"median_error":median(errors)}


def evaluate(predictions):
    pairs=[x for x in predictions if x.get("actual") is not None]
    if not pairs: return {"available":False,"sample_size":0}
    return {"available":True,**_metric(pairs)}


def _actual_fp(engine, row, pos, settings=None):
    # Convert one NFLverse weekly player/team row into the same canonical stat names
    # used by the live scorer. This is evaluation-only and never enters the pregame history.
    from .features import f, scoring
    s={}
    if pos=="QB": s={"pass_attempts":f(row,"attempts"),"completions":f(row,"completions"),"passing_yards":f(row,"passing_yards"),"passing_tds":f(row,"passing_tds"),"interceptions":f(row,"passing_interceptions","interceptions"),"rushing_yards":f(row,"rushing_yards"),"rushing_tds":f(row,"rushing_tds")}
    elif pos=="RB": s={"carries":f(row,"carries"),"rushing_yards":f(row,"rushing_yards"),"targets":f(row,"targets"),"receptions":f(row,"receptions"),"receiving_yards":f(row,"receiving_yards"),"rushing_tds":f(row,"rushing_tds"),"receiving_tds":f(row,"receiving_tds")}
    elif pos in {"WR","TE"}: s={"targets":f(row,"targets"),"receptions":f(row,"receptions"),"receiving_yards":f(row,"receiving_yards"),"receiving_tds":f(row,"receiving_tds")}
    elif pos=="K": s={"field_goal_attempts":f(row,"fg_att","field_goal_attempts"),"field_goals":f(row,"fg_made","field_goals"),"extra_point_attempts":f(row,"pat_att","extra_point_attempts"),"extra_points":f(row,"pat_made","extra_points")}
    return s, scoring(settings or {}, s, pos)


def _bucket(value, cuts, labels):
    for cut,label in zip(cuts,labels):
        if value < cut: return label
    return labels[-1]


def _segments(obs, keyfn):
    groups=defaultdict(list)
    for x in obs: groups[keyfn(x)].append(x)
    return {str(k):_metric([{"predicted":x["predicted_fantasy_points"],"actual":x["actual_fantasy_points"]} for x in v]) for k,v in groups.items()}


def _td_calibration(obs):
    rows=[]
    for x in obs:
        expected=sum(float(x.get("predicted_stats",{}).get(k,0) or 0) for k in ("passing_tds","rushing_tds","receiving_tds","def_tds"))
        actual=sum(float(x.get("actual_stats",{}).get(k,0) or 0) for k in ("passing_tds","rushing_tds","receiving_tds","def_tds"))
        p=1-math.exp(-max(expected,0))
        rows.append((p,1 if actual>0 else 0))
    if not rows: return {"sample_size":0}
    brier=fmean((p-a)**2 for p,a in rows)
    bins=[]
    edges=[0,.1,.2,.4,.6,.8,1.0001]
    for lo,hi in zip(edges[:-1],edges[1:]):
        q=[(p,a) for p,a in rows if lo<=p<hi]
        if q: bins.append({"range":f"{lo:.1f}-{min(hi,1):.1f}","n":len(q),"predicted_rate":fmean(p for p,a in q),"actual_rate":fmean(a for p,a in q)})
    return {"sample_size":len(rows),"brier_score":brier,"bins":bins}


def _interval(obs):
    q=[x for x in obs if x.get("actual_fantasy_points") is not None and x.get("distribution")]
    if not q:return {"sample_size":0}
    def cov(lo,hi): return fmean(float(x["distribution"][lo])<=float(x["actual_fantasy_points"])<=float(x["distribution"][hi]) for x in q)
    return {"sample_size":len(q),"p10_p90_coverage":cov("p10","p90"),"p25_p75_coverage":cov("p25","p75"),"p05_p95_coverage":cov("p05","p95"),"nominal":{"p10_p90":.80,"p25_p75":.50,"p05_p95":.90}}


def _confidence(obs):
    groups=defaultdict(list)
    for x in obs:
        c=float(x.get("confidence",0)); groups[_bucket(c,[.65,.75,.85,.95],["<.65",".65-.74",".75-.84",".85-.94",".95+"])].append(x)
    out={}
    for k,v in groups.items():
        m=_metric([{"predicted":x["predicted_fantasy_points"],"actual":x["actual_fantasy_points"]} for x in v])
        out[k]={**m,"mean_confidence":fmean(float(x.get("confidence",0)) for x in v)}
    return out


def summarize(observations):
    fp=[{"predicted":x["predicted_fantasy_points"],"actual":x["actual_fantasy_points"]} for x in observations]
    by_pos={p:_metric([{"predicted":x["predicted_fantasy_points"],"actual":x["actual_fantasy_points"]} for x in observations if x["position"]==p]) for p in ["QB","RB","WR","TE","K","DEF"]}
    stat_metrics={}
    for pos in by_pos:
        stat_metrics[pos]={}
        for stat in STAT_MAP[pos]:
            rows=[{"predicted":x.get("predicted_stats",{}).get(stat,0),"actual":x.get("actual_stats",{}).get(stat,0)} for x in observations if x["position"]==pos]
            stat_metrics[pos][stat]=_metric(rows)
    seg={
        "position":_segments(observations,lambda x:x["position"]),
        "history_depth":_segments(observations,lambda x:_bucket(x.get("history_depth",0),[2,4,7],["1","2-3","4-6","7+"])),
        "game_total":_segments(observations,lambda x:_bucket(x.get("game_total",44),[40,48,56],["<40","40-47","48-55","56+"])),
        "spread":_segments(observations,lambda x:_bucket(abs(x.get("spread",0)),[3,7,14],["0-2.9","3-6.9","7-13.9","14+"])),
        "confidence":_confidence(observations),
        "matchup":_segments(observations,lambda x:_bucket(x.get("matchup_factor",1),[.97,1.03],["<.97",".97-1.02","1.03+"]))
    }
    layer={}
    for x in observations:
        err=float(x["predicted_fantasy_points"])-float(x["actual_fantasy_points"])
        for name,impact in x.get("layer_impacts",{}).items():
            layer.setdefault(name,[]).append((float(impact or 0),err))
    layer_out={}
    for name,pairs in layer.items():
        active=[z for z in pairs if z[0]!=0]
        if len(active)>=3:
            mx=fmean(a for a,e in active); my=fmean(e for a,e in active)
            cov=fmean((a-mx)*(e-my) for a,e in active); va=fmean((a-mx)**2 for a,e in active)
            corr=cov/math.sqrt(va*fmean((e-my)**2 for a,e in active)) if va>0 and fmean((e-my)**2 for a,e in active)>0 else 0
        else: corr=0
        layer_out[name]={"active_samples":len(active),"mean_impact":fmean(a for a,e in active) if active else 0,"error_impact_correlation":corr}
    return {"sample_size":len(observations),"fantasy_points":_metric(fp),"by_position":by_pos,"counting_stats":stat_metrics,"segments":seg,"td_calibration":_td_calibration(observations),"interval_coverage":_interval(observations),"confidence_calibration":_confidence(observations),"layer_error_attribution":layer_out}


def walk_forward(client, season, start_week=2, end_week=None, settings=None, max_players=None):
    """Generate strictly pregame walk-forward observations from bundled NFLverse data.
    Current bundles may contain only a subset of seasons; only seasons explicitly supplied are used.
    """
    from .predictor import PredictionEngine
    stats=client.player_stats(season)
    weeks=sorted({int(r.get("week",0)) for r in stats if str(r.get("season_type","REG"))=="REG" and int(r.get("week",0) or 0)>=start_week})
    if end_week is not None: weeks=[w for w in weeks if w<=end_week]
    engine=PredictionEngine(_NullSleeper(),client,"calibration-walk-forward")
    observations=[]
    # Build target-week player identities/positions only; no target-week performance is passed to history.
    for week in weeks:
        target=[r for r in stats if int(r.get("week",0) or 0)==week and str(r.get("season_type","REG"))=="REG"]
        players={}
        for r in target:
            pid=str(r.get("player_id")); pos=str(r.get("position") or "").upper(); team=client.normalize_team(r.get("recent_team") or r.get("team"))
            if pid and pos in STAT_MAP: players[pid]={"player_id":pid,"full_name":r.get("player_display_name") or r.get("player_name"),"position":pos,"team":team}
        # Defense is one team-level fantasy entity per game.
        game_teams=[]
        for g in client.week_games(season,week):
            for team in (client.normalize_team(g.get("home_team")),client.normalize_team(g.get("away_team"))): game_teams.append((team,g))
        candidates=[p for p in players.values()]
        if max_players: candidates=candidates[:max_players]
        for p in candidates:
            game=client.team_game(season,week,p["team"])
            if not game: continue
            opp=client.normalize_team(game.get("away_team")) if client.normalize_team(game.get("home_team"))==p["team"] else client.normalize_team(game.get("home_team"))
            # Empty starter list avoids lineup-position assumptions in historical evaluation.
            pred=engine._project_player(p,players,game,opp,season,week,settings or {},[])
            actual_rows=[r for r in target if str(r.get("player_id"))==str(p["player_id"])]
            if not actual_rows: continue
            ar=actual_rows[0]; astats,afp=_actual_fp(engine,ar,p["position"],settings)
            impacts={z["layer"]:z.get("impact",0) for z in pred.get("layer_audit",[]) if z.get("active")}
            observations.append({"player_id":p["player_id"],"player_name":p["full_name"],"position":p["position"],"team":p["team"],"opponent":opp,"season":season,"week":week,"history_depth":pred.get("historical_games",0),"confidence":pred.get("confidence",0),"game_total":float(game.get("total_line") or 44),"spread":float(game.get("spread_line") or 0),"matchup_factor":float(pred.get("factors",{}).get("position_matchup",{}).get("value",{}).get("factor",1)),"predicted_stats":pred["projection"],"actual_stats":astats,"predicted_fantasy_points":pred["projection"]["median_fantasy_points"],"actual_fantasy_points":afp,"distribution":pred.get("distribution",{}),"layer_impacts":impacts})
        # Team-defense observations: one defense entity per team/game.
        for team,g in game_teams:
            opp=client.normalize_team(g.get("away_team")) if client.normalize_team(g.get("home_team"))==team else client.normalize_team(g.get("home_team"))
            p={"player_id":team,"full_name":team,"position":"DEF","team":team}
            pred=engine._project_player(p,players,g,opp,season,week,settings or {},[])
            drows=[r for r in target if client.normalize_team(r.get("recent_team") or r.get("team"))==team]
            astats={"sacks":sum(float(r.get("def_sacks") or 0) for r in drows),"interceptions":sum(float(r.get("def_interceptions") or 0) for r in drows),"fumble_recoveries":sum(float(r.get("def_fumbles") or 0) for r in drows),"def_tds":sum(float(r.get("def_tds") or 0) for r in drows)}
            from .features import scoring
            afp=scoring(settings or {},astats,"DEF")
            impacts={z["layer"]:z.get("impact",0) for z in pred.get("layer_audit",[]) if z.get("active")}
            observations.append({"player_id":team,"player_name":team,"position":"DEF","team":team,"opponent":opp,"season":season,"week":week,"history_depth":len(client.defense_history(season,team,week)),"confidence":pred.get("confidence",0),"game_total":float(g.get("total_line") or 44),"spread":float(g.get("spread_line") or 0),"matchup_factor":1.0,"predicted_stats":pred["projection"],"actual_stats":astats,"predicted_fantasy_points":pred["projection"]["median_fantasy_points"],"actual_fantasy_points":afp,"distribution":pred.get("distribution",{}),"layer_impacts":impacts})
    return observations


class _NullSleeper:
    def get_players(self): return {}


def fit_affine_profile(observations, train_end_week):
    profile={"method":"walk_forward_affine","trained_through_week":train_end_week,"by_position":{},"global":{}}
    def fit(rows):
        xs=[float(x["predicted_fantasy_points"]) for x in rows]; ys=[float(x["actual_fantasy_points"]) for x in rows]
        if len(xs)<8: return {"a":0.0,"b":1.0,"sample_size":len(xs),"status":"insufficient_sample"}
        mx=fmean(xs); my=fmean(ys); den=sum((x-mx)**2 for x in xs)
        b=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/den if den else 1.0
        b=max(.70,min(1.30,b)); a=my-b*mx
        return {"a":a,"b":b,"sample_size":len(xs),"status":"fitted"}
    train=[x for x in observations if int(x["week"])<=int(train_end_week)]
    profile["global"]=fit(train)
    for pos in ["QB","RB","WR","TE","K","DEF"]: profile["by_position"][pos]=fit([x for x in train if x["position"]==pos])
    return profile

def apply_affine_profile(observations, profile):
    out=[]
    for x in observations:
        y=dict(x); p=profile.get("by_position",{}).get(x["position"],profile.get("global",{"a":0,"b":1}))
        a=float(p.get("a",0)); b=float(p.get("b",1)); raw=float(x["predicted_fantasy_points"]); cal=a+b*raw
        y["uncalibrated_fantasy_points"]=raw; y["predicted_fantasy_points"]=cal
        if y.get("distribution"):
            d=dict(y["distribution"]);
            for k in ("p05","p10","p25","p50","p75","p90","p95","mean"):
                if k in d: d[k]=max(0,a+b*float(d[k]))
            y["distribution"]=d
        out.append(y)
    return out
