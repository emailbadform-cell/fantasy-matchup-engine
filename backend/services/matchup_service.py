from backend.integrations.sleeper import SleeperClient
from backend.integrations.nflverse import NFLVerseClient
from backend.services.model_service import ModelService
from backend.scoring.fantasy_scoring import from_sleeper

class MatchupService:
    def __init__(self,sleeper=None,nflverse=None):
        self.sleeper=sleeper or SleeperClient(); self.nflverse=nflverse or NFLVerseClient(); self.model=ModelService()
        self._cache={}
    def _user(self,users,owner_id):
        return next((u for u in users if str(u.get("user_id"))==str(owner_id)),None)
    def _player(self,players,pid):
        return players.get(str(pid),{}) if isinstance(players,dict) else {}
    def _game_context(self,season,week,team):
        g=self.nflverse.get_team_game(season,week,team); nt=self.nflverse.normalize_team(team); opp=self.nflverse.get_team_opponent(season,week,team); side=self.nflverse.get_team_side(team,g)
        def num(x):
            try:return float(x)
            except:return None
        return {"team":nt,"opponent":opp,"game_id":g.get("game_id") if g else None,"game":g,
          "environment":{"total_line":num(g.get("total_line")) if g else None,"spread_line":num(g.get("spread_line")) if g else None,
          "team_side":side,"gameday":g.get("gameday") if g else None,"gametime":g.get("gametime") if g else None,
          "rest_days":num(g.get("away_rest") if side=="away" else g.get("home_rest")) if g else None}}
    def _starter(self,pid,p,season,week):
        is_def=str(pid).upper() in {"ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL","DEN","DET","GB","HOU","IND","JAX","KC","LAC","LV","MIA","MIN","NE","NO","NYG","NYJ","PHI","PIT","SEA","SF","TB","TEN","WAS","LA"}
        team=p.get("team") or (str(pid).upper() if is_def else None); pos=p.get("position") or ("DEF" if is_def else None)
        ctx=self._game_context(season,week,team) if team else {"team":None,"opponent":None,"game_id":None,"game":None,"environment":{}}
        return {"player_id":str(pid),"name":p.get("full_name") or " ".join(x for x in [p.get("first_name"),p.get("last_name")] if x) or (p.get("team") or str(pid)),
          "position":pos,"team":team,"nfl_team":ctx["team"],"nfl_opponent":ctx["opponent"],"game":ctx["game"],"game_context":ctx,
          "status":p.get("status"),"injury_status":p.get("injury_status"),"identity":{"gsis_id":p.get("gsis_id"),"espn_id":p.get("espn_id"),"pfr_id":p.get("pfr_id")}}
    def _qb_environment(self, player_rows, game, team, season, week, own=True):
        """Resolve the relevant QB from the game's home/away QB identity and use that player's history.
        For DEF, own=False means use the opposing QB because the defense is facing him.
        """
        if not game:
            return self.model.qb.evaluate({}, {})
        team_n=self.nflverse.normalize_team(team)
        away=self.nflverse.normalize_team(game.get("away_team")); home=self.nflverse.normalize_team(game.get("home_team"))
        side="away" if team_n==away else "home"
        if not own: side="home" if side=="away" else "away"
        qid=game.get("away_qb_id") if side=="away" else game.get("home_qb_id")
        qname=game.get("away_qb_name") if side=="away" else game.get("home_qb_name")
        if qid:
            roll=self.model.features.rolling_player(player_rows,qid,season,week)
            if any((roll.get(w) or {}).get("attempts",0)>0 for w in roll):
                return self.model.qb.evaluate(roll, self.model.features.latest_player(player_rows,qid,season,week))
        # Fallback by name when GSIS IDs are not present in the stats release.
        for raw in player_rows or []:
            name=str(raw.get("player_display_name") or raw.get("player_name") or raw.get("name") or "")
            if qname and name.lower()==str(qname).lower():
                pid=raw.get("player_id") or raw.get("gsis_id")
                roll=self.model.features.rolling_player(player_rows,pid,season,week)
                return self.model.qb.evaluate(roll, self.model.features.latest_player(player_rows,pid,season,week))
        return self.model.qb.evaluate({}, {})

    def build(self,league_id,username,season,week,include_projections=True):
        league=self.sleeper.get_league(league_id); users=self.sleeper.get_users(league_id); rosters=self.sleeper.get_rosters(league_id); players=self.sleeper.get_players(); matchups=self.sleeper.get_matchups(league_id,week)
        user=next((u for u in users if str(u.get("display_name","")).lower()==username.lower() or str(u.get("username","")).lower()==username.lower()),None)
        if not user: raise ValueError(f"Sleeper user '{username}' not found")
        roster=next((r for r in rosters if str(r.get("owner_id"))==str(user.get("user_id"))),None)
        if not roster: raise ValueError("Roster not found")
        mid=next((m.get("matchup_id") for m in matchups if str(m.get("roster_id"))==str(roster.get("roster_id"))),None)
        opp=next((m for m in matchups if m.get("matchup_id")==mid and str(m.get("roster_id"))!=str(roster.get("roster_id"))),None)
        opp_user=self._user(users,opp.get("owner_id")) if opp else None
        player_rows=[]; team_rows=[]; data_errors=[]
        self.model.set_scoring(from_sleeper(league.get("scoring_settings") or {}))
        try: player_rows=self.nflverse.get_player_stats(season)
        except Exception as e: data_errors.append(f"player_stats: {e}")
        try: team_rows=self.nflverse.get_team_stats(season)
        except Exception as e: data_errors.append(f"team_stats: {e}")
        starters=[self._starter(pid,self._player(players,pid),season,week) for pid in (roster.get("starters") or [])]
        projections=[]
        if include_projections:
            for s in starters:
                if s["position"] not in {"QB","RB","WR","TE","K","DEF"}: continue
                # Sleeper gsis_id is preferred; fallback to Sleeper ID.
                model_player={"player_id":s["identity"].get("gsis_id") or s["player_id"],"name":s["name"],"position":s["position"],"team":s["nfl_team"]}
                if player_rows:
                    # The QB environment must come from the relevant team's QB, not from the
                    # player being projected. DEF uses the opposing QB environment.
                    own_qb = s["position"] != "DEF"
                    qb_env = self._qb_environment(player_rows, s["game"] or {}, s["nfl_team"], season, week, own=own_qb)
                    proj,detail=self.model.project(model_player,player_rows,team_rows,season,week,s["game"] or {},s["nfl_opponent"],qb_override=qb_env)
                else:
                    proj={"status":"data_limited","player":s["name"],"position":s["position"],"low":{},"median":{},"high":{},"fantasy_points":{"low":None,"median":None,"high":None},"factors":{},"confidence":.15,"audit":{"errors":data_errors}}
                    detail={}
                projections.append({"player_id":s["player_id"],**proj,"details":detail})
        return {"platform":"sleeper","schedule_source":"nflverse","architecture_version":"1.2.0","model_status":"full_architecture","scoring_settings":league.get("scoring_settings") or {},
          "season":season,"week":week,"league_id":league_id,"matchup_id":mid,
          "team":{"roster_id":roster.get("roster_id"),"owner_id":roster.get("owner_id"),"username":user.get("username"),"display_name":user.get("display_name"),"starters":starters},
          "opponent":{"roster_id":opp.get("roster_id") if opp else None,"owner_id":opp.get("owner_id") if opp else None,
             "username":opp_user.get("username") if opp_user else None,"display_name":opp_user.get("display_name") if opp_user else None,
             "starters":opp.get("starters",[]) if opp else []},
          "data_health":{"player_stats_loaded":bool(player_rows),"team_stats_loaded":bool(team_rows),"errors":data_errors},
          "projections":projections}
