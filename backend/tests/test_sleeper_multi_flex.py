from backend.engine.optimizer import optimize_lineup, normalize_slot
from backend.engine.waivers import recommend_waiver_moves

def player(pid,pos,points):
    return {"player_id":pid,"name":pid,"position":pos,"projection":{"median_fantasy_points":points}}

def test_two_flex_plus_superflex_independent():
    slots=["QB","FLEX","FLEX","SUPER_FLEX"]
    roster=[player("q1","QB",25),player("q2","QB",22),player("q3","QB",40),player("r1","RB",19),player("w1","WR",18),player("t1","TE",16)]
    opt=optimize_lineup(roster,slots)
    assert opt["filled_slots"]==4
    assert opt["configured_slots"].count("FLEX")==2
    assert opt["configured_slots"].count("SUPER_FLEX")==1
    assert all(a["position"]!="QB" for a in opt["assignment"] if a["slot"]=="FLEX")
    assert sum(a["position"]=="QB" for a in opt["assignment"])==2

def test_superflex_can_be_non_qb():
    roster=[player("q","QB",20),player("r1","RB",18),player("w1","WR",17),player("t1","TE",16)]
    opt=optimize_lineup(roster,["QB","FLEX","FLEX","SUPER_FLEX"])
    assert opt["filled_slots"]==4
    assert next(a for a in opt["assignment"] if a["slot"]=="SUPER_FLEX")["position"] in {"RB","WR","TE"}

def test_waiver_preserves_flex_counts():
    roster=[player("q1","QB",20),player("q2","QB",18),player("r1","RB",16),player("w1","WR",15),player("t1","TE",14),player("bench","WR",2)]
    out=recommend_waiver_moves(roster,[player("r2","RB",22)],["QB","FLEX","FLEX","SUPER_FLEX"],max_moves=1)
    assert out["lineup_slot_audit"]["standard_flex"]==2
    assert out["lineup_slot_audit"]["superflex"]==1
    assert out["final_optimal_team_points"]>=69

def test_sleeper_aliases():
    assert normalize_slot("SUPER_FLEX")=="SUPER_FLEX"
    assert normalize_slot("FLEX")=="FLEX"
