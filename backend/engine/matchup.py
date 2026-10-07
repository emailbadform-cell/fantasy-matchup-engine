from .features import clamp, safe_div, mean, f


def matchup_score(offense, defense):
    """Combine opponent-adjusted offense/defense factors into a bounded matchup multiplier."""
    values = [float(x) for x in (offense or {}).values() if isinstance(x, (int, float))]
    dvalues = [float(x) for x in (defense or {}).values() if isinstance(x, (int, float))]
    o = mean(values, 1.0)
    d = mean(dvalues, 1.0)
    return clamp(1.0 + (o - d) * 0.35, 0.82, 1.18)


def scheme_matchup(player_position, offense_context, defense_context):
    """Position-aware scheme proxy; explicitly labels proxies where granular tracking is unavailable."""
    pos = str(player_position or "UNK").upper()
    offense = offense_context or {}
    defense = defense_context or {}
    pass_rate = float(offense.get("pass_rate", 0.58))
    coverage = float(defense.get("coverage_factor", 1.0))
    pressure = float(defense.get("pressure_factor", 1.0))
    if pos == "RB":
        factor = 1.0 + (1 - pass_rate) * 0.08
    elif pos in {"WR", "TE"}:
        factor = 1.0 + (pass_rate - 0.58) * 0.20
    elif pos == "QB":
        factor = 1.0 + (pass_rate - 0.58) * 0.10 - (pressure - 1) * 0.15
    else:
        factor = 1.0
    factor *= coverage
    return {"factor": clamp(factor, 0.82, 1.18), "status": "derived_proxy", "position": pos}


def matchup_feature_bundle(team_rows, opponent_rows, game):
    """Produces the complete matchup feature family in one deterministic bundle."""
    team_pass = mean([f(r, "attempts", "passing_attempts") for r in team_rows], 34)
    team_plays = mean([f(r, "offensive_plays", "plays") for r in team_rows], 63)
    pass_rate = safe_div(team_pass, team_plays, 0.58)
    opp_pass = mean([f(r, "attempts", "passing_attempts") for r in opponent_rows], 34)
    opp_plays = mean([f(r, "offensive_plays", "plays") for r in opponent_rows], 63)
    pressure = clamp(1 + (opp_pass / max(opp_plays, 1) - 0.58) * 0.5, 0.90, 1.10)
    return {
        "offense": {"pass_rate": clamp(pass_rate, 0.35, 0.75), "plays": team_plays},
        "defense": {"pressure_factor": pressure},
        "environment": {
            "total": f(game, "total_line", "total"),
            "spread": f(game, "spread_line", "spread"),
        },
    }
