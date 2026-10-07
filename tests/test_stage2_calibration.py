from backend.engine.calibration import summarize, fit_affine_profile, apply_affine_profile

def test_stage2_summary_metrics():
    obs=[{"position":"WR","predicted_fantasy_points":10,"actual_fantasy_points":8,"history_depth":3,"confidence":.8,"game_total":48,"spread":3,"matchup_factor":1.02,"predicted_stats":{"targets":7,"receptions":5,"receiving_yards":70,"receiving_tds":.3},"actual_stats":{"targets":8,"receptions":5,"receiving_yards":65,"receiving_tds":0},"distribution":{"p05":2,"p10":4,"p25":7,"p50":10,"p75":13,"p90":17,"p95":20},"layer_impacts":{"opportunity":.1}}]
    out=summarize(obs)
    assert out["sample_size"]==1
    assert out["fantasy_points"]["mae"]==2
    assert "WR" in out["counting_stats"]
    assert out["interval_coverage"]["sample_size"]==1

def test_affine_profile_is_walk_forward_safe():
    obs=[{"position":"QB","predicted_fantasy_points":float(i),"actual_fantasy_points":float(i+2),"week":2,"distribution":{"p10":i-2,"p50":i,"p90":i+2}} for i in range(1,12)]
    profile=fit_affine_profile(obs,2)
    out=apply_affine_profile(obs,profile)
    assert profile["by_position"]["QB"]["status"]=="fitted"
    assert out[0]["uncalibrated_fantasy_points"]==1
    assert out[0]["predicted_fantasy_points"]>1
