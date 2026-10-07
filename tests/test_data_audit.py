from backend.engine.features import red_zone, position_matchup, defensive_scheme, coverage_assignment


def test_red_zone_is_explicit_proxy_when_unavailable():
    x = red_zone([{"attempts": 30, "carries": 30, "passing_tds": 3, "rushing_tds": 0}])
    assert x["status"] == "proxy"
    assert x["td_rate_proxy"] > 0


def test_position_matchup_uses_actual_allowed_context():
    x = position_matchup("RB", [{"rushing_yards_allowed": 160, "passing_yards_allowed": 200, "def_sacks": 2}])
    assert x["status"] == "data_backed"
    assert x["factor"] > 1


def test_defensive_scheme_is_not_default_when_data_exists():
    x = defensive_scheme([{"rushing_yards_allowed": 100, "passing_yards_allowed": 180, "def_sacks": 4}])
    assert x["status"] == "data_backed"
    assert x["pressure_factor"] > 1


def test_coverage_is_transparent_when_assignment_data_is_missing():
    x = coverage_assignment({"position": "WR"}, [{"passing_yards_allowed": 220}])
    assert x["status"] == "unavailable"
    assert x["coverage_factor"] == 1.0
