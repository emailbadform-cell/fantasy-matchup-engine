from .features import clamp
from .layers import PREDICTIVE_LAYERS, METADATA_LAYERS


def audit_predictions(predictions):
    players=predictions.get("team",{}).get("starters",[]) if isinstance(predictions,dict) else []
    issues=[]; warnings=[]; layer_failures=[]
    for p in players:
        pid=p.get("player_id"); proj=p.get("projection",{}); la=p.get("layer_audit",[])
        if not proj: issues.append({"player_id":pid,"type":"missing_projection"})
        if p.get("historical_games",0)==0: warnings.append({"player_id":pid,"type":"no_history","fallback_used":True})
        if p.get("position") != "DEF" and p.get("identity",{}).get("resolved_id") is None: warnings.append({"player_id":pid,"type":"identity_unresolved"})
        if proj.get("median_fantasy_points",0)<0: issues.append({"player_id":pid,"type":"negative_projection"})
        if proj.get("high",0)<proj.get("low",0): issues.append({"player_id":pid,"type":"invalid_distribution"})
        for x in la:
            if not x.get("present") or x.get("status")=="missing": layer_failures.append({"player_id":pid,"layer":x.get("layer"),"reason":"missing"})
            if x.get("active") and x.get("status") in {"unavailable","fallback"}: warnings.append({"player_id":pid,"type":"active_fallback","layer":x.get("layer")})
    players_n=max(len(players),1); quality=1-clamp((len(warnings)+len(layer_failures)*2)/max(players_n*5,1),0,1)
    return {"players":len(players),"issues":issues,"warnings":warnings,"layer_failures":layer_failures,"required_layers":len(PREDICTIVE_LAYERS),"predictive_layers":len(PREDICTIVE_LAYERS)-len(METADATA_LAYERS),"data_quality_score":round(quality,4),"audit_ready":not issues and not layer_failures and quality>=.85 and predictions.get("model_gate",{}).get("audit_ready",False)}
