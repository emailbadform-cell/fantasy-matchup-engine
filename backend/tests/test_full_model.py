from backend.engine.features import scoring, simulation, confidence_score
from backend.engine.optimizer import optimize_lineup
from backend.engine.audit import audit_predictions
from backend.engine.calibration import evaluate


def test_scoring_defaults_are_ppr():
    assert scoring({}, {"receptions": 5, "receiving_yards": 50}, "WR") == 10.0


def test_simulation_has_distribution():
    x = simulation(15, 3, n=500)
    assert x["p05"] <= x["p50"] <= x["p95"]
    assert 0 <= x["prob_10"] <= 1


def test_confidence_is_bounded():
    assert 0.05 <= confidence_score(3, True, ["available", "derived"], "WR") <= 0.99


def test_optimizer_assigns_legal_slots():
    players = [
        {"player_id": "1", "position": "QB", "projection": {"median_fantasy_points": 20}},
        {"player_id": "2", "position": "WR", "projection": {"median_fantasy_points": 15}},
        {"player_id": "3", "position": "RB", "projection": {"median_fantasy_points": 14}},
    ]
    x = optimize_lineup(players, ["QB", "FLEX"])
    assert len(x["assignment"]) == 2


def test_audit_flags_missing_history_as_warning_not_crash():
    x = audit_predictions({"team": {"starters": [{"player_id": "1", "projection": {"median_fantasy_points": 10}, "historical_games": 0, "identity": {"resolved_id": None}}]}})
    assert x["issues"] == []
    assert x["warnings"]


def test_calibration_metrics():
    x = evaluate([{"predicted": 10, "actual": 8}, {"predicted": 12, "actual": 15}])
    assert x["available"]
    assert x["sample_size"] == 2
    assert x["mae"] == 2.5

def test_matchup_layers_are_not_universally_neutral():
    from backend.engine.features import position_matchup, offensive_scheme, defensive_scheme
    weak = [{"passing_yards_allowed": 310, "rushing_yards_allowed": 155, "def_sacks": 1}]
    strong = [{"passing_yards_allowed": 180, "rushing_yards_allowed": 85, "def_sacks": 4}]
    assert position_matchup("WR", weak)["factor"] > position_matchup("WR", strong)["factor"]
    assert defensive_scheme(strong)["pressure_factor"] > defensive_scheme(weak)["pressure_factor"]


def test_pregame_cutoff_excludes_target_week():
    assert __import__('backend.engine.features', fromlist=['cutoff']).cutoff(2026, 4)["historical_weeks_lt"] == 3
