from backend.integrations.espn import ESPNClient, espn_defense_team
from backend.engine.waivers import recommend_waiver_moves


def make_player(pid, pos, pts, *, bye=False):
    return {"player_id":pid,"name":pid,"position":pos,"on_bye":bye,"projection":{"median_fantasy_points":pts}}


def test_rams_defense_negative_id_without_metadata():
    assert espn_defense_team(-16014) == 'LAR'
    assert espn_defense_team(-16033) == 'BAL'
    assert espn_defense_team(-16999) is None


def test_rams_defense_full_espn_roster_crosswalk():
    client=ESPNClient()
    rams=make_player('LAR','DEF',5); rams['team']='LAR'
    qb=make_player('qb','QB',20); qb['team']='NE'; qb['espn_id']=123
    client.league=lambda league_id,week:{'teams':[{'id':1,'roster':{'entries':[
      {'playerId':123,'lineupSlotId':0,'playerPoolEntry':{'player':{'id':123,'fullName':'Quarterback','defaultPositionId':1,'proTeamId':17}}},
      {'playerId':-16014,'lineupSlotId':16,'playerPoolEntry':{'player':{'id':-16014,'fullName':'Rams D/ST'}}}
    ]}}]}
    client._player_crosswalk=lambda:({'LAR':rams,'qb':qb},{})
    client._nflverse_identity_index=lambda:{}
    client.lineup_settings=lambda league_id:{'starter_slots':['QB','DEF'],'expected_starters':2}
    client.scoring_settings=lambda league_id:{}
    result=client.normalized('123',1,5)
    assert result['lineup_settings']['occupied_starters']==2
    assert set(result['starters'])=={'LAR','qb'}


def test_waiver_pickup_must_start_and_replaced_starter_named():
    roster=[make_player('starter','QB',15),make_player('bench','QB',4),make_player('rb','RB',11)]
    add=[make_player('not_upgrade','QB',8),make_player('upgrade','QB',22)]
    result=recommend_waiver_moves(roster,add,['QB','RB'],max_moves=1)
    assert result['move_count']==1
    move=result['moves'][0]
    assert move['pickup']['player_id']=='upgrade'
    assert move['starter_replaced'][0]['player_id']=='starter'
    assert move['pickup_starting_slot']=='QB'
    assert move['drop']['player_id']=='bench'
    assert move['team_points_gain']==7


def test_bye_player_not_selected_as_drop():
    roster=[make_player('starter','QB',15),make_player('bye','QB',0,bye=True),make_player('bench','QB',4)]
    result=recommend_waiver_moves(roster,[make_player('upgrade','QB',22)],['QB'],max_moves=1)
    assert result['moves'][0]['drop']['player_id']=='bench'


def test_no_recommendation_for_nonstarting_pickup():
    roster=[make_player('starter','QB',22),make_player('bench','QB',3)]
    result=recommend_waiver_moves(roster,[make_player('worse','QB',18)],['QB'])
    assert result['move_count']==0
