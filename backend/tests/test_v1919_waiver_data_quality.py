from backend.integrations.nflverse import NFLVerseClient
from backend.engine.waivers import recommend_waiver_moves


def player(pid, pos, pts):
    return {'player_id':pid,'name':pid,'position':pos,'projection':{'median_fantasy_points':pts}}


def test_missing_individual_row_when_team_week_published_not_pending(monkeypatch):
    c=NFLVerseClient()
    monkeypatch.setattr(c,'team_game',lambda *args:{'week':'4'})
    monkeypatch.setattr(c,'player_stats',lambda season:[{'week':'4','recent_team':'WAS','player_id':'teammate'}])
    st=c.player_history_status(2026,'WAS',[{'week':'3'}],5)
    assert st['complete'] is True and st['status']=='player_week_unrecorded'


def test_missing_team_data_remains_pending(monkeypatch):
    c=NFLVerseClient()
    monkeypatch.setattr(c,'team_game',lambda *args:{'week':'4'})
    monkeypatch.setattr(c,'player_stats',lambda season:[{'week':'4','recent_team':'DAL','player_id':'someone'}])
    st=c.player_history_status(2026,'WAS',[{'week':'3'}],5)
    assert st['complete'] is False and st['status']=='data_pending'


def test_waiver_decision_does_not_claim_rest_of_season_value():
    roster=[player('current','QB',10),player('bench','QB',5)]
    result=recommend_waiver_moves(roster,[player('pickup','QB',12)],['QB'],max_moves=1)
    assert result['move_count']==1
    m=result['moves'][0]
    assert m['new_starter']=='pickup' and m['team_points_gain']==2
    assert m['decision'].startswith('Streaming only')
    assert m['rest_of_season_assessed'] is False
