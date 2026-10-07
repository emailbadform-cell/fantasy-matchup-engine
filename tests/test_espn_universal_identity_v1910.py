from unittest.mock import patch
from backend.integrations.espn import ESPNClient


def test_suffix_variants_are_equivalent():
    c=ESPNClient()
    assert c._name_variants('Harold Fannin Jr.') & c._name_variants('Harold Fannin')
    assert c._name_variants('Deebo Samuel Sr.') & c._name_variants('Deebo Samuel')


def test_nflverse_espn_id_bridge_contains_fannin():
    c=ESPNClient()
    idx=c._nflverse_identity_index()
    assert idx.get('5083076') == '00-0040663'


def test_fannin_resolves_through_espn_to_gsis_bridge():
    c=ESPNClient(2026,espn_s2='x',swid='{x}')
    sleeper={
        'hf': {'full_name':'Harold Fannin','position':'TE','team':'CLE','gsis_id':'00-0040663'},
    }
    league={'teams':[{'id':1,'name':'T','owners':['o'],'roster':{'entries':[{
        'playerId':5083076,'lineupSlotId':6,'playerPoolEntry':{'player':{
            'id':5083076,'fullName':'Harold Fannin Jr.','proTeamId':5,'defaultPositionId':4
        }}
    }]}}], 'schedule':[]}
    with patch.object(c,'league',return_value=league), \
         patch.object(c,'_player_crosswalk',return_value=(sleeper,{})), \
         patch.object(c,'lineup_settings',return_value={'starter_slots':['TE'],'expected_starters':1}), \
         patch.object(c,'scoring_settings',return_value={}):
        out=c.normalized('L',1,5)
    assert out['starters']==['hf']
    assert out['unresolved']==[]


def test_ambiguous_or_unknown_still_fails_closed():
    c=ESPNClient(2026,espn_s2='x',swid='{x}')
    sleeper={'x':{'full_name':'Someone Else','position':'TE','team':'CLE','gsis_id':'00-x'}}
    league={'teams':[{'id':1,'name':'T','owners':['o'],'roster':{'entries':[{
        'playerId':999999999,'lineupSlotId':6,'playerPoolEntry':{'player':{
            'id':999999999,'fullName':'Unknown Player','proTeamId':5,'defaultPositionId':4
        }}
    }]}}], 'schedule':[]}
    with patch.object(c,'league',return_value=league), \
         patch.object(c,'_player_crosswalk',return_value=(sleeper,{})), \
         patch.object(c,'lineup_settings',return_value={'starter_slots':['TE'],'expected_starters':1}), \
         patch.object(c,'scoring_settings',return_value={}):
        try: c.normalized('L',1,5)
        except Exception as e: assert ('crosswalk incomplete' in str(e) or 'no active starters' in str(e))
        else: raise AssertionError('unknown occupied starter must fail closed')
