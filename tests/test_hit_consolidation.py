from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
import main


def test_player_search_uses_correct_platform_scoring():
    class Sleeper:
        def get_players(self): return {'1':{'full_name':'Test Receiver','position':'WR','team':'SF'}}
        def get_league(self, lid): return {'scoring_settings':{'rec':.5}}
    class Engine:
        sleeper=Sleeper()
        def project_candidate(self,p,universe,season,week,settings,starters=()):
            return {'name':p['full_name'],'projection':{'low':2,'median_fantasy_points':5,'high':10,'hit':7},'settings_used':settings}
    class ESPN:
        def __init__(self,season): pass
        def scoring_settings(self, lid): return {'rec':1.0}
    with patch.object(main,'_engine',return_value=Engine()),patch.object(main,'ESPNClient',ESPN):
        c=TestClient(main.app)
        for platform,rec in [('espn',1.0),('sleeper',.5)]:
            response=c.post('/api/v1/players/project',json={'names':'Test Receiver','platform':platform,'league_id':'123','week':6})
            assert response.status_code==200
            assert response.json()['players'][0]['settings_used']['rec']==rec
            assert response.json()['players'][0]['projection']['hit']==7


def test_dashboard_has_search_and_four_projections():
    text=(Path(__file__).resolve().parents[1]/'fantasy-matchup-dashboard/index.html').read_text()
    assert 'id="playerNames"' in text
    assert 'id="projectNamedPlayers"' in text
    assert 'function projectNamedPlayers()' in text
    assert '<th>Low</th><th>Median</th><th>High</th><th>Hit</th>' in text
