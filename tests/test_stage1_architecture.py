from backend.engine.predictor import scheme_offense_factor, scheme_defense_factor
from backend.engine.features import red_zone


def test_stage1_separates_offensive_and_defensive_scheme_roles():
    off_low = scheme_offense_factor("WR", {"pass_rate": .45})
    off_high = scheme_offense_factor("WR", {"pass_rate": .70})
    def_soft = scheme_defense_factor("WR", {"pressure_factor": .90})
    def_hard = scheme_defense_factor("WR", {"pressure_factor": 1.10})
    assert off_low != off_high
    assert def_soft != def_hard
    assert off_low == scheme_offense_factor("WR", {"pass_rate": .45})
    assert off_low != def_hard


def test_stage1_red_zone_is_td_rate_only_proxy():
    x = red_zone([{"attempts": 30, "carries": 30, "passing_tds": 3, "rushing_tds": 0}])
    assert x["status"] == "proxy"
    assert "proxy_basis" in x
    assert x["td_rate_proxy"] > 0
