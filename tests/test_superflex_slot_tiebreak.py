from backend.engine.optimizer import optimize_lineup


def p(pos, points):
    return {"player_id": pos, "position": pos, "projection": {"median_fantasy_points": points}}


def test_mandatory_rb_preferred_to_superflex_on_tie():
    result = optimize_lineup([p("RB", 10)], ["QB", "RB", "SUPER_FLEX"])
    assert result["open_slot_names"] == ["QB", "SUPER_FLEX"]
    assert result["median_points"] == 10


def test_superflex_accepts_all_four_positions():
    for position in ("QB", "RB", "WR", "TE"):
        result = optimize_lineup([p(position, 10)], ["SUPER_FLEX"])
        assert result["filled_slots"] == 1


def test_higher_scoring_lineup_still_wins():
    result = optimize_lineup([p("RB", 10), p("QB", 20)], ["RB", "SUPER_FLEX"])
    assert result["median_points"] == 30
    assert {a["slot"]: a["position"] for a in result["assignment"]} == {"RB": "RB", "SUPER_FLEX": "QB"}
