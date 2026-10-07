from backend.integrations.nflverse import NFLVerseClient

def test_aliases():
    assert NFLVerseClient.normalize_team("LAR")=="LA"
    assert NFLVerseClient.normalize_team("LVR")=="LV"
