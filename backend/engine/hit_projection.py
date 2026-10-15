"""Independent chronology-safe Hit fantasy projection. No future-week data is used."""
from backend.scoring.league_rules import score

STATS = {"QB": ("passing_yards", "passing_tds"), "WR": ("receiving_yards", "receiving_tds"), "TE": ("receiving_yards", "receiving_tds")}


def num(row, key):
    try: return float(row.get(key) or 0)
    except (TypeError, ValueError): return 0.0


def hit_projection(position, player_rows, defense_rows, team_rows, player_stats, opponent, week, base_stats, scoring):
    """Player vs opponent position-allowed 50/50 baseline; season/recent hit rates.

    For WR/TE defense allowances, use per-game per-player production (not the
    entire WR/TE corps), so the comparison has matching units. Missing evidence
    produces a null Hit, not a fabricated median duplicate.
    """
    if position not in STATS:
        return {"points": None, "status": "unsupported_position", "stats": {}}
    rows = sorted([r for r in player_rows if int(r.get("week") or 0) < int(week)], key=lambda r:int(r.get("week") or 0))
    if not rows: return {"points": None, "status": "no_player_history", "stats": {}}
    opp_games = {(str(r.get("game_id")), int(r.get("week") or 0)) for r in team_rows if str(r.get("opponent_team") or "").upper() == str(opponent).upper() and int(r.get("week") or 0) < int(week)}
    allowed = {k: [] for k in STATS[position]}
    # Prefer directly recorded defensive allowances when present. Otherwise
    # derive QB yards from the actual quarterbacks that faced this defense.
    if position == "QB":
        direct=[num(r,"passing_yards_allowed") for r in defense_rows if r.get("passing_yards_allowed") is not None]
        if direct: allowed["passing_yards"] = direct
    if opp_games:
        for r in player_stats:
            if str(r.get("position") or "").upper() != position: continue
            if (str(r.get("game_id")),int(r.get("week") or 0)) not in opp_games: continue
            for key in STATS[position]:
                if not (position == "QB" and key == "passing_yards" and allowed[key]):
                    allowed[key].append(num(r,key))
    details, projected = {}, {}
    for key in STATS[position]:
        values = [num(r,key) for r in rows]
        opponents = allowed[key]
        if not opponents: return {"points":None,"status":"missing_position_defense_allowance","stats":details}
        player_avg = sum(values)/len(values)
        defense_avg = sum(opponents)/len(opponents)
        raw_blend = (player_avg + defense_avg)/2
        # Historical line-hit consistency is a modest, explicitly experimental
        # adjustment; do not mistake this heuristic for a calibrated probability.
        line_for_rate = raw_blend - .5 if key.endswith("tds") else raw_blend
        season_rate = sum(v > line_for_rate for v in values)/len(values)
        recent_rate = sum(v > line_for_rate for v in values[-5:])/len(values[-5:])
        defense_rate = sum(v > line_for_rate for v in opponents)/len(opponents)
        hit_index = .4*season_rate + .3*recent_rate + .3*defense_rate
        estimate = max(0, raw_blend * (1 + .20*(hit_index-.5)))
        # TD expectations are count-based; no threshold conversion to probability.
        line = estimate - .5 if key.endswith("tds") else estimate
        details[key] = {"player_average":round(player_avg,3),"defense_allowed_average":round(defense_avg,3),"blended_projection":round(estimate,3),"player_games":len(values),"defense_samples":len(opponents),"line":round(line,3),"player_hit_rate":round(100*sum(v>line for v in values)/len(values),2),"recent_5_hit_rate":round(100*sum(v>line for v in values[-5:])/len(values[-5:]),2),"defense_over_line_rate":round(100*sum(v>line for v in opponents)/len(opponents),2),"combined_hit_index":round(100*hit_index,2),"raw_blended_projection":round(raw_blend,3)}
        projected[key] = estimate
    # Score the adjusted stat line using the same league scoring rules as FME.
    points = score(scoring, {**base_stats, **projected}, position)
    return {"points":round(points,3),"status":"calculated","stats":details,"method":"equal_weight_player_average_vs_position_defense_allowed"}
