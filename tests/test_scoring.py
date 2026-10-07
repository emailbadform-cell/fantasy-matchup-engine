from backend.scoring.fantasy_scoring import from_sleeper,fantasy_points
def test_sleeper_scoring():
    s=from_sleeper({"pass_yd":0.04,"pass_td":4,"rec":1,"rec_yd":0.1,"rec_td":6})
    assert fantasy_points("WR",{"receptions":5,"receiving_yards":80,"receiving_tds":1},s)==19.0
