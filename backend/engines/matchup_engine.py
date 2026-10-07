class MatchupEngine:
    """Position-aware matchup adjustments. Neutral when assignment data is unavailable."""
    def evaluate(self,position,offense,defense,advanced=None):
        d=defense or {}; a=advanced or {}
        if position=="QB":
            return {"pressure":d.get("pressure",1),"coverage":d.get("coverage",1)}
        if position=="RB":
            return {"run_defense":d.get("run_defense",1),"receiving":d.get("rb_receiving",1)}
        if position=="WR":
            return {"outside":d.get("outside",1),"slot":d.get("slot",1),"coverage":d.get("coverage",1)}
        if position=="TE":
            return {"te":d.get("te",1),"coverage":d.get("coverage",1)}
        if position=="K":
            return {"red_zone":d.get("red_zone",1)}
        if position=="DEF":
            return {"pass_defense":d.get("pass_defense",1),"pressure":d.get("pressure",1)}
        return {}
