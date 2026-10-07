from typing import Dict, Any

def offensive_profile(game:Dict[str,Any], team:str)->Dict[str,Any]:
    return {'team':team,'home':str(game.get('home_team','')).upper()==team,'pace':'unknown','pass_rate':'data_pending','run_rate':'data_pending','red_zone':'data_pending','scheme_status':'foundation'}

def defensive_profile(team:str)->Dict[str,Any]:
    return {'team':team,'coverage':'data_pending','shell':'data_pending','blitz_rate':None,'pressure_rate':None,'run_defense':'data_pending','position_matchups':{'QB':'data_pending','RB_rush':'data_pending','RB_rec':'data_pending','WR_outside':'data_pending','WR_slot':'data_pending','TE':'data_pending','K':'data_pending','DEF':'data_pending'},'scheme_status':'foundation'}
