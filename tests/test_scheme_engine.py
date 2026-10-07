from backend.engines.scheme_engine import SchemeEngine

def test_offense_accepts_feature_store_window_dict():
    x=SchemeEngine().offense({6:{"plays":64,"pass_rate":.61,"rush_rate":.39,"red_zone_rate":1.1,"explosive_rate":1.05}},"DET",2026,4)
    assert x["plays"]==64
    assert x["pass_rate"]==.61

def test_offense_ignores_string_items():
    x=SchemeEngine().offense({6:{"plays":60}},"DET",2026,4)
    assert x["plays"]==60
