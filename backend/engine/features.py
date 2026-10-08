import math, random, statistics


def f(row, *keys):
    if not isinstance(row, dict): return 0.0
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            try: return float(v)
            except (ValueError, TypeError): pass
    return 0.0


def text(row, *keys, default=""):
    if not isinstance(row, dict): return default
    for k in keys:
        v = row.get(k)
        if v not in (None, ""): return str(v)
    return default


def mean(xs, default=0.0):
    xs = [x for x in xs if x is not None]
    return statistics.fmean(xs) if xs else default


def weighted_recent(values, default=0.0):
    values = [v for v in values if v is not None]
    if not values: return default
    weights = list(range(1, len(values) + 1))
    return sum(v*w for v,w in zip(values, weights))/sum(weights)


def clamp(x, lo, hi): return max(lo, min(hi, x))
def safe_div(a,b,default=0.0): return a/b if b else default


def normalize_team(team):
    aliases={"LAR":"LA","LVR":"LV","OAK":"LV","STL":"LA","SD":"LAC","SDG":"LAC","JAC":"JAX","WSH":"WAS"}
    return aliases.get(str(team or "").upper(), str(team or "").upper())


def availability(player):
    status=str(player.get("injury_status") or "").lower()
    if status in {"out","ir","injured_reserve","doubtful"}: return {"availability":0.0,"label":status}
    if status in {"questionable","q"}: return {"availability":0.75,"label":"questionable"}
    if status in {"limited"}: return {"availability":0.85,"label":"limited"}
    return {"availability":1.0,"label":"available"}


def replacement_factor(starters, player_id):
    try:
        idx=[str(x) for x in starters].index(str(player_id))
        return 1.0 if idx < 2 else 0.85
    except ValueError: return 0.8


def offensive_line_factor(team_rows):
    if not team_rows: return 1.0
    ypc=mean([safe_div(f(r,"rushing_yards","rush_yards"), max(f(r,"rushing_attempts","carries","rush_attempts"),1)) for r in team_rows],4.2)
    sacks=mean([f(r,"sacks_allowed","sacks") for r in team_rows],2.0)
    return clamp(1 + 0.025*(ypc-4.2) - 0.010*(sacks-2),0.90,1.10)


def defensive_front_factor(opp_rows):
    if not opp_rows: return 1.0
    allowed=mean([safe_div(f(r,"rushing_yards","rush_yards"), max(f(r,"rushing_attempts","carries","rush_attempts"),1)) for r in opp_rows],4.2)
    sacks=mean([f(r,"def_sacks","sacks") for r in opp_rows],2.0)
    # >1 benefits the offense; strong defense suppresses it.
    return clamp(1 - 0.022*(4.2-allowed) - 0.018*(sacks-2),0.88,1.12)


def trench_matchup(ol,dl): return clamp(ol/dl if dl else 1.0,0.86,1.16)


def game_script(game, team):
    total=f(game,"total_line") or 44.0
    spread=f(game,"spread_line","spread")
    home=normalize_team(game.get("home_team")); team=normalize_team(team)
    team_spread=spread if team==home else -spread
    team_points=clamp(total/2-team_spread*0.45,13,34)
    opp_points=clamp(total-team_points,10,34)
    lead=team_points-opp_points
    return {"team_points":team_points,"opp_points":opp_points,"lead":lead,
            "rush_factor":clamp(1+lead/24,.78,1.22),"pass_factor":clamp(1-lead/30,.78,1.25),
            "pace_factor":clamp(1+(total-44)/180,.90,1.08)}


def play_volume(team_rows, game, team):
    plays=[f(r,"offensive_plays","plays","off_plays") for r in team_rows]
    baseline=mean([p for p in plays if p>0],63)
    total=f(game,"total_line") or 44
    return clamp(baseline*(1+clamp((total-44)/100,-.08,.10)),52,76)


def _player_avg(history,*keys,default=0): return mean([f(r,*keys) for r in history],default)


def opportunity(history,team_rows,position,gs,player_share=None):
    share=player_share or {}
    team_pass=_player_avg(team_rows,"attempts","passing_attempts","pass_attempts",default=34)
    team_plays=_player_avg(team_rows,"offensive_plays","plays",default=63)
    if position=="QB":
        a=_player_avg(history,"attempts","passing_attempts","pass_attempts") or team_pass
        return {"pass_attempts":clamp(a*gs["pass_factor"],18,50)}
    if position=="RB":
        c=_player_avg(history,"carries","rushing_attempts","rush_attempts") or max(2,team_plays*share.get("rush_share",.18))
        t=_player_avg(history,"targets","receiving_targets") or max(1,team_pass*share.get("target_share",.06))
        return {"carries":max(0,c*gs["rush_factor"]),"targets":max(0,t*gs["pass_factor"])}
    t=_player_avg(history,"targets","receiving_targets") or max(2,team_pass*share.get("target_share",.10))
    return {"targets":max(0,t*gs["pass_factor"])}


def route_alignment(player,history):
    routes=_player_avg(history,"routes","route_runs","routes_run")
    snaps=_player_avg(history,"offense_snaps","offensive_snaps","snaps")
    slot=_player_avg(history,"slot_snaps","slot_routes")
    return {"route_share":clamp(safe_div(routes,snaps,.75),0,1),"slot_proxy":clamp(slot,0,1),"position":player.get("position")}


def coverage_assignment(player,opponent_rows):
    pos=str(player.get("position") or "").upper()
    outside=mean([f(r,"outside_allowed","outside") for r in opponent_rows],0)
    slot=mean([f(r,"slot_allowed","slot") for r in opponent_rows],0)
    te=mean([f(r,"te_allowed","te") for r in opponent_rows],0)
    # True player-level coverage assignments are not present in the bundled NFLverse stats.
    # Use position-specific team defense only when those fields exist; otherwise remain neutral.
    raw = {"WR":outside,"TE":te}.get(pos,0)
    if raw:
        factor=clamp(raw,0.90,1.10)
        status="position_defense_data"
    else:
        factor=1.0; status="unavailable"
    return {"coverage_factor":factor,"assignment":"position-level defense data" if raw else "unavailable","position":pos,"status":status}


def position_matchup(position,opponent_rows):
    pos=str(position or "").upper()
    if not opponent_rows:
        return {"factor":1.0,"position":pos,"basis":"unavailable","status":"unavailable"}
    pass_allowed=mean([f(r,"passing_yards_allowed") for r in opponent_rows],0)
    rush_allowed=mean([f(r,"rushing_yards_allowed") for r in opponent_rows],0)
    sacks=mean([f(r,"def_sacks") for r in opponent_rows],0)
    if pos in {"WR","TE","QB"} and pass_allowed>0:
        factor=clamp(1+(pass_allowed-230)/1000,.90,1.10)
    elif pos=="RB" and rush_allowed>0:
        factor=clamp(1+(rush_allowed-120)/700,.90,1.10)
    elif sacks>0:
        factor=clamp(1-(sacks-2)*.015,.94,1.06)
    else:
        return {"factor":1.0,"position":pos,"basis":"unavailable","status":"unavailable"}
    return {"factor":factor,"position":pos,"basis":"team-level opponent allowed production","status":"data_backed"}


def offensive_scheme(team_rows):
    pass_att=mean([f(r,"attempts","passing_attempts","pass_attempts") for r in team_rows],34)
    rush=mean([f(r,"rushing_attempts","carries","rush_attempts") for r in team_rows],26)
    plays=max(pass_att+rush,1)
    pr=clamp(pass_att/plays,.35,.75)
    return {"pass_rate":pr,"rush_rate":1-pr,"tempo_plays":mean([f(r,"offensive_plays","plays") for r in team_rows],63),"status":"data_backed"}


def defensive_scheme(opponent_rows):
    if not opponent_rows:
        return {"pressure_factor":1.0,"pass_yards_allowed":0,"rush_yards_allowed":0,"status":"unavailable"}
    sacks=mean([f(r,"def_sacks") for r in opponent_rows],0)
    pass_allowed=mean([f(r,"passing_yards_allowed") for r in opponent_rows],0)
    rush_allowed=mean([f(r,"rushing_yards_allowed") for r in opponent_rows],0)
    if sacks<=0 and pass_allowed<=0 and rush_allowed<=0:
        return {"pressure_factor":1.0,"pass_yards_allowed":0,"rush_yards_allowed":0,"status":"unavailable"}
    pressure=clamp(1+(sacks-2)*.06, .82,1.18)
    return {"pressure_factor":pressure,"pass_yards_allowed":pass_allowed,"rush_yards_allowed":rush_allowed,"status":"data_backed"}


def weather(game):
    wind=f(game,"wind"); temp=f(game,"temp"); desc=str(game.get("weather") or "").lower()
    rain=1.0 if any(x in desc for x in ("rain","storm","snow")) else 0.0
    passing=clamp(1-wind/180-rain*.05,.80,1.03); kicking=clamp(1-wind/140-rain*.03,.78,1.04)
    return {"wind":wind,"temperature":temp,"precipitation_proxy":rain,"pass_factor":passing,"kick_factor":kicking,"status":"schedule_data"}


def surface(game):
    roof=str(game.get("roof","")).lower(); surf=str(game.get("surface","")).lower()
    indoor=roof in {"dome","closed","retractable"}
    return {"indoor":indoor,"surface":surf or "unknown","pass_factor":1.02 if indoor else 1.0}


def referee(game, historical_penalty_rate=None, league_penalty_rate=None):
    name=game.get("referee")
    if historical_penalty_rate is None or league_penalty_rate in (None,0):
        return {"referee":name,"penalty_factor":1.0,"data_status":"unavailable" if not name else "name_only"}
    factor=clamp(historical_penalty_rate/max(league_penalty_rate,1e-6),.94,1.06)
    return {"referee":name,"penalty_rate":historical_penalty_rate,"league_penalty_rate":league_penalty_rate,"penalty_factor":factor,"data_status":"data_backed"}


def coaching(game,team, historical_pass_rate=None, league_pass_rate=None):
    coach=game.get("home_coach") if normalize_team(game.get("home_team"))==normalize_team(team) else game.get("away_coach")
    if historical_pass_rate is None or league_pass_rate in (None,0):
        return {"coach":coach,"aggression":1.0,"data_status":"name_only" if coach else "unavailable"}
    aggression=clamp(historical_pass_rate/max(league_pass_rate,1e-6),.94,1.06)
    return {"coach":coach,"pass_rate":historical_pass_rate,"league_pass_rate":league_pass_rate,"aggression":aggression,"data_status":"data_backed"}


def red_zone(team_rows):
    rz=[f(r,"red_zone_targets","redzone_targets","red_zone_touches") for r in team_rows]
    if any(v>0 for v in rz):
        tds=mean([f(r,"touchdowns","passing_tds","rushing_tds","receiving_tds") for r in team_rows],0)
        td_rate=clamp(tds/max(mean(rz,0),1),.02,.35)
        return {"rz_opportunity":mean(rz,0),"td_rate_proxy":td_rate,"status":"data_backed"}
    # Bundled NFLverse weekly team stats do not expose red-zone opportunity.
    # Use overall TD/play as a clearly-labelled scoring-environment proxy.
    plays=max(mean([f(r,"attempts")+f(r,"carries") for r in team_rows],63),1)
    tds=mean([f(r,"passing_tds")+f(r,"rushing_tds") for r in team_rows],0)
    td_rate=clamp(tds/plays,.01,.12)
    return {"rz_opportunity":0.0,"td_rate_proxy":td_rate,"status":"proxy","proxy_basis":"team_touchdown_rate_per_offensive_play"}


def explosive(history):
    rec=mean([f(r,"receiving_20","receptions_20_plus","receiving_20_plus") for r in history],0)
    rush=mean([f(r,"rushing_20","rushing_20_plus") for r in history],0)
    return {"explosive_rate":clamp((rec+rush)/max(len(history),1),0,.5),"big_plays":rec+rush}


def qb_correlation(qb_efficiency,position):
    rho={"WR":.35,"TE":.30,"RB":.15}.get(position,0)
    return {"rho":rho,"qb_effect":clamp(1+(qb_efficiency-1)*rho,.88,1.12)}


def defensive_fantasy(opponent_qb, opponent_rows):
    qb_att=max(f(opponent_qb,"attempts","passing_attempts","pass_attempts"),1)
    qb_int=clamp(f(opponent_qb,"interceptions","passing_interceptions","ints")/qb_att,.005,.08)
    sacks=mean([f(r,"def_sacks","sacks") for r in opponent_rows],2)
    return {"sacks":clamp(sacks,.5,6),"interception_rate":qb_int,"fumble_recovery_rate":.45,"def_td_rate":.08}


def simulation(base,sd,n=4000,seed=13):
    rng=random.Random(seed); vals=[max(0,rng.gauss(base,max(sd,.25))) for _ in range(n)]; vals.sort()
    def pct(p): return vals[min(len(vals)-1,int(p*(len(vals)-1)))]
    return {"n":n,"p05":pct(.05),"p10":pct(.10),"p25":pct(.25),"p50":pct(.50),"p75":pct(.75),"p90":pct(.90),"p95":pct(.95),
            "prob_10":sum(v>=10 for v in vals)/n,"prob_15":sum(v>=15 for v in vals)/n,"prob_20":sum(v>=20 for v in vals)/n,
            "mean":statistics.fmean(vals),"stdev":statistics.pstdev(vals)}


def simulate(base,sd,n=3000,seed=13): return simulation(base,sd,n=n,seed=seed)


def scoring(settings,stat,pos=None):
    from backend.scoring.league_rules import score
    return score(settings, stat, pos)


def start_sit(players): return sorted(players,key=lambda x:x.get("projection",{}).get("median_fantasy_points",0),reverse=True)
def calibration(predicted,actual):
    if actual is None:return {"available":False}
    e=predicted-actual; return {"available":True,"error":e,"absolute_error":abs(e),"squared_error":e*e}

def cutoff(season,week): return {"season":season,"week":week,"historical_weeks_lt":max(0,week-1),"pregame_only":True}
def provenance(features): return [{"feature":k,"source":v.get("source","derived"),"status":v.get("status","available")} for k,v in features.items()]
def versioning(version): return {"model_version":version,"feature_schema":"1.5","prediction_schema":"1.5","calibration_schema":"1.1"}

def confidence_score(historical_games,has_qb,feature_statuses,position):
    hist=clamp(historical_games/6,0,1); qb=1 if has_qb or position in {"QB","K","DEF"} else .5
    coverage=safe_div(sum(1 for s in feature_statuses if s in {"available","derived","data_backed","schedule_data","schedule-level"}),max(len(feature_statuses),1),.5)
    bonus=.05 if position in {"QB","RB","WR","TE"} else 0
    return clamp(.25*hist+.25*qb+.45*coverage+bonus,.05,.99)
