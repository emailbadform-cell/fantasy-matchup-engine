class PositionEngine:
    def __init__(self, position):
        self.position = position

    def evaluate(self, context, qb_state=None, offense_state=None, defense_state=None, historical=None):
        return {
            "status": "architecture_ready",
            "position": self.position,
            "usage": 1.0,
            "matchup": (defense_state or {}).get("position_matchups", {}).get(self.position, 1.0),
            "qb_dependency": 1.0 if self.position in {"WR", "TE"} else None,
        }

def get_position_engine(position):
    return PositionEngine((position or "UNK").upper())
