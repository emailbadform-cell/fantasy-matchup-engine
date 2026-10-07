from backend.engine.predictor import PredictionEngine

class S: pass
class N: pass

def test_canonical_attempts_are_not_yards():
    e=PredictionEngine(S(),N(),"test")
    row={"attempts":"32","passing_yards":"269","passing_tds":"2","completions":"25"}
    c=e._canonical(row)
    assert c["attempts"]==32
    assert c["passing_yards"]==269
    assert c["attempts"] != c["passing_yards"]

def test_aliases():
    from backend.engine.features import normalize_team
    assert normalize_team("LAR")=="LA"
    assert normalize_team("LVR")=="LV"


def test_sleeper_scoring_settings_comes_from_league(monkeypatch):
    from backend.integrations.sleeper import SleeperClient
    client = SleeperClient()
    monkeypatch.setattr(client, "get_league", lambda league_id: {"league_id": league_id, "scoring_settings": {"rec": 0.5}})
    assert client.get_scoring_settings("x") == {"rec": 0.5}


def test_sleeper_scoring_settings_missing_is_empty(monkeypatch):
    from backend.integrations.sleeper import SleeperClient
    client = SleeperClient()
    monkeypatch.setattr(client, "get_league", lambda league_id: {"league_id": league_id})
    assert client.get_scoring_settings("x") == {}
