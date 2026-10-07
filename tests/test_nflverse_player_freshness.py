from backend.integrations.nflverse import NFLVerseClient


def test_player_specific_missing_prior_week_forces_refresh(monkeypatch):
    c = NFLVerseClient()
    stale = [
        {"player_id":"goff","week":"1"},
        {"player_id":"goff","week":"2"},
        {"player_id":"goff","week":"3"},
        {"player_id":"other","week":"4"},
    ]
    fresh = stale + [{"player_id":"goff","week":"4"}]
    c._stats_cache[2026] = stale
    calls = []

    def fake_player_stats(season, force_refresh=False):
        calls.append(force_refresh)
        if force_refresh:
            c._stats_cache[season] = fresh
        return c._stats_cache[season]

    monkeypatch.setattr(c, "player_stats", fake_player_stats)
    rows = c.player_history(2026, player_id="goff", through_week=5)
    assert max(int(r["week"]) for r in rows) == 4
    assert True in calls
