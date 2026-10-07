from functools import lru_cache


def normalize_slot(slot):
    """Normalize ESPN/Sleeper/common fantasy lineup slot aliases."""
    raw = str(slot or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "SUPERFLEX": "SUPER_FLEX",
        "SUPER_FLEX": "SUPER_FLEX",
        "SUPER_FLEX_SLOT": "SUPER_FLEX",
        "OP": "SUPER_FLEX",
        "QB/RB/WR/TE": "SUPER_FLEX",
        "Q/W/R/T": "SUPER_FLEX",
        "Q_R_W_T": "SUPER_FLEX",
        "FLEX": "FLEX",
        "RB/WR/TE": "FLEX",
        "W/R/T": "FLEX",
        "W_R_T": "FLEX",
        "WR/RB": "WR_RB",
        "RB/WR": "WR_RB",
        "RB_WR": "WR_RB",
        "W/R": "WR_RB",
        "W_R": "WR_RB",
        "WR/TE": "WR_TE",
        "WR_TE": "WR_TE",
        "W/T": "WR_TE",
        "W_T": "WR_TE",
        "DST": "DEF",
        "D/ST": "DEF",
    }
    return aliases.get(raw, raw)


def optimize_lineup(players, slots):
    """Exact roster optimizer: maximize legal filled slots first, then median points."""
    players = [p for p in players if p.get("projection", {}).get("median_fantasy_points") is not None]
    slots = [normalize_slot(s) for s in (slots or [])]

    @lru_cache(maxsize=None)
    def solve(i, used_mask):
        if i >= len(slots):
            return (0, 0.0, ())
        # Open is a fallback only. Lexicographic comparison below always prefers
        # more filled slots over points, even when a player's median is negative.
        best = solve(i + 1, used_mask)
        slot = slots[i]
        for j, p in enumerate(players):
            if used_mask & (1 << j) or not _eligible(p, slot):
                continue
            filled, points, assignment = solve(i + 1, used_mask | (1 << j))
            points_here = float(p.get("projection", {}).get("median_fantasy_points", 0.0) or 0.0)
            candidate = (filled + 1, points + points_here, ((i, slot, j),) + assignment)
            if (candidate[0], candidate[1]) > (best[0], best[1]):
                best = candidate
        return best

    filled, total, raw = solve(0, 0)
    assignment = []
    filled_indices = set()
    for slot_index, slot, j in raw:
        filled_indices.add(slot_index)
        p = players[j]
        assignment.append({
            "slot": slot,
            "slot_index": slot_index,
            "player_id": p.get("player_id"),
            "name": p.get("name") or p.get("full_name"),
            "position": p.get("position"),
            "team": p.get("team"),
            "median_fantasy_points": p.get("projection", {}).get("median_fantasy_points", 0.0),
        })
    open_slot_names = [slot for i, slot in enumerate(slots) if i not in filled_indices]
    return {
        "median_points": round(total, 4),
        "assignment": assignment,
        "filled_slots": filled,
        "open_slots": len(open_slot_names),
        "open_slot_names": open_slot_names,
        "configured_slots": slots,
    }


def _eligible(player, slot):
    pos = str(player.get("position") or "").upper()
    elig = {str(x).upper() for x in (player.get("eligible_positions") or []) if x}
    if pos:
        elig.add(pos)
    if "DST" in elig:
        elig.add("DEF")
    if "DEF" in elig:
        elig.add("DST")
    slot = normalize_slot(slot)
    if slot == "FLEX":
        return bool(elig & {"RB", "WR", "TE"})
    if slot == "WR_RB":
        return bool(elig & {"WR", "RB"})
    if slot == "WR_TE":
        return bool(elig & {"WR", "TE"})
    if slot == "SUPER_FLEX":
        return bool(elig & {"QB", "RB", "WR", "TE"})
    if slot == "DEF":
        return bool(elig & {"DEF", "DST"})
    return slot in elig
