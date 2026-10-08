import unittest
from backend.scoring.league_rules import score, coverage
from backend.engine.features import scoring
from backend.integrations.espn import ESPNClient

class LeagueScoringTests(unittest.TestCase):
    def test_custom_half_ppr_zero_is_not_defaulted(self):
        row={'receptions': 4,'receiving_yards':60,'receiving_tds':1}
        self.assertAlmostEqual(scoring({'rec':.5},row,'WR'),14.0)
        self.assertAlmostEqual(scoring({'rec':0},row,'WR'),12.0)
    def test_qb_custom(self):
        self.assertAlmostEqual(score({'pass_td':6,'pass_int':-1},{'passing_tds':2,'interceptions':1},'QB'),11)
    def test_sleeper_int_alias_and_sacks(self):
        self.assertAlmostEqual(score({'pass_int':-1},{'interceptions':2},'QB'),-2)
        self.assertAlmostEqual(score({'int':3},{'interceptions':2},'DEF'),6)
        self.assertAlmostEqual(score({'sack':2,'def_int':4},{'sacks':3,'interceptions':2},'DEF'),14)
    def test_missed_kicks_are_calculated_from_attempts(self):
        self.assertAlmostEqual(score({'fgm':3,'xpm':1,'fgmiss':-1,'xpmiss':-2},
            {'field_goal_attempts':3,'field_goals':2,'extra_point_attempts':3,'extra_points':2},'K'),5)
    def test_completion_and_attempt_scoring(self):
        self.assertAlmostEqual(score({'pass_cmp':.5,'pass_att':-.1,'pass_inc':-.5},
            {'pass_attempts':20,'completions':15},'QB'),3)
    def test_kicker_and_defense(self):
        self.assertAlmostEqual(score({'fgm':4,'xpm':2},{'field_goals':2,'extra_points':3},'K'),14)
    def test_unsupported_bonus_is_exposed(self):
        report=coverage({'rec':.5,'fgm_50p':5,'pts_allow_0':10},'sleeper')
        self.assertFalse(report['fully_modeled'])
        self.assertEqual(report['unmodeled_configured_rules'],['fgm_50p','pts_allow_0'])
    def test_espy_unmapped_items_not_ignored(self):
        client=ESPNClient()
        client._get=lambda *a,**k:{'settings':{'scoringSettings':{'scoringItems':[
            {'statId':3,'points':.05},{'statId':9999,'points':5},{'statId':9998,'points':0}]}}}
        s=client.scoring_settings('123')
        self.assertEqual(s['pass_yd'],.05)
        self.assertIn('espn_stat_id:9999',coverage(s,'espn')['unmodeled_configured_rules'])
    def test_unmodeled_scoring_never_claims_complete(self):
        self.assertFalse(coverage({'bonus_rec_yd_100':3})['fully_modeled'])
    def test_scoring_does_not_mutate_input(self):
        rules={'rec':.5}; stats={'receptions':2}
        score(rules,stats,'RB')
        self.assertEqual(rules,{'rec':.5})
        self.assertEqual(stats,{'receptions':2})

if __name__ == '__main__':unittest.main()
