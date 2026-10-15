import unittest
from backend.engine.hit_projection import hit_projection
from backend.engine.optimizer import optimize_lineup

class HitTests(unittest.TestCase):
    def test_qb_blend_and_chronology(self):
        p=[{'week':1,'passing_yards':250,'passing_tds':2},{'week':2,'passing_yards':270,'passing_tds':2},{'week':3,'passing_yards':9999,'passing_tds':99}]
        d=[{'passing_yards_allowed':280},{'passing_yards_allowed':300}]
        t=[{'week':1,'game_id':'a','opponent_team':'NE'},{'week':2,'game_id':'b','opponent_team':'NE'}]
        stats=[{'week':1,'game_id':'a','position':'QB','passing_tds':2},{'week':2,'game_id':'b','position':'QB','passing_tds':2},{'week':3,'game_id':'c','position':'QB','passing_tds':99}]
        r=hit_projection('QB',p,d,t,stats,'NE',3,{'rushing_yards':0,'rushing_tds':0,'interceptions':0},{'pass_yd':.04,'pass_td':4})
        self.assertEqual(r['stats']['passing_yards']['raw_blended_projection'],275)
        self.assertEqual(r['stats']['passing_yards']['blended_projection'],264)
        self.assertGreater(r['points'],0)
    def test_missing_defense_not_invented(self):
        r=hit_projection('WR',[{'week':1,'receiving_yards':40}],[],[],[],'NE',3,{}, {})
        self.assertIsNone(r['points'])
    def test_optimizer_hit_totals(self):
        p=[{'position':'WR','eligible_positions':['WR'],'projection':{'median_fantasy_points':10,'low':4,'high':20,'hit':12}}]
        r=optimize_lineup(p,['WR'])
        self.assertEqual(r['hit_points'],12)
        self.assertEqual(r['low_points'],4)

if __name__=='__main__':unittest.main()
