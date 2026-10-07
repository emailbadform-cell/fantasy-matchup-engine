from dataclasses import dataclass, field
from typing import Any, Dict, Optional

POSITIONS={"QB","RB","WR","TE","K","DEF"}

@dataclass
class GameContext:
    season:int; week:int; team:str; opponent:Optional[str]; game_id:Optional[str]
    game:Optional[Dict[str,Any]]; environment:Dict[str,Any]=field(default_factory=dict)

@dataclass
class PlayerContext:
    player_id:str; name:Optional[str]; position:Optional[str]; team:Optional[str]
    opponent:Optional[str]; game_context:GameContext
    status:Optional[str]=None; injury_status:Optional[str]=None
    identity:Dict[str,Any]=field(default_factory=dict)

@dataclass
class Projection:
    player_id:str; position:str; low:Dict[str,float]; median:Dict[str,float]
    high:Dict[str,float]; fantasy_points:Dict[str,float]; factors:Dict[str,float]
    confidence:float; audit:Dict[str,Any]=field(default_factory=dict)
