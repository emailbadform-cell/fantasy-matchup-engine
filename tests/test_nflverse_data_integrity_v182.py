from pathlib import Path
from backend.integrations.nflverse import NFLVerseClient


def test_force_refresh_bypasses_alternate_cache(monkeypatch, tmp_path):
    # Contract test for the v1.8.1 regression: force_refresh must reach the network path.
    c = NFLVerseClient()
    calls=[]
    class R:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def read(self): return b"player_id,week\nx,4\n"
    def fake_open(req, timeout=60):
        calls.append(True); return R()
    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    import backend.integrations.nflverse as mod
    monkeypatch.setattr(mod, "CACHE", tmp_path)
    data=c._download("https://example.invalid/test.csv","x.csv",force_refresh=True)
    assert calls and b"x,4" in data


def test_player_refresh_key_is_player_and_week_specific():
    c=NFLVerseClient()
    assert c._player_refresh_key(2026,"goff",required_week=4) != c._player_refresh_key(2026,"other",required_week=4)
    assert c._player_refresh_key(2026,"goff",required_week=4) != c._player_refresh_key(2026,"goff",required_week=5)


def test_history_status_treats_bye_as_complete(monkeypatch):
    c=NFLVerseClient()
    monkeypatch.setattr(c,"team_game",lambda season,week,team: None)
    x=c.player_history_status(2026,"DET",[{"week":"3"}],5)
    assert x["complete"] is True and x["status"]=="complete_bye"


def test_history_status_marks_expected_missing_week_pending(monkeypatch):
    c=NFLVerseClient()
    monkeypatch.setattr(c,"team_game",lambda season,week,team: {"week":str(week),"home_team":team})
    x=c.player_history_status(2026,"DET",[{"week":"1"},{"week":"2"},{"week":"3"}],5)
    assert x["complete"] is False and x["status"]=="data_pending" and x["required_week"]==4
