class QBEngine:
    """QB environment model. Metrics are based on leakage-safe historical game averages."""
    def evaluate(self, rolling, latest=None, availability=1.0):
        r3=(rolling or {}).get(3,{}) or {}; r6=(rolling or {}).get(6,{}) or {}; r12=(rolling or {}).get(12,{}) or {}
        def blend(k, default=0.0):
            vals=[r3.get(k,default),r6.get(k,default),r12.get(k,default)]
            return 0.45*vals[0]+0.35*vals[1]+0.20*vals[2]
        att=max(blend("attempts"),0.0); py=max(blend("passing_yards"),0.0); tds=max(blend("passing_tds"),0.0); ints=max(blend("interceptions"),0.0)
        ypa=py/att if att else 0.0; td_rate=tds/att if att else 0.0; int_rate=ints/att if att else 0.0
        ypa_factor=max(.72,min(1.28,1+(ypa-7.0)*.055)) if ypa else .92
        td_factor=max(.75,min(1.25,1+(td_rate-.04)*3.0)) if att else .95
        int_factor=max(.75,min(1.25,1-(int_rate-.025)*3.0)) if att else .98
        eff=max(.65,min(1.35,ypa_factor*.55+td_factor*.25+int_factor*.20))
        volume=max(.70,min(1.30,att/34.0)) if att else .88
        scoring=max(.70,min(1.30,eff*.72+volume*.18+.10))
        rush_att=blend("carries")
        rush_yards=blend("rushing_yards")
        rush_eff=(rush_yards/rush_att) if rush_att else 0.0
        return {
            "pass_volume":volume,"pass_efficiency":eff,"turnover_risk":max(.70,min(1.30,1+(int_rate-.025)*3.0)) if att else 1.0,
            "team_scoring_impact":scoring,"rushing_value":max(.70,min(1.30,1+(rush_eff-4.5)*.035)) if rush_eff else 1.0,
            "availability":availability,"attempts":att,"passing_yards":py,"passing_tds":tds,"interceptions":ints,
            "yards_per_attempt":ypa,"td_rate":td_rate,"int_rate":int_rate,"rush_attempts":rush_att,"rush_yards":rush_yards
        }

    def dependency_multiplier(self,pos,qb):
        q=qb or {}; se=q.get("pass_efficiency",1); sv=q.get("pass_volume",1); ss=q.get("team_scoring_impact",1); tr=q.get("turnover_risk",1)
        if pos in {"WR","TE"}:
            return max(.68,min(1.34,.42*se+.28*sv+.20*ss+.10*(2-tr)))
        if pos=="RB":
            # Poor QB can reduce receiving but may create additional rushing/game-script opportunity.
            return max(.78,min(1.24,.55+.20*ss+.10*sv+.10*(2-tr)+.05))
        if pos=="K": return max(.70,min(1.30,.60+.40*ss))
        return 1.0
