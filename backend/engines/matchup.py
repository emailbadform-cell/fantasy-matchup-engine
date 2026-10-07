from typing import Dict,Any

def matchup_context(player:Dict[str,Any], game:Dict[str,Any], usage:Dict[str,Any], qb:Dict[str,Any], defense:Dict[str,Any])->Dict[str,Any]:
    pos=player.get('position'); qb_factor=qb.get('qb_environment',1.0) if pos!='QB' else 1.0
    return {'position':pos,'qb_factor':qb_factor,'defensive_scheme':defense,'assignment':'data_pending','route_alignment':'data_pending','matchup_factor':1.0,'note':'Individual assignment and scheme data are pending until play-level/charting feeds are added.'}
