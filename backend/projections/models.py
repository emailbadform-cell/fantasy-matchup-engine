from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Projection:
    player_id: str
    low_ppr: float
    median_ppr: float
    high_ppr: float
    matchup: Optional[str] = None
    opportunity: Optional[str] = None
    efficiency: Optional[str] = None
    upside: Optional[str] = None
