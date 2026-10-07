from backend.engines.projection_engine import ProjectionEngine
def test_projection_nonzero():
    e=ProjectionEngine()
    p={"name":"Test","position":"WR"}
    b={"targets":8,"receptions":5,"receiving_yards":70,"receiving_tds":.5,"rush_attempts":0,"rush_yards":0,"rush_tds":0}
    out=e.project(p,b,{"pass_efficiency":1,"pass_volume":1,"team_scoring_impact":1},{"pass_rate":.58,"rush_rate":.42,"explosive_rate":1,"red_zone_rate":1},{"outside":1,"coverage":1,"te":1,"run_defense":1,"red_zone":1,"explosive_allowed":1},1.0,{"total_line":50,"spread_line":-3})
    assert out["median"]["targets"]>0
    assert out["fantasy_points"]["median"]>0
