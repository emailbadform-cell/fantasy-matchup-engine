from math import log, exp
from backend.engines.qb_engine import QBEngine
from backend.engines.scheme_engine import SchemeEngine
from backend.scoring.fantasy_scoring import fantasy_points

class ProjectionEngine:
    def __init__(self,scoring=None): self.qb=QBEngine(); self.scheme=SchemeEngine(); self.scoring=scoring

    def factors(self,pos,qb,offense,defense,usage,game,matchup=None,advanced=None):
        game=game or {}; offense=offense or {}; defense=defense or {}; matchup=matchup or {}
        total=float(game.get("total_line") or 43); env=max(.78,min(1.24,total/43.0))
        spread=float(game.get("spread_line") or 0)
        # Positive home/away spread affects script differently; keep it modest until backtested.
        script=1.0+max(-.08,min(.08,abs(spread)/28.0))
        if pos in {"QB","WR","TE"}: script=1.0+max(-.06,min(.06,(total-43)/120.0))
        def clamp(x,lo=.70,hi=1.30): return max(lo,min(hi,float(x)))
        qb_factor=self.qb.dependency_multiplier(pos,qb)
        pass_rate=offense.get("pass_rate",.58); rush_rate=offense.get("rush_rate",.42)
        if pos in {"QB","WR","TE"}: off_factor=clamp(pass_rate/.58)
        elif pos=="RB": off_factor=clamp(rush_rate/.42)
        elif pos=="K": off_factor=clamp(offense.get("red_zone_rate",1))
        else: off_factor=1.0
        matchup_factor=clamp(self.scheme.position_matchup(pos,defense))
        explosive=clamp(float(offense.get("explosive_rate",1))*float(defense.get("explosive_allowed",1)),.78,1.28)
        td=clamp(float(offense.get("red_zone_rate",1))*float(defense.get("red_zone",1))*env,.72,1.30)
        return {
          "qb_environment":clamp(qb_factor,.68,1.34),"offensive_scheme":off_factor,"defensive_scheme":matchup_factor,
          "usage":clamp(usage,.60,1.45),"position_matchup":matchup_factor,"game_environment":env,"game_script":script,
          "explosive_play":explosive,"td_environment":td
        }

    def multiplier(self,f):
        weights={"qb_environment":.18,"offensive_scheme":.09,"defensive_scheme":.08,"usage":.22,"position_matchup":.10,"game_environment":.10,"game_script":.05,"explosive_play":.08,"td_environment":.10}
        return max(.55,min(1.55,exp(sum(weights[k]*log(max(.01,f[k])) for k in weights))))

    def _position_projection(self,pos,base,f,usage,qb,offense,defense,game):
        # Opportunity and efficiency are separated so a bad QB doesn't blindly reduce rushing volume.
        qb_dep=self.qb.dependency_multiplier(pos,qb)
        env=f["game_environment"]; scheme=f["offensive_scheme"]; match=f["position_matchup"]
        if pos=="QB":
            vol=base.get("pass_attempts",0)*f["usage"]*scheme*env
            ypa=max(.1,qb.get("yards_per_attempt",7.0))*match*f["explosive_play"]
            pass_yards=vol*ypa
            td=base.get("pass_tds",0)*f["td_environment"]*qb.get("team_scoring_impact",1)
            ints=base.get("interceptions",0)*qb.get("turnover_risk",1)
            rush_att=base.get("rush_attempts",0)*f["usage"]
            rush_yards=base.get("rush_yards",0)*f["usage"]
            return {"pass_attempts":vol,"pass_yards":pass_yards,"pass_tds":td,"interceptions":ints,"rush_attempts":rush_att,"rush_yards":rush_yards,"rush_tds":base.get("rush_tds",0)*f["td_environment"]}
        if pos=="RB":
            carries=base.get("carries",0)*f["usage"]*scheme*f["game_script"]
            ypc=max(.1,base.get("rush_yards",0)/base.get("carries",1) if base.get("carries",0) else 4.0)*match*f["explosive_play"]
            targets=base.get("targets",0)*f["usage"]*qb_dep
            catch=max(.1,base.get("receptions",0)/base.get("targets",1) if base.get("targets",0) else .70)*qb_dep
            rec=targets*catch
            ypt=max(.1,base.get("receiving_yards",0)/base.get("targets",1) if base.get("targets",0) else 7.0)*match
            return {"carries":carries,"rush_yards":carries*ypc,"targets":targets,"receptions":rec,"receiving_yards":targets*ypt,"rush_tds":base.get("rush_tds",0)*f["td_environment"],"receiving_tds":base.get("receiving_tds",0)*f["td_environment"]*qb_dep}
        if pos in {"WR","TE"}:
            targets=base.get("targets",0)*f["usage"]*qb_dep*scheme
            catch=max(.1,base.get("receptions",0)/base.get("targets",1) if base.get("targets",0) else .62)*qb_dep
            rec=targets*catch
            ypt=max(.1,base.get("receiving_yards",0)/base.get("targets",1) if base.get("targets",0) else 9.0)*match*f["explosive_play"]
            return {"targets":targets,"receptions":rec,"receiving_yards":targets*ypt,"receiving_tds":base.get("receiving_tds",0)*f["td_environment"]*qb_dep,"rush_attempts":base.get("rush_attempts",0)*f["usage"],"rush_yards":base.get("rush_yards",0)*f["usage"]*f["explosive_play"],"rush_tds":base.get("rush_tds",0)*f["td_environment"]}
        if pos=="K":
            fg=base.get("field_goals",0)*f["usage"]*f["td_environment"]*env
            xp=base.get("extra_points",0)*f["usage"]*f["td_environment"]*qb.get("team_scoring_impact",1)
            return {"field_goals":fg,"extra_points":xp}
        if pos=="DEF":
            pressure=defense.get("pressure",1); opp_qb=1/qb.get("pass_efficiency",1) if qb else 1
            return {"sacks":base.get("sacks",0)*f["usage"]*pressure*opp_qb,"interceptions":base.get("interceptions",0)*f["usage"]*opp_qb,"fumble_recoveries":base.get("fumble_recoveries",0)*f["usage"],"def_tds":base.get("def_tds",0)*f["td_environment"]}
        return {k:v for k,v in base.items()}

    def project(self,player,base,qb,offense,defense,usage,game,matchup=None,advanced=None):
        pos=player["position"]; f=self.factors(pos,qb,offense,defense,usage,game,matchup,advanced)
        med=self._position_projection(pos,base,f,usage,qb,offense,defense,game)
        low={k:max(0,v*.82) for k,v in med.items()}; high={k:max(0,v*1.18) for k,v in med.items()}
        med={k:round(max(0,v),2) for k,v in med.items()}; low={k:round(v,2) for k,v in low.items()}; high={k:round(v,2) for k,v in high.items()}
        fp={"low":fantasy_points(pos,low,self.scoring),"median":fantasy_points(pos,med,self.scoring),"high":fantasy_points(pos,high,self.scoring)}
        confidence=max(.25,min(.95,.72 + min(0.15,usage*.05) - abs(self.multiplier(f)-1)*.20))
        return {"status":"model_complete","player":player["name"],"position":pos,"low":low,"median":med,"high":high,"fantasy_points":fp,
                "factor_multiplier":round(self.multiplier(f),4),"factors":{k:round(v,4) for k,v in f.items()},"confidence":round(confidence,3),
                "audit":{"base_source":"leakage_safe_rolling_history","factor_count":len(f),"qb_upstream":pos in {"WR","TE","RB","K"},"opportunity_efficiency_split":True}}
