def base_projection(pos, r):
    r=r or {}
    if pos=="QB":
        return {"pass_attempts":r.get("attempts",0),"pass_yards":r.get("passing_yards",0),"pass_tds":r.get("passing_tds",0),"interceptions":r.get("interceptions",0),"rush_attempts":r.get("carries",0),"rush_yards":r.get("rushing_yards",0),"rush_tds":r.get("rushing_tds",0)}
    if pos=="RB":
        return {"carries":r.get("carries",0),"rush_yards":r.get("rushing_yards",0),"targets":r.get("targets",0),"receptions":r.get("receptions",0),"receiving_yards":r.get("receiving_yards",0),"rush_tds":r.get("rushing_tds",0),"receiving_tds":r.get("receiving_tds",0)}
    if pos in {"WR","TE"}:
        return {"targets":r.get("targets",0),"receptions":r.get("receptions",0),"receiving_yards":r.get("receiving_yards",0),"receiving_tds":r.get("receiving_tds",0),"rush_attempts":r.get("carries",0),"rush_yards":r.get("rushing_yards",0),"rush_tds":r.get("rushing_tds",0)}
    if pos=="K": return {"field_goals":r.get("field_goals",0),"extra_points":r.get("extra_points",0)}
    if pos=="DEF": return {"sacks":r.get("sacks",0),"interceptions":r.get("interceptions",0),"fumble_recoveries":r.get("fumbles_lost",0),"def_tds":r.get("def_tds",0)}
    return {}
