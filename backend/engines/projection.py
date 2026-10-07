from typing import Dict, Any
from backend.models.contracts import GameContext


def build_projection(player_name: str, position: str, game_context: GameContext) -> Dict[str, Any]:
    """
    v0.2.1 projection contract.

    This is intentionally a transparent baseline, not the final trained model.
    The architecture is ready for historical usage, QB, scheme, coverage,
    explosive-play, and TD components.
    """
    position = (position or "UNK").upper()

    base = {
        "QB": {"pass_attempts": 0, "pass_yards": 0, "pass_tds": 0, "interceptions": 0, "rush_attempts": 0, "rush_yards": 0, "rush_tds": 0},
        "RB": {"rush_attempts": 0, "rush_yards": 0, "receptions": 0, "receiving_yards": 0, "receiving_tds": 0, "fumbles": 0},
        "WR": {"targets": 0, "receptions": 0, "receiving_yards": 0, "receiving_tds": 0, "rush_attempts": 0, "rush_yards": 0, "rush_tds": 0},
        "TE": {"targets": 0, "receptions": 0, "receiving_yards": 0, "receiving_tds": 0, "rush_attempts": 0, "rush_yards": 0, "rush_tds": 0},
        "K": {"fg_made": 0, "fg_attempts": 0, "xp_made": 0, "xp_attempts": 0},
        "DEF": {"sacks": 0, "interceptions": 0, "fumble_recoveries": 0, "def_tds": 0, "points_allowed": 0},
    }.get(position, {})

    factors = {
        "qb_environment": 1.0,
        "offensive_scheme": 1.0,
        "defensive_scheme": 1.0,
        "usage": 1.0,
        "coverage_matchup": 1.0,
        "game_environment": 1.0,
        "explosive_play": 1.0,
        "td_environment": 1.0,
    }

    return {
        "player": player_name,
        "position": position,
        "status": "baseline_contract_only",
        "low": base.copy(),
        "median": base.copy(),
        "high": base.copy(),
        "fantasy_points": {"low": 0.0, "median": 0.0, "high": 0.0},
        "factors": factors,
        "confidence": 0.0,
        "game_context": {
            "team": game_context.team,
            "opponent": game_context.opponent,
            "game_id": game_context.game_id,
            "environment": game_context.environment,
        },
    }
