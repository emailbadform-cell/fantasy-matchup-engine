from backend.engines.qb_engine import QBEngine
def test_bad_qb_reduces_receivers():
    q=QBEngine()
    bad=q.dependency_multiplier("WR",{"pass_efficiency":.75,"pass_volume":.8,"team_scoring_impact":.75})
    good=q.dependency_multiplier("WR",{"pass_efficiency":1.15,"pass_volume":1.1,"team_scoring_impact":1.1})
    assert bad < good
