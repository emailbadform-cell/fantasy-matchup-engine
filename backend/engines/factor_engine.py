"""
Shared model-factor architecture.

Every position eventually consumes the same factor pipeline.
These are contracts/defaults only until historical data is connected.
"""

DEFAULT_WEIGHTS = {
    "qb_environment": 0.18,
    "offensive_scheme": 0.14,
    "defensive_scheme": 0.14,
    "usage": 0.18,
    "position_matchup": 0.12,
    "game_environment": 0.10,
    "explosive_play": 0.07,
    "td_environment": 0.07,
}

def build_factor_state() -> dict:
    return {
        "qb_environment": 1.0,
        "offensive_scheme": 1.0,
        "defensive_scheme": 1.0,
        "usage": 1.0,
        "position_matchup": 1.0,
        "game_environment": 1.0,
        "explosive_play": 1.0,
        "td_environment": 1.0,
    }

def weighted_score(factors: dict, weights: dict = DEFAULT_WEIGHTS) -> float:
    return sum(
        float(factors.get(k, 1.0)) * float(w)
        for k, w in weights.items()
    )
