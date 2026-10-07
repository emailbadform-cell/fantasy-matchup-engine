import unittest
from unittest.mock import patch, Mock
from backend.integrations.espn import ESPNClient, ESPNAPIError, SCORING_IDS

class ESPNIntegrationTests(unittest.TestCase):
    def test_common_scoring_ids(self):
        self.assertEqual(SCORING_IDS[3],"pass_yd")
        self.assertEqual(SCORING_IDS[42],"rec_yd")
        self.assertEqual(SCORING_IDS[43],"rec_td")
        self.assertEqual(SCORING_IDS[53],"rec")
    def test_private_auth_error_is_clear(self):
        self.assertTrue(issubclass(ESPNAPIError,RuntimeError))

    @patch("backend.integrations.espn.httpx.get")
    def test_authenticated_request_uses_browser_ua_and_decodes_cookie(self, get):
        response=Mock(status_code=200)
        response.raise_for_status.return_value=None
        response.json.return_value={"id":83709501}
        get.return_value=response
        c=ESPNClient(2026, espn_s2="abc%2Bdef%3D%3D", swid="{TEST-SWID}")
        out=c._get("83709501",("mTeam",))
        self.assertEqual(out["id"],83709501)
        kw=get.call_args.kwargs
        self.assertEqual(kw["cookies"]["espn_s2"],"abc+def==")
        self.assertEqual(kw["cookies"]["SWID"],"{TEST-SWID}")
        self.assertIn("Mozilla/5.0",kw["headers"]["User-Agent"])

    @patch("backend.integrations.espn.httpx.get")
    def test_403_with_loaded_credentials_is_not_mislabeled_missing_auth(self, get):
        get.return_value=Mock(status_code=403)
        c=ESPNClient(2026, espn_s2="abc", swid="{TEST}")
        with self.assertRaises(ESPNAPIError) as cm:
            c._get("83709501",("mTeam",))
        self.assertIn("Credentials are loaded",str(cm.exception))

    @patch("backend.integrations.espn.ESPNClient._get")
    def test_scoring_translation_does_not_treat_td_points_as_yard_points(self, get):
        get.return_value={"settings":{"scoringSettings":{"scoringItems":[
            {"statId":42,"points":0.1},{"statId":43,"points":6},{"statId":53,"points":1}
        ]}}}
        c=ESPNClient(2026,espn_s2="x",swid="{x}")
        self.assertEqual(c.scoring_settings(1),{"rec_yd":0.1,"rec_td":6,"rec":1})

    @patch("backend.integrations.espn.ESPNClient._get")
    def test_lineup_settings_exclude_bench_and_ir(self, get):
        get.return_value={"settings":{"rosterSettings":{"lineupSlotCounts":{"0":1,"2":2,"4":2,"6":1,"16":1,"17":1,"20":7,"21":2,"23":1}}}}
        c=ESPNClient(2026,espn_s2="x",swid="{x}")
        out=c.lineup_settings(1)
        self.assertEqual(out["expected_starters"],9)
        self.assertNotIn("20",out["active_slot_counts"])
        self.assertNotIn("21",out["active_slot_counts"])

    @patch("backend.integrations.espn.ESPNClient._player_crosswalk")
    @patch("backend.integrations.espn.ESPNClient.scoring_settings")
    @patch("backend.integrations.espn.ESPNClient.lineup_settings")
    @patch("backend.integrations.espn.ESPNClient.league")
    def test_empty_configured_starter_slot_is_valid(self, league, lineup_settings, scoring_settings, player_crosswalk):
        players={"qb1":{"full_name":"QB One","team":"DET","position":"QB","espn_id":1},
                 "rb1":{"full_name":"RB One","team":"DET","position":"RB","espn_id":2}}
        player_crosswalk.return_value=(players,{})
        scoring_settings.return_value={}
        lineup_settings.return_value={"active_slot_counts":{"0":1,"2":1},"expected_starters":2}
        league.return_value={"teams":[{"id":1,"name":"Test","roster":{"entries":[
            {"playerId":1,"lineupSlotId":20,"playerPoolEntry":{"player":{"id":1,"fullName":"QB One","proTeamId":8,"defaultPositionId":1}}},
            {"playerId":2,"lineupSlotId":2,"playerPoolEntry":{"player":{"id":2,"fullName":"RB One","proTeamId":8,"defaultPositionId":2}}}
        ]}}],"schedule":[]}
        c=ESPNClient(2026,espn_s2="x",swid="{x}")
        out=c.normalized(1,1,5)
        self.assertEqual(out["starters"],["rb1"])
        self.assertEqual(out["lineup_settings"]["occupied_starters"],1)
        self.assertEqual(out["lineup_settings"]["open_starter_slots"],1)

    def test_name_normalization(self):
        self.assertEqual(ESPNClient._name("A.J. Brown"),"ajbrown")

if __name__ == '__main__': unittest.main()
