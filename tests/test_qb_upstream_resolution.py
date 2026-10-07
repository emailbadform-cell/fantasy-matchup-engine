from backend.services.matchup_service import MatchupService

class FakeNFL:
    def normalize_team(self,t): return {"LAR":"LA"}.get(t,t)


def test_qb_environment_comes_from_game_qb_not_projected_player():
    svc=MatchupService(nflverse=FakeNFL())
    rows=[
      {"player_id":"qb1","player_name":"Good QB","season":2026,"week":1,"recent_team":"DET","attempts":35,"passing_yards":300,"passing_tds":3,"interceptions":0},
      {"player_id":"wr1","player_name":"WR","season":2026,"week":1,"recent_team":"DET","targets":10,"receptions":7,"receiving_yards":90},
    ]
    game={"away_team":"DET","home_team":"CAR","away_qb_id":"qb1","away_qb_name":"Good QB","home_qb_id":"qb2","home_qb_name":"Bad QB"}
    q=svc._qb_environment(rows,game,"DET",2026,2,own=True)
    assert q["attempts"] > 0
    assert q["passing_yards"] > 0
