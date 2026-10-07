from backend.data.feature_store import FeatureStore
from backend.engines.baselines import base_projection
from backend.engines.projection_engine import ProjectionEngine
from backend.engines.qb_engine import QBEngine
from backend.engines.scheme_engine import SchemeEngine
from backend.engines.matchup_engine import MatchupEngine

class ModelService:
    def __init__(self):
        self.features=FeatureStore(); self.engine=ProjectionEngine(); self.qb=QBEngine(); self.scheme=SchemeEngine(); self.matchup=MatchupEngine()
    def set_scoring(self,scoring):
        self.engine.scoring=scoring or {}
    def project(self,player,player_rows,team_rows,season,week,game,opponent_team,qb_override=None):
        pid=player.get("gsis_id") or player.get("player_id")
        rolling=self.features.rolling_player(player_rows,pid,season,week)
        latest=self.features.latest_player(player_rows,pid,season,week)
        r6=rolling.get(6,{})
        qb=qb_override or self.qb.evaluate(rolling,latest)
        team=self.features.team_games(team_rows,player.get("team") or "",season,week)
        offense=self.scheme.offense(team.get(6,{}),player.get("team") or "",season,week)
        defense=self.scheme.defense(team_rows,opponent_team or "",season,week)
        usage=self._usage(player.get("position"),r6,latest)
        base=base_projection(player.get("position"),r6)
        if player.get("position")=="DEF":
            td=self.features.rolling_team(team_rows,player.get("team") or "",season,week,6)
            base={"sacks":td.get("sacks",0),"interceptions":td.get("interceptions",0),"fumble_recoveries":td.get("fumble_recoveries",td.get("fumbles_lost",0)),"def_tds":td.get("def_tds",0)}
        match=self.matchup.evaluate(player.get("position"),offense,defense)
        projection=self.engine.project(player,base,qb,offense,defense,usage,game,matchup=match)
        projection["matchup_detail"]=match
        return projection,{"rolling":rolling,"latest":latest,"qb":qb,"offense":offense,"defense":defense,"usage":usage,"matchup":match}
    def _usage(self,pos,r,latest):
        if pos in {"WR","TE"}: return max(.65,min(1.40,r.get("targets",0)/8 if r.get("targets",0) else .85))
        if pos=="RB": return max(.65,min(1.40,r.get("carries",0)/15 if r.get("carries",0) else .85))
        if pos=="QB": return max(.70,min(1.35,r.get("attempts",0)/34 if r.get("attempts",0) else .90))
        if pos=="K": return max(.70,min(1.30,r.get("field_goals",0)/2 if r.get("field_goals",0) else .85))
        return 1.0
