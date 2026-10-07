from backend.engine.predictor import PredictionEngine

class Dummy: pass

def test_defense_gets_display_name():
    e=PredictionEngine.__new__(PredictionEngine)
    p=e._resolve_player({"PHI": {"position":"DEF","team":"PHI"}}, "PHI")
    assert p["full_name"] == "PHI D/ST"
    assert p["name"] == "PHI D/ST"

def test_defense_team_id_without_player_record_gets_name():
    e=PredictionEngine.__new__(PredictionEngine)
    p=e._resolve_player({}, "PHI")
    assert p["position"] == "DEF"
    assert p["full_name"] == "PHI D/ST"
