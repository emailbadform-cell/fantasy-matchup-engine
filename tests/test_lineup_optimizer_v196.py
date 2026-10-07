from backend.engine.optimizer import optimize_lineup

def p(pid,name,pos,pts):
    return {"player_id":pid,"name":name,"position":pos,"team":"X","projection":{"median_fantasy_points":pts}}

def test_optimizer_uses_bench_player_when_better():
    players=[p("q1","Starter QB","QB",10),p("q2","Bench QB","QB",20),p("r1","RB1","RB",15),p("w1","WR1","WR",14),p("t1","TE1","TE",9)]
    out=optimize_lineup(players,["QB","RB","WR","TE"])
    assert out["filled_slots"]==4
    assert out["median_points"]==58
    assert any(x["player_id"]=="q2" and x["slot"]=="QB" for x in out["assignment"])

def test_optimizer_flex_is_legal_and_exact():
    players=[p("r1","RB1","RB",10),p("r2","RB2","RB",30),p("w1","WR1","WR",20)]
    out=optimize_lineup(players,["RB","FLEX"])
    assert out["median_points"]==50
    assert {x["player_id"] for x in out["assignment"]}=={"r2","w1"}

def test_optimizer_can_leave_unfillable_slot_open():
    out=optimize_lineup([p("w1","WR1","WR",12)],["QB","WR"])
    assert out["filled_slots"]==1 and out["open_slots"]==1 and out["median_points"]==12
