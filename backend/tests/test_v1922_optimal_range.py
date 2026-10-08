import unittest
from backend.engine.optimizer import optimize_lineup

class OptimalRangeTests(unittest.TestCase):
    def test_high_sums_same_median_selected_starters(self):
        players = [
            {'player_id':'q1','position':'QB','projection':{'median_fantasy_points':20,'high_fantasy_points':28}},
            {'player_id':'q2','position':'QB','projection':{'median_fantasy_points':19,'high_fantasy_points':40}},
            {'player_id':'r1','position':'RB','projection':{'median_fantasy_points':15,'high_fantasy_points':24}},
        ]
        result = optimize_lineup(players,['QB','RB'])
        self.assertEqual(result['median_points'],35)
        self.assertEqual(result['high_points'],52)
        self.assertEqual([x['player_id'] for x in result['assignment']],['q1','r1'])
    def test_missing_high_remains_unknown(self):
        players=[{'player_id':'q','position':'QB','projection':{'median_fantasy_points':10}}]
        result=optimize_lineup(players,['QB'])
        self.assertIsNone(result['high_points'])
    def test_open_slot_contributes_zero(self):
        players=[{'player_id':'q','position':'QB','projection':{'median_fantasy_points':10,'high_fantasy_points':18}}]
        result=optimize_lineup(players,['QB','RB'])
        self.assertEqual(result['high_points'],18)
        self.assertEqual(result['open_slots'],1)

if __name__=='__main__': unittest.main()
