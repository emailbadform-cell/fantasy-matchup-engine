from backend.data.feature_store import FeatureStore
def test_leakage():
    rows=[{"player_id":"1","season":2026,"week":1,"targets":5},{"player_id":"1","season":2026,"week":2,"targets":7},{"player_id":"1","season":2026,"week":4,"targets":20}]
    x=FeatureStore().rolling_player(rows,"1",2026,4,windows=(3,))
    assert x[3]["targets"]==6
