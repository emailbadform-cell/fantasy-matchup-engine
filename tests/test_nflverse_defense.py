from backend.integrations.nflverse import NFLVerseClient

def test_defense_history_filters_to_target_defense():
    client = NFLVerseClient()
    rows = client.defense_history(2026, "BAL", 4)
    assert len(rows) == 3
    assert all(r["opponent_team"] == "BAL" for r in rows)
    assert all(r["week"] < 4 for r in rows)
    assert any(r["def_sacks"] > 0 for r in rows)
