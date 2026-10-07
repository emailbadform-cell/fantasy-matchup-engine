from unittest.mock import patch

from backend.integrations.espn import ESPNClient
from backend.engine.optimizer import optimize_lineup, normalize_slot


def _p(pid, pos, pts):
    return {"player_id": pid, "name": pid, "position": pos, "team": "X", "projection": {"median_fantasy_points": pts}}


def test_espn_slot_3_decodes_to_rb_wr():
    c = ESPNClient()
    payload = {"settings": {"rosterSettings": {"lineupSlotCounts": {"0":1,"2":2,"3":1,"4":2,"6":1,"16":1,"17":1,"20":7}}}}
    with patch.object(c, "_get", return_value=payload):
        out = c.lineup_settings("1")
    assert "SLOT_3" not in out["starter_slots"]
    assert "RB_WR" in out["starter_slots"]
    assert len(out["starter_slots"]) == 9


def test_espn_rb_wr_slot_is_fillable():
    slots=["QB","RB","RB","RB_WR","WR","WR","TE","DEF","K"]
    players=[_p("qb","QB",10),_p("rb1","RB",9),_p("rb2","RB",8),_p("rb3","RB",7),_p("wr1","WR",9),_p("wr2","WR",8),_p("te","TE",6),_p("def","DEF",5),_p("k","K",4)]
    out=optimize_lineup(players,slots)
    assert out["filled_slots"] == 9
    assert out["open_slots"] == 0
    assert any(x["slot"] == "WR_RB" for x in out["assignment"])


def test_other_espn_combo_slots_decode():
    c=ESPNClient()
    payload={"settings":{"rosterSettings":{"lineupSlotCounts":{"5":1,"7":1,"23":1,"20":5}}}}
    with patch.object(c,"_get",return_value=payload):
        out=c.lineup_settings("1")
    assert out["starter_slots"] == ["WR_TE","SUPER_FLEX","FLEX"]
