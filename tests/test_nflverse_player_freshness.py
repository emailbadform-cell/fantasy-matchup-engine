from backend.integrations.nflverse import NFLVerseClient


def test_missing_individual_player_week_does_not_force_refresh(monkeypatch):
    c = NFLVerseClient()
    rows = [
        {"player_id": "goff", "week": "1"},
        {"player_id": "goff", "week": "2"},
        {"player_id": "goff", "week": "3"},
        {"player_id": "other", "week": "4"},
    ]
    c._stats_cache[2026] = rows
    calls = []

    def fake_player_stats(season, force_refresh=False):
        calls.append(force_refresh)
        return c._stats_cache[season]

    monkeypatch.setattr(c, "player_stats", fake_player_stats)
    for player_id in ("goff", "another", "goff"):
        c.player_history(2026, player_id=player_id, through_week=5)
    assert True not in calls


def test_dataset_missing_required_week_refreshes_once_for_many_players(monkeypatch):
    c = NFLVerseClient()
    stale = [{"player_id": "goff", "week": "3"}]
    c._stats_cache[2026] = stale
    calls = []

    def fake_player_stats(season, force_refresh=False):
        calls.append(force_refresh)
        return c._stats_cache[season]

    monkeypatch.setattr(c, "player_stats", fake_player_stats)
    for player_id in ("goff", "other", "third"):
        c.player_history(2026, player_id=player_id, through_week=5)
    assert calls.count(True) == 1
