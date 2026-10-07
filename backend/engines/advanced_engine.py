import math
class AdvancedEngine:
    """Derives scheme/pressure/coverage proxies from PBP when available.
    Missing charting fields remain neutral instead of fabricating assignments.
    """
    def team_pbp_profile(self,pbp,team,week=None):
        if pbp is None or len(pbp)==0:return {}
        df=pbp.copy()
        if "posteam" not in df.columns:return {}
        x=df[df["posteam"].astype(str).str.upper()==str(team).upper()]
        if week is not None and "week" in x.columns:
            x=x[x["week"].astype(float)<float(week)]
        if len(x)==0:return {}
        def ratio(mask):
            return float(mask.mean()) if len(mask) else 0
        out={}
        if "pass" in x.columns: out["pass_rate"]=ratio(x["pass"].fillna(0).astype(float)>0)
        if "rush" in x.columns: out["rush_rate"]=ratio(x["rush"].fillna(0).astype(float)>0)
        if "shotgun" in x.columns: out["shotgun_rate"]=ratio(x["shotgun"].fillna(0).astype(float)>0)
        if "no_huddle" in x.columns: out["no_huddle_rate"]=ratio(x["no_huddle"].fillna(0).astype(float)>0)
        if "qb_hit" in x.columns: out["pressure_proxy"]=ratio(x["qb_hit"].fillna(0).astype(float)>0)
        if "sack" in x.columns: out["sack_rate"]=ratio(x["sack"].fillna(0).astype(float)>0)
        if "air_yards" in x.columns:
            vals=x["air_yards"].dropna()
            out["avg_air_yards"]=float(vals.mean()) if len(vals) else 0
        return out
    def coverage_profile(self,pbp,defteam,week=None):
        if pbp is None or len(pbp)==0:return {}
        df=pbp.copy()
        if "defteam" not in df.columns:return {}
        x=df[df["defteam"].astype(str).str.upper()==str(defteam).upper()]
        if week is not None and "week" in x.columns:x=x[x["week"].astype(float)<float(week)]
        out={}
        if "number_of_pass_rushers" in x.columns:
            v=x["number_of_pass_rushers"].dropna(); out["pass_rushers_avg"]=float(v.mean()) if len(v) else 0
        if "defenders_in_box" in x.columns:
            v=x["defenders_in_box"].dropna(); out["box_count_avg"]=float(v.mean()) if len(v) else 0
        return out
