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


def _projection_high(projection):
    """Use the production predictor's `high` (P90), with legacy alias support."""
    value = projection.get("high_fantasy_points")
    if value is None:
        value = projection.get("high")
    return value


def optimize_lineup(players, slots):
    """Exact roster optimizer: maximize legal filled slots first, then median points."""
    players = [p for p in players if p.get("projection", {}).get("median_fantasy_points") is not None]
    slots = [normalize_slot(s) for s in (slots or [])]

    # Exact maximum-weight bipartite assignment, polynomial in roster size.
    # An occupied slot is always preferable to an empty one, regardless of points.
    # Each slot has its own dummy player so vacancies remain legal.
    n=len(slots); m=len(players); cols=m+n
    bonus=1.0 + sum(abs(float((x.get("projection") or {}).get("median_fantasy_points") or 0)) for x in players)
    # Stable tie-break: when points and filled-slot counts are equal, prefer
    # mandatory positional slots over flexible slots. The perturbation is only
    # used to resolve numerically tied assignments, never for reported points.
    slot_priority = {"SUPER_FLEX": 0, "FLEX": 1, "WR_RB": 1, "WR_TE": 1}
    tie_epsilon = 1e-9
    weight=[]
    for i,slot in enumerate(slots):
        priority = slot_priority.get(slot, 2)
        weight.append([bonus+float((x.get("projection") or {}).get("median_fantasy_points") or 0)+tie_epsilon*priority if _eligible(x,slot) else -1e12 for x in players]+[0.0]*n)
    # Hungarian algorithm (min-cost form, rectangular n <= cols).
    u=[0.0]*(n+1); v=[0.0]*(cols+1); match=[0]*(cols+1); way=[0]*(cols+1)
    for i in range(1,n+1):
        match[0]=i; j0=0; minv=[float('inf')]*(cols+1); used=[False]*(cols+1)
        while True:
            used[j0]=True; i0=match[j0]; delta=float('inf'); j1=0
            for j in range(1,cols+1):
                if used[j]: continue
                cur=-weight[i0-1][j-1]-u[i0]-v[j]
                if cur<minv[j]: minv[j]=cur; way[j]=j0
                if minv[j]<delta: delta=minv[j]; j1=j
            for j in range(cols+1):
                if used[j]: u[match[j]]+=delta; v[j]-=delta
                else: minv[j]-=delta
            j0=j1
            if match[j0]==0: break
        while True:
            j1=way[j0]; match[j0]=match[j1]; j0=j1
            if j0==0: break
    raw=[]
    for j in range(1,cols+1):
        if match[j] and j<=m and weight[match[j]-1][j-1]>-1e11:
            i=match[j]-1; raw.append((i,slots[i],j-1))
    raw.sort()
    filled=len(raw)
    total=sum(float((players[j].get("projection") or {}).get("median_fantasy_points") or 0) for _,_,j in raw)
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
            "high_fantasy_points": _projection_high(p.get("projection") or {}),
            "low_fantasy_points": (p.get("projection") or {}).get("low"),
            "hit_fantasy_points": (p.get("projection") or {}).get("hit"),
        })
    high_values = [a.get("high_fantasy_points") for a in assignment]
    low_values = [a.get("low_fantasy_points") for a in assignment]
    hit_values = [a.get("hit_fantasy_points") for a in assignment]
    # A missing high projection is unknown, not zero: never invent an upper bound.
    high_total = round(sum(float(v) for v in high_values), 4) if all(v is not None for v in high_values) else None
    open_slot_names = [slot for i, slot in enumerate(slots) if i not in filled_indices]
    return {
        "median_points": round(total, 4),
        "high_points": high_total,
        "low_points": round(sum(float(v) for v in low_values),4) if all(v is not None for v in low_values) else None,
        "hit_points": round(sum(float(v) for v in hit_values if v is not None),4),
        "hit_coverage": sum(v is not None for v in hit_values),
        "hit_complete": all(v is not None for v in hit_values),
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
