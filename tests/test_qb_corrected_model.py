from backend.engine.predictor import PredictionEngine

class Dummy: pass

def engine():
    return PredictionEngine(Dummy(), Dummy(), "1.8.0-qb-corrected")

def test_qb_volume_recency_and_script_damping():
    e = engine()
    history = [
        {"week":1,"attempts":24}, {"week":2,"attempts":30},
        {"week":3,"attempts":36}, {"week":4,"attempts":40},
    ]
    team = [{"week":i+1,"position":"QB","attempts":a} for i,a in enumerate([26,31,35,39])]
    neutral = e._qb_corrected_volume(history, team, {"pass_factor":1.0})
    suppressed = e._qb_corrected_volume(history, team, {"pass_factor":.78})
    assert 30 <= neutral <= 42
    assert suppressed >= neutral * .88  # only half of directional suppression is allowed

def test_qb_efficiency_stack_is_bounded():
    e = engine()
    assert e._qb_efficiency_stack(1.10,1.05,1.06,1.10,1.20) == 1.15
    assert e._qb_efficiency_stack(.90,.95,.94,.90,.80) == .85
