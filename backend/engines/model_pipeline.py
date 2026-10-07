from backend.engines.qb_engine import QBEngine
from backend.engines.offense_engine import OffenseEngine
from backend.engines.defense_engine import DefenseEngine
from backend.engines.position_engines import get_position_engine
from backend.engines.factor_engine import build_factor_state, weighted_score

class ModelPipeline:
    """
    Shared pipeline:
    Game -> QB -> Offense -> Defense -> Position -> Factors -> Projection.

    This is intentionally separate from Sleeper/NFLverse integrations.
    """
    def __init__(self):
        self.qb = QBEngine()
        self.offense = OffenseEngine()
        self.defense = DefenseEngine()

    def evaluate(self, player, context, historical=None):
        qb = self.qb.evaluate(context, historical)
        offense = self.offense.evaluate(context, qb, historical)
        defense = self.defense.evaluate(context, historical)
        position = get_position_engine(player.get("position")).evaluate(
            context, qb, offense, defense, historical
        )
        factors = build_factor_state()
        score = weighted_score(factors)
        return {
            "status": "architecture_ready",
            "player": player,
            "qb": qb,
            "offense": offense,
            "defense": defense,
            "position": position,
            "factors": factors,
            "factor_score": score,
        }
