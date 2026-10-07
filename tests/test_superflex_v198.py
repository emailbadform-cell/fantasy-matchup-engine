from backend.engine.optimizer import optimize_lineup, normalize_slot


def p(pid, pos, pts, elig=None):
    return {"player_id":pid,"name":pid,"position":pos,"eligible_positions":elig or [pos],"projection":{"median_fantasy_points":pts}}


def test_all_superflex_aliases_normalize():
    for alias in ["SUPER_FLEX", "SUPERFLEX", "OP", "QB/RB/WR/TE", "Q/W/R/T"]:
        assert normalize_slot(alias) == "SUPER_FLEX"


def test_super_flex_underscore_fills_with_qb():
    out=optimize_lineup([p("qb1","QB",20),p("qb2","QB",15)], ["QB","SUPER_FLEX"])
    assert out["filled_slots"] == 2
    assert out["open_slots"] == 0
    assert [x["slot"] for x in out["assignment"]] == ["QB","SUPER_FLEX"]


def test_superflex_can_fill_rb_wr_te():
    for pos in ["RB","WR","TE"]:
        out=optimize_lineup([p("x",pos,5)], ["SUPER_FLEX"])
        assert out["filled_slots"] == 1
        assert out["open_slots"] == 0


def test_fill_count_beats_negative_points():
    out=optimize_lineup([p("qb","QB",10),p("rb","RB",-2)], ["QB","RB"])
    assert out["filled_slots"] == 2
    assert out["open_slots"] == 0


def test_open_slot_is_named_when_truly_unfillable():
    out=optimize_lineup([p("rb","RB",10)], ["QB","RB","SUPER_FLEX"])
    assert out["filled_slots"] == 1
    assert out["open_slots"] == 2
    assert out["open_slot_names"] == ["QB","RB"]
    assert len(out["open_slot_names"]) == out["open_slots"]
