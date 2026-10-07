from backend.engine.qb_monte_carlo import simulate_qb_stats

def test_qb_stat_mc_shape_and_thresholds():
    projected={"pass_attempts":35,"completions":23,"passing_yards":250,"passing_tds":1.6,"interceptions":.8,"rushing_yards":20,"rushing_tds":.15}
    history=[{"attempts":30,"passing_yards":210,"rushing_yards":12},{"attempts":38,"passing_yards":290,"rushing_yards":28}]
    out=simulate_qb_stats(projected,history,{},n=5000,seed=7)
    assert out["n"] == 5000
    assert 200 < out["passing_yards"]["p50"] < 300
    assert 0 <= out["thresholds"]["pass_250"] <= 1
    assert out["fantasy_points"]["p90"] > out["fantasy_points"]["p10"]
