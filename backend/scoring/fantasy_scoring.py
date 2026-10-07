def from_sleeper(settings):
    s=dict(DEFAULT_SCORING)
    m={"pass_yd":"pass_yards","pass_td":"pass_td","pass_int":"interception","rush_yd":"rush_yards","rush_td":"rush_td","rec":"reception","rec_yd":"receiving_yards","rec_td":"receiving_td","fgm":"field_goal","xpm":"extra_point"}
    for a,b in m.items():
        if a in settings:
            try:s[b]=float(settings[a])
            except:pass
    return s

DEFAULT_SCORING={
 "pass_yards":0.04,"pass_td":4,"interception":-2,"rush_yards":0.1,"rush_td":6,
 "reception":1,"receiving_yards":0.1,"receiving_td":6,"two_point":2,
 "field_goal":3,"extra_point":1,"sack":1,"def_interception":2,"fumble_recovery":2,"def_td":6
}
def fantasy_points(pos,stats,scoring=None):
    s=dict(DEFAULT_SCORING); s.update(scoring or {})
    p=0
    if pos=="QB":
        p+=stats.get("pass_yards",0)*s["pass_yards"]+stats.get("pass_tds",0)*s["pass_td"]+stats.get("interceptions",0)*s["interception"]
        p+=stats.get("rush_yards",0)*s["rush_yards"]+stats.get("rush_tds",0)*s["rush_td"]
    elif pos=="RB":
        p+=stats.get("rush_yards",0)*s["rush_yards"]+stats.get("rush_tds",0)*s["rush_td"]
        p+=stats.get("receptions",0)*s["reception"]+stats.get("receiving_yards",0)*s["receiving_yards"]+stats.get("receiving_tds",0)*s["receiving_td"]
    elif pos in {"WR","TE"}:
        p+=stats.get("receptions",0)*s["reception"]+stats.get("receiving_yards",0)*s["receiving_yards"]+stats.get("receiving_tds",0)*s["receiving_td"]
        p+=stats.get("rush_yards",0)*s["rush_yards"]+stats.get("rush_tds",0)*s["rush_td"]
    elif pos=="K": p+=stats.get("field_goals",0)*s["field_goal"]+stats.get("extra_points",0)*s["extra_point"]
    elif pos=="DEF": p+=stats.get("sacks",0)*s["sack"]+stats.get("interceptions",0)*s["def_interception"]+stats.get("fumble_recoveries",0)*s["fumble_recovery"]+stats.get("def_tds",0)*s["def_td"]
    return round(p,2)
