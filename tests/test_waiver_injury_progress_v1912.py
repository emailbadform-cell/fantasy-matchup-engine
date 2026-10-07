from main import _role_intel
from backend.engine.waivers import recommend_waiver_moves


def test_rb_backup_gets_injury_role_boost_when_player_ahead_is_out():
    universe={
      '1':{'full_name':'Starter','team':'DET','position':'RB','depth_chart_order':1,'injury_status':'Out'},
      '2':{'full_name':'Backup','team':'DET','position':'RB','depth_chart_order':2,'injury_status':''},
    }
    x=_role_intel(universe['2'],universe)
    assert x['depth_chart_promotion'] is True
    assert x['opportunity_multiplier'] > 1.0
    assert x['teammate_injuries'][0]['name']=='Starter'


def test_healthy_depth_chart_has_no_role_boost():
    universe={
      '1':{'full_name':'Starter','team':'DET','position':'RB','depth_chart_order':1,'injury_status':''},
      '2':{'full_name':'Backup','team':'DET','position':'RB','depth_chart_order':2,'injury_status':''},
    }
    x=_role_intel(universe['2'],universe)
    assert x['opportunity_multiplier']==1.0
    assert x['depth_chart_promotion'] is False


def test_waiver_brief_preserves_role_intelligence():
    slots=['RB']
    roster=[{'player_id':'old','name':'Old','position':'RB','eligible_positions':['RB'],'projection':{'median_fantasy_points':5}}]
    add={'player_id':'new','name':'New','position':'RB','eligible_positions':['RB'],'projection':{'median_fantasy_points':12},'waiver_role_intel':{'role_change':'Expected increased role','opportunity_multiplier':1.18}}
    out=recommend_waiver_moves(roster,[add],slots)
    assert out['moves'][0]['pickup']['waiver_role_intel']['opportunity_multiplier']==1.18


def test_progress_callback_is_emitted():
    calls=[]
    roster=[{'player_id':'old','name':'Old','position':'RB','eligible_positions':['RB'],'projection':{'median_fantasy_points':5}}]
    add={'player_id':'new','name':'New','position':'RB','eligible_positions':['RB'],'projection':{'median_fantasy_points':12}}
    recommend_waiver_moves(roster,[add],['RB'],progress=lambda d,t,m:calls.append((d,t,m)))
    assert calls and calls[0][0] == 1
