from backend.engine.optimizer import optimize_lineup


def p(pid, pos, pts, elig=None):
    return {"player_id":pid,"name":pid,"position":pos,"eligible_positions":elig or [pos],"projection":{"median_fantasy_points":pts}}


def test_optimizer_fills_every_fillable_slot_before_points():
    players=[p("qb","QB",1),p("rb","RB",20),p("wr","WR",19),p("te","TE",18)]
    out=optimize_lineup(players,["QB","RB","WR","TE"])
    assert out["filled_slots"] == 4
    assert out["open_slots"] == 0
    assert {x["player_id"] for x in out["assignment"]} == {"qb","rb","wr","te"}


def test_sleeper_flex_aliases_and_eligible_positions():
    players=[p("wr","WR",10,["WR"]),p("rb","RB",9,["RB"]),p("te","TE",8,["TE"])]
    out=optimize_lineup(players,["W/R/T","WR","RB"])
    assert out["filled_slots"] == 3
    assert out["open_slots"] == 0


def test_open_slot_only_when_no_eligible_player_exists():
    out=optimize_lineup([p("rb","RB",10)],["QB","RB"])
    assert out["filled_slots"] == 1
    assert out["open_slots"] == 1
