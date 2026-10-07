from backend.integrations.nflverse import NFLVerseClient


def test_deebo_full_display_name_matches_when_short_name_is_abbreviated(monkeypatch):
    c = NFLVerseClient()
    rows = [
        {"player_id":"00-0035719","player_name":"D.Samuel","player_display_name":"Deebo Samuel Sr.",
         "season":"2026","week":"4","team":"SF","opponent_team":"DEN","receptions":"5",
         "targets":"6","receiving_yards":"26","receiving_tds":"1","carries":"3","rushing_yards":"44"}
    ]
    monkeypatch.setattr(c, "_ensure_player_history_fresh", lambda season, through_week: None)
    monkeypatch.setattr(c, "player_stats", lambda season, force_refresh=False: rows)
    got = c.player_history(2026, player_name="Deebo Samuel", through_week=5)
    assert len(got) == 1
    assert got[0]["player_id"] == "00-0035719"
    assert got[0]["week"] == "4"
    assert got[0]["targets"] == "6"
    assert got[0]["receptions"] == "5"
    assert got[0]["receiving_yards"] == "26"
    assert got[0]["receiving_tds"] == "1"
    assert got[0]["carries"] == "3"
    assert got[0]["rushing_yards"] == "44"


def test_nonmatching_player_still_rejected(monkeypatch):
    c = NFLVerseClient()
    rows = [{"player_id":"00-x","player_name":"A.Other","player_display_name":"Another Player","week":"4","team":"SF"}]
    monkeypatch.setattr(c, "_ensure_player_history_fresh", lambda season, through_week: None)
    monkeypatch.setattr(c, "player_stats", lambda season, force_refresh=False: rows)
    assert c.player_history(2026, player_name="Deebo Samuel", through_week=5) == []
