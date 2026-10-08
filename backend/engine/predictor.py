import re
from .features import *
from .layers import PREDICTIVE_LAYERS, propagation_audit
from .qb_monte_carlo import simulate_qb_stats

DEF_TEAMS = {"ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL","DEN","DET","GB","HOU","IND","JAX","KC","LV","LAC","LA","MIA","MIN","NE","NO","NYG","NYJ","PHI","PIT","SF","SEA","TB","TEN","WAS"}


def sleeper_starter_slot_map(starter_ids, league_slots):
    """Bind each Sleeper matchup starter ID to its own league slot.

    The roster player list has no positional relationship to league slots.
    Sleeper matchup `starters` *does*: it follows active `roster_positions`,
    including vacant placeholders, which must keep their indices.
    """
    slots=[str(s).upper() for s in (league_slots or [])
           if str(s).upper() not in {"BN", "BENCH", "IR", "RESERVE", "TAXI"}]
    ids=list(starter_ids or [])
    if not slots or len(slots) != len(ids):
        return {}
    mapping={}
    for index,(pid,slot) in enumerate(zip(ids,slots)):
        if pid is None or str(pid) in {"0", "", "None"}:
            continue
        key=str(pid)
        if key in mapping:
            return {}  # ambiguous starter IDs must not receive guessed labels
        mapping[key]={"starting_slot":slot,"starting_slot_index":index}
    return mapping


class PredictionEngine:
    """Pregame fantasy prediction pipeline with explicit single-owner feature architecture."""

    def __init__(self, sleeper, nfl, model_version):
        self.sleeper, self.nfl, self.model_version = sleeper, nfl, model_version
        self._crosswalk = None

    def _load_crosswalk(self):
        if self._crosswalk is not None:
            return self._crosswalk
        try:
            rows = self.nfl.player_id_map()
        except Exception:
            rows = []
        by_gsis, by_name = {}, {}
        for r in rows:
            gs = str(r.get("gsis_id") or r.get("player_id") or "")
            name = str(r.get("display_name") or r.get("player_name") or "").strip().lower()
            if gs:
                by_gsis[gs] = r
            if name:
                by_name[name] = r
        self._crosswalk = {"by_gsis": by_gsis, "by_name": by_name, "rows": rows}
        return self._crosswalk

    def _resolve_identity(self, player):
        direct = player.get("gsis_id") or player.get("gsis")
        if direct:
            return {"resolved_id": str(direct), "method": "sleeper_gsis", "confidence": 1.0}
        cw = self._load_crosswalk()
        name = str(player.get("full_name") or player.get("name") or "").strip().lower()
        row = cw["by_name"].get(name)
        if row:
            return {"resolved_id": str(row.get("gsis_id") or row.get("player_id")), "method": "nflverse_name", "confidence": .92}
        return {"resolved_id": None, "method": "unresolved", "confidence": 0.0}

    def _player_rows(self, player, season, week):
        if not player:
            return [], {"resolved_id": None, "method": "unavailable", "confidence": 0.0}
        identity = self._resolve_identity(player)
        rid = identity.get("resolved_id")
        rows = self.nfl.player_history(season, player_id=rid, through_week=week) if rid else []
        if not rows:
            name = player.get("full_name") or player.get("name")
            if name:
                rows = self.nfl.player_history(season, player_name=name, through_week=week)
                if not rows:
                    base_name = re.sub(r"\s+(jr\.?|sr\.?|ii|iii|iv)$", "", str(name), flags=re.I).strip()
                    if base_name and base_name != name:
                        rows = self.nfl.player_history(season, player_name=base_name, through_week=week)
        return rows, identity

    def _team_rows(self, team, season, week):
        return self.nfl.team_history(season, normalize_team(team), through_week=week)

    def _defense_rows(self, team, season, week):
        try:
            return self.nfl.defense_history(season, normalize_team(team), through_week=week)
        except Exception:
            return []

    def _canonical(self, r):
        return {
            "attempts": f(r,"attempts","passing_attempts","pass_attempts"),
            "completions": f(r,"completions","passing_completions","pass_cmp"),
            "passing_yards": f(r,"passing_yards","pass_yards"),
            "passing_tds": f(r,"passing_tds","pass_tds"),
            "interceptions": f(r,"interceptions","passing_interceptions","ints"),
            "carries": f(r,"carries","rushing_attempts","rush_attempts"),
            "rushing_yards": f(r,"rushing_yards","rush_yards"),
            "rushing_tds": f(r,"rushing_tds","rush_tds"),
            "targets": f(r,"targets","receiving_targets"),
            "receptions": f(r,"receptions","rec"),
            "receiving_yards": f(r,"receiving_yards","receiving_yds","rec_yards"),
            "receiving_tds": f(r,"receiving_tds","rec_tds"),
            "field_goals": f(r,"fg_made","field_goals"),
            "field_goal_attempts": f(r,"fg_att","field_goal_attempts"),
            "extra_points": f(r,"pat_made","extra_points"),
            "extra_point_attempts": f(r,"pat_att","extra_point_attempts"),
            "sacks": f(r,"sacks","def_sacks","sacks_allowed"),
            "interceptions_def": f(r,"def_interceptions","def_ints"),
            "fumble_recoveries": f(r,"fumble_recoveries","def_fumble_recoveries"),
            "fumbles_lost": f(r,"fumbles_lost","fumble_lost"),
        }

    def _base_stats(self, rows):
        keys = self._canonical({}).keys()
        if not rows:
            return {k: 0.0 for k in keys}
        c = [self._canonical(r) for r in rows]
        return {k: weighted_recent([x[k] for x in c], 0) for k in keys}

    def _team_aggregate(self, rows):
        by_week = {}
        for r in rows:
            by_week.setdefault(str(r.get("week", "")), []).append(r)
        out = []
        for wk, rs in by_week.items():
            qbs = [r for r in rs if str(r.get("position") or "").upper() == "QB"]
            pass_att = sum(f(r,"attempts","passing_attempts","pass_attempts") for r in qbs) or sum(f(r,"attempts","passing_attempts","pass_attempts") for r in rs)
            pass_yards = sum(f(r,"passing_yards","pass_yards") for r in qbs) or sum(f(r,"passing_yards","pass_yards") for r in rs)
            rush = sum(f(r,"carries","rushing_attempts","rush_attempts") for r in rs)
            ry = sum(f(r,"rushing_yards","rush_yards") for r in rs)
            targets = sum(f(r,"targets","receiving_targets") for r in rs)
            rec = sum(f(r,"receptions","rec") for r in rs)
            sacks = sum(f(r,"sacks_allowed","sacks") for r in qbs) or sum(f(r,"sacks_allowed","sacks") for r in rs)
            plays = max(pass_att + rush, 1)
            out.append({"week": wk, "attempts": pass_att, "passing_yards": pass_yards, "rushing_attempts": rush, "rushing_yards": ry, "targets": targets, "receptions": rec, "sacks": sacks, "offensive_plays": plays})
        return out

    def _team_shares(self, player_rows, team_rows):
        ta = self._team_aggregate(team_rows)
        tp = mean([x["targets"] for x in ta], 36)
        tc = mean([x["rushing_attempts"] for x in ta], 26)
        pt = mean([f(r,"targets") for r in player_rows], 0)
        pc = mean([f(r,"carries","rushing_attempts") for r in player_rows], 0)
        return {"target_share": clamp(safe_div(pt,tp,.10),.01,.40), "rush_share": clamp(safe_div(pc,tc,.18),.01,.80)}

    def _opportunity_factor(self, volume, base, pos):
        if pos == "QB":
            key, out = "attempts", "pass_attempts"
        elif pos == "RB":
            key, out = "carries", "carries"
        elif pos in {"WR","TE"}:
            key, out = "targets", "targets"
        else:
            return 1.0
        return clamp(safe_div(float(volume.get(out,0)), max(float(base.get(key,0)),1.0), 1.0), .75, 1.25)

    @staticmethod
    def _impact(factor):
        return round(float(factor) - 1.0, 6)

    @staticmethod
    def _td_factor(rz):
        return clamp(rz.get("td_rate_proxy", .04) / .04, .75, 1.25)

    def _qb_corrected_volume(self, history, team_rows, gs):
        """Chronology-safe QB attempt estimate.

        Uses the same pre-target-week history already returned by _player_rows,
        emphasizes recent starts, blends player and team volume, and only applies
        half of the schedule-derived pass tendency. This prevents a single spread
        assumption from collapsing a starter's attempt projection.
        """
        attempts = [f(r, "attempts", "passing_attempts", "pass_attempts") for r in history]
        attempts = [x for x in attempts if x > 0]
        player_recent = weighted_recent(attempts, 34) if attempts else 34.0
        team_agg = self._team_aggregate(team_rows)
        team_attempts = [f(r, "attempts", "passing_attempts", "pass_attempts") for r in team_agg]
        team_attempts = [x for x in team_attempts if x > 0]
        team_recent = weighted_recent(team_attempts, player_recent) if team_attempts else player_recent
        baseline = .80 * player_recent + .20 * team_recent
        directional = 1.0 + (float(gs.get("pass_factor", 1.0)) - 1.0) * .50
        return clamp(baseline * directional, 20, 48)

    @staticmethod
    def _qb_efficiency_stack(*factors):
        """Bound compounded contextual YPA effects; avoids multiplicative blow-ups."""
        product = 1.0
        for factor in factors:
            product *= float(factor)
        return clamp(product, .85, 1.15)

    def _factor_ledger(self, pos, factors, ownership):
        """Return an explicit ownership/activation ledger used by audit and calibration."""
        ledger = []
        for name, item in factors.items():
            if name in {"monte_carlo"}:
                continue
            owner = ownership.get(name, "diagnostic")
            ledger.append({
                "layer": name,
                "owner": owner,
                "status": item.get("status", "missing"),
                "active": bool(item.get("active", False)),
                "impact": item.get("impact"),
                "applied_to": item.get("applied_to", []),
            })
        # A layer may share an outcome family (for example, multiple uncertainty
        # components) without double-counting. The collision guard therefore checks
        # the exact formula slot, not merely the broad owner label.
        slots = {}
        for x in ledger:
            for slot in x.get("applied_to", []):
                slots.setdefault(slot, []).append(x["layer"])
        allowed_shared = {
            "role_volume": {"opportunity", "injury_role_change"},
            "simulation_sd": {"replacement", "explosive"},
            "receiver_targets": {"route_alignment", "coverage_assignment"},
            "efficiency": {"position_matchup", "defensive_scheme"},
            "pass_efficiency": {"weather", "surface"},
        }
        collisions = {}
        for slot, names in slots.items():
            if len(names) <= 1:
                continue
            allowed = allowed_shared.get(slot, set())
            if set(names) - allowed:
                collisions[slot] = names
        return {
            "position": pos,
            "layers": ledger,
            "single_owner_rule": True,
            "formula_slot_collisions": collisions,
            "double_counting_detected": bool(collisions),
        }

    def _project_player(self, player, players, game, opponent, season, week, settings, starters):
        pid = player.get("player_id")
        pos = str(player.get("position") or ("DEF" if normalize_team(pid) in DEF_TEAMS else "UNK")).upper()
        team = normalize_team(player.get("team") or player.get("nfl_team") or pid)
        history, identity = self._player_rows(player, season, week)
        base = self._base_stats(history)
        team_raw = self._team_rows(team, season, week)
        opp_raw = self._team_rows(opponent, season, week)
        team_rows = self._team_aggregate(team_raw)
        opp_rows = self._team_aggregate(opp_raw)
        opp_defense = self._defense_rows(opponent, season, week)

        gs = game_script(game, team)
        volume_team = play_volume(team_rows, game, team)
        weather_i = weather(game)
        surface_i = surface(game)
        avail = availability(player)
        ol = offensive_line_factor(team_rows)
        dl = defensive_front_factor(opp_defense)
        trench = trench_matchup(ol, dl)
        shares = self._team_shares(history, team_raw)
        volume = opportunity(history, team_raw, pos, gs, shares)
        role_opportunity_multiplier = float(player.get("role_opportunity_multiplier") or 1.0)
        if pos == "RB":
            volume["carries"] = volume.get("carries", 0) * role_opportunity_multiplier
            volume["targets"] = volume.get("targets", 0) * min(role_opportunity_multiplier, 1.25)
        elif pos in {"WR","TE"}:
            volume["targets"] = volume.get("targets", 0) * role_opportunity_multiplier
        align = route_alignment(player, history)
        cov = coverage_assignment(player, opp_defense)
        pos_match = position_matchup(pos, opp_defense)
        off_scheme = offensive_scheme(team_rows)
        def_scheme = defensive_scheme(opp_defense)
        rz = red_zone(team_rows)
        expl = explosive(history)
        qb = self._qb_for_team(players, team)
        qb_hist, qb_identity = self._player_rows(qb, season, week)
        qb_base = self._base_stats(qb_hist)
        qb_att = qb_base.get("attempts", 0)
        qb_ypa = safe_div(qb_base.get("passing_yards",0), qb_att, 7)
        qb_eff = clamp(qb_ypa / 7, .75, 1.25)
        qbc = qb_correlation(qb_eff, pos)
        coaching_i = coaching(game, team)
        ref = referee(game)
        replacement = replacement_factor(starters, pid)

        # Stage 1 ownership rules:
        # - game_script owns pace and directional pass/rush volume
        # - play_volume is diagnostic only (never another multiplier)
        # - offensive_scheme owns offensive distribution tendency
        # - defensive_scheme owns pressure/efficiency effect
        # - OL-vs-DL owns trench interaction; raw OL/DL remain diagnostics
        # - position_matchup owns position-specific allowed-production adjustment
        # - weather owns weather; surface owns indoor/surface adjustment
        # - opportunity owns player share/role volume
        # - red_zone owns TD-rate adjustment only
        # - explosive affects uncertainty, not the median directly
        # - replacement affects uncertainty only
        # - referee/coaching remain metadata until historical data exists
        game_factor = gs["pace_factor"]
        offensive_distribution = scheme_offense_factor(pos, off_scheme)
        defensive_efficiency = scheme_defense_factor(pos, def_scheme)
        matchup_factor = pos_match["factor"] if pos_match.get("status") == "data_backed" else 1.0
        td_factor = self._td_factor(rz)
        env_factor = weather_i["pass_factor"] if pos in {"QB","WR","TE"} else weather_i["kick_factor"]
        surface_factor = surface_i["pass_factor"] if pos in {"QB","WR","TE"} else 1.0

        base_stats = {}
        if pos == "QB":
            # Corrected QB branch (v1.8): chronology-safe recent volume, damped
            # game-script direction, bounded efficiency stacking, and QB-specific
            # TD rate. The generic team TD/play red-zone proxy is intentionally
            # NOT applied to passing TDs.
            attempts = self._qb_corrected_volume(history, team_raw, gs) * game_factor
            comp = clamp(safe_div(base.get("completions"), max(base.get("attempts"),1), .64), .50, .75)
            ypa = clamp(safe_div(qb_base.get("passing_yards"), max(qb_att,1), 7), 5.5, 9)
            efficiency_stack = self._qb_efficiency_stack(
                env_factor, surface_factor, offensive_distribution,
                defensive_efficiency, matchup_factor,
            )
            ypa *= efficiency_stack
            tdr = clamp(safe_div(qb_base.get("passing_tds"), max(qb_att,1), .035), .015, .075)
            rush = max(base.get("carries",0),2) * gs["rush_factor"] * trench
            ry = rush * safe_div(base.get("rushing_yards"), max(base.get("carries"),1), 4)
            base_stats = {
                "pass_attempts": attempts * avail["availability"],
                "completions": attempts * comp * avail["availability"],
                "passing_yards": attempts * ypa * avail["availability"],
                "passing_tds": attempts * tdr * avail["availability"],
                "interceptions": attempts * clamp(safe_div(qb_base.get("interceptions"), max(qb_att,1), .025), .005, .08) * avail["availability"],
                "rushing_yards": ry * avail["availability"],
                "rushing_tds": rush * clamp(safe_div(base.get("rushing_tds"), max(base.get("carries"),1), .03), 0, .15) * td_factor * avail["availability"],
            }
        elif pos == "RB":
            carries = volume.get("carries",12) * game_factor * offensive_distribution * defensive_efficiency * matchup_factor * avail["availability"]
            ry = carries * clamp(safe_div(base.get("rushing_yards"), max(base.get("carries"),1),4.2), 2.5, 6.5)
            targets = volume.get("targets",3) * qbc["qb_effect"] * offensive_distribution * matchup_factor * avail["availability"]
            rec = targets * clamp(safe_div(base.get("receptions"), max(base.get("targets"),1),.72), .4, .95)
            rcy = rec * clamp(safe_div(base.get("receiving_yards"), max(base.get("receptions"),1),7.5), 4, 13) * env_factor * surface_factor
            base_stats = {
                "carries": carries, "rushing_yards": ry, "targets": targets, "receptions": rec,
                "receiving_yards": rcy,
                "rushing_tds": max(0, carries / 18 * td_factor),
                "receiving_tds": max(0, targets / 25 * td_factor * .35),
            }
        elif pos in {"WR","TE"}:
            role_factor = clamp(1 + (align.get("route_share",.75)-.75)*.20, .92, 1.08)
            targets = volume.get("targets",5) * qbc["qb_effect"] * cov["coverage_factor"] * avail["availability"] * role_factor * game_factor * offensive_distribution * defensive_efficiency * matchup_factor
            rec = targets * clamp(safe_div(base.get("receptions"), max(base.get("targets"),1),.66), .35, .90)
            ypr = clamp(safe_div(base.get("receiving_yards"), max(base.get("receptions"),1), 10 if pos=="WR" else 8), 4, 18)
            base_stats = {
                "targets": targets, "receptions": rec, "receiving_yards": rec*ypr*env_factor*surface_factor,
                "receiving_tds": max(0, targets/22 * td_factor * qbc["qb_effect"] * offensive_distribution),
            }
        elif pos == "K":
            team_points = gs["team_points"] * weather_i["kick_factor"]
            fga = max(0, team_points/18)
            xpa = max(0, team_points/7)
            base_stats = {"field_goal_attempts": fga, "field_goals": fga*.86, "extra_point_attempts": xpa, "extra_points": xpa*.94}
        elif pos == "DEF":
            opp_qb = self._qb_for_team(players, opponent)
            opp_hist, _ = self._player_rows(opp_qb, season, week)
            opp_base = self._base_stats(opp_hist)
            df = defensive_fantasy(opp_base, opp_defense)
            sacks = df["sacks"] * def_scheme["pressure_factor"]
            ints = clamp(df["interception_rate"] * max(opp_base.get("attempts",0),1), .2, 2.2)
            base_stats = {"sacks": sacks, "interceptions": ints, "fumble_recoveries": df["fumble_recovery_rate"], "def_tds": df["def_td_rate"]}
        else:
            base_stats = {"fantasy_points": 0}

        fp = scoring(settings, base_stats, pos)
        confidence = confidence_score(len(history), bool(qb), ["available","derived"], pos)
        uncertainty_multiplier = clamp(1 + (1-replacement)*.50, 1.0, 1.12)
        sd = max(2, abs(fp) * (.18 + expl["explosive_rate"]*.45 + (1-confidence)*.30) * uncertainty_multiplier)
        sim = simulation(fp, sd, 4000, 13 + sum(ord(c) for c in str(pid)))
        stat_sim = None
        if pos == "QB":
            import os
            stat_n = int(os.getenv("FME_QB_STAT_MC_N", "1000000"))
            stat_sim = simulate_qb_stats(
                base_stats, history, settings, n=stat_n,
                seed=13013 + sum(ord(c) for c in str(pid)),
            )

        factors = {
            "availability": {"source":"sleeper", "status":"available", "value":avail["availability"], "impact":self._impact(avail["availability"]), "active":avail["availability"] != 1.0, "owner":"availability", "applied_to":["all_projected_stats"]},
            "replacement": {"source":"sleeper_roster", "status":"derived", "value":replacement, "impact":round(uncertainty_multiplier-1,6), "active":replacement < 1.0, "owner":"uncertainty", "applied_to":["simulation_sd"]},
            "offensive_line": {"source":"nflverse_team_stats", "status":"data_backed" if team_rows else "unavailable", "value":ol, "impact":self._impact(ol), "active":False, "owner":"trench_diagnostic", "applied_to":[]},
            "defensive_front": {"source":"nflverse_team_defense", "status":"data_backed" if opp_defense else "unavailable", "value":dl, "impact":self._impact(dl), "active":False, "owner":"trench_diagnostic", "applied_to":[]},
            "trench_matchup": {"source":"derived", "status":"derived", "value":trench, "impact":self._impact(trench), "active":pos=="QB", "owner":"trench_interaction", "applied_to":["qb_rushing"]},
            "game_script": {"source":"nflverse_schedule", "status":"schedule_data", "value":gs, "impact":self._impact(game_factor), "active":True, "owner":"game_script", "applied_to":["pace"]},
            "play_volume": {"source":"nflverse_team_stats", "status":"data_backed" if team_rows else "unavailable", "value":volume_team, "impact":0.0, "active":False, "owner":"diagnostic", "applied_to":[]},
            "injury_role_change": {"source":"sleeper_player_status", "status":"derived", "value":player.get("waiver_role_intel") or {}, "impact":round(role_opportunity_multiplier-1,6), "active":role_opportunity_multiplier != 1.0, "owner":"injury_role_change", "applied_to":["role_volume"] if role_opportunity_multiplier != 1.0 else []},
            "opportunity": {"source":"nflverse_player_stats", "status":"data_backed" if history else "fallback", "value":{**volume,**shares}, "impact":self._impact(self._opportunity_factor(volume,base,pos)), "active":pos in {"QB","RB","WR","TE"}, "owner":"opportunity", "applied_to":["role_volume"]},
            "route_alignment": {"source":"nflverse_player_stats", "status":"data_backed" if history else "fallback", "value":align, "impact":self._impact(clamp(1+(align.get('route_share',.75)-.75)*.20,.92,1.08)), "active":pos in {"WR","TE"}, "owner":"role", "applied_to":["receiver_targets"]},
            "coverage_assignment": {"source":"nflverse_team_defense", "status":cov.get("status","unavailable"), "value":cov, "impact":self._impact(cov["coverage_factor"]), "active":pos in {"WR","TE"} and cov.get("status")=="position_defense_data", "owner":"coverage", "applied_to":["receiver_targets"]},
            "weather": {"source":"nflverse_schedule", "status":"schedule_data", "value":weather_i, "impact":self._impact(env_factor), "active":pos in {"QB","WR","TE","K"}, "owner":"weather", "applied_to":["pass_efficiency" if pos in {"QB","WR","TE"} else "kicking"]},
            "surface": {"source":"nflverse_schedule", "status":"schedule_data", "value":surface_i, "impact":self._impact(surface_factor), "active":pos in {"QB","WR","TE"}, "owner":"surface", "applied_to":["pass_efficiency"]},
            "referee": {"source":"nflverse_schedule", "status":ref["data_status"], "value":ref, "impact":0.0, "active":False, "owner":"metadata", "applied_to":[]},
            "coaching": {"source":"nflverse_schedule", "status":coaching_i.get("data_status","name_only"), "value":coaching_i, "impact":0.0, "active":False, "owner":"metadata", "applied_to":[]},
            "red_zone": {"source":"nflverse_team_stats", "status":rz.get("status","proxy"), "value":rz, "impact":0.0 if pos=="QB" else self._impact(td_factor), "active":pos!="QB", "owner":"touchdown_rate", "applied_to":[] if pos=="QB" else ["td_expectation"]},
            "explosive": {"source":"nflverse_player_stats", "status":"data_backed" if history else "fallback", "value":expl, "impact":expl["explosive_rate"], "active":True, "owner":"uncertainty", "applied_to":["simulation_sd"]},
            "qb_correlation": {"source":"nflverse_player_stats", "status":"data_backed" if qb_hist else "fallback", "value":qbc, "impact":self._impact(qbc["qb_effect"]), "active":pos in {"WR","TE","RB"}, "owner":"qb_dependency", "applied_to":["skill_volume"]},
            "position_matchup": {"source":"nflverse_team_defense", "status":pos_match.get("status","unavailable"), "value":pos_match, "impact":self._impact(matchup_factor), "active":pos in {"QB","RB","WR","TE"} and pos_match.get("status")=="data_backed", "owner":"position_matchup", "applied_to":["efficiency"]},
            "offensive_scheme": {"source":"nflverse_team_stats", "status":off_scheme["status"], "value":off_scheme, "impact":self._impact(offensive_distribution), "active":pos in {"QB","RB","WR","TE"}, "owner":"offensive_scheme", "applied_to":["distribution"]},
            "defensive_scheme": {"source":"nflverse_team_defense", "status":def_scheme["status"], "value":def_scheme, "impact":self._impact(defensive_efficiency), "active":pos in {"QB","RB","WR","TE"} and def_scheme["status"]=="data_backed", "owner":"defensive_scheme", "applied_to":["efficiency"]},
            "defensive_fantasy": {"source":"nflverse_team_defense", "status":def_scheme["status"], "value":base_stats if pos=="DEF" else {"opponent_pressure":def_scheme["pressure_factor"]}, "impact":self._impact(def_scheme["pressure_factor"]), "active":pos=="DEF" and def_scheme["status"]=="data_backed,", "owner":"defensive_fantasy", "applied_to":["defense_stats"]},
            "monte_carlo": {"source":"engine", "status":"available", "value":sim, "impact":None, "active":True, "owner":"simulation", "applied_to":["distribution"]},
        }
        # Correct accidental string typo defensively; keeps the output contract stable.
        factors["defensive_fantasy"]["active"] = bool(pos=="DEF" and def_scheme["status"]=="data_backed")

        ownership = {k:v.get("owner","diagnostic") for k,v in factors.items()}
        factor_ledger = self._factor_ledger(pos, factors, ownership)
        if factor_ledger["double_counting_detected"]:
            raise RuntimeError(f"Predictive factor ownership collision: {factor_ledger['formula_slot_collisions']}")

        effective_history = len(history) if pos != "DEF" else len(opp_defense)
        history_freshness = self.nfl.player_history_status(season, team, history, week) if pos != "DEF" else {"status":"not_applicable","complete":True,"required_week":max(0,int(week)-1),"latest_week":None}
        dq = {
            "historical_rows": len(history),
            "effective_context_rows": effective_history,
            "qb_linked": bool(qb) if pos != "DEF" else True,
            "status": "usable" if effective_history>=3 else ("limited" if effective_history else "fallback"),
            "projection_status": "usable" if confidence>=.55 else "limited",
            "fallback_used": effective_history==0,
            "history_freshness": history_freshness,
            "history_complete": bool(history_freshness.get("complete", True)),
            "history_status": history_freshness.get("status", "unknown"),
        }
        if not dq["history_complete"]:
            dq["projection_status"] = "data_pending"
        return {
            "player_id":pid,"name":player.get("full_name") or player.get("name"),"position":pos,"eligible_positions":list(player.get("fantasy_positions") or ([pos] if pos else [])),"team":team,"opponent":opponent,
            "historical_games":len(history),"historical":base,"identity":identity,
            "projection":{**base_stats,"median_fantasy_points":(stat_sim["fantasy_points"]["p50"] if stat_sim else sim["p50"]),"low":(stat_sim["fantasy_points"]["p10"] if stat_sim else sim["p10"]),"high":(stat_sim["fantasy_points"]["p90"] if stat_sim else sim["p90"])},
            "distribution":sim,"stat_distribution":stat_sim,"confidence":confidence,"factors":factors,"layer_audit":propagation_audit(factors),
            "factor_ledger":factor_ledger,"provenance":provenance(factors),"data_quality":dq,"versioning":versioning(self.model_version),
        }

    def _qb_for_team(self, players, team):
        q=[p for p in (players.values() if isinstance(players,dict) else []) if isinstance(p,dict) and normalize_team(p.get("team"))==normalize_team(team) and str(p.get("position") or "").upper()=="QB"]
        q.sort(key=lambda p:(0 if str(p.get("depth_chart_position") or "").upper() in {"1","QB1"} else 1, 0 if str(p.get("status") or "").lower()=="active" else 1))
        return q[0] if q else None

    def _context(self, league_id, username, season, week):
        user=self.sleeper.get_user(username); rosters=self.sleeper.get_rosters(league_id); matchups=self.sleeper.get_matchups(league_id,week); players=self.sleeper.get_players()
        if not user: raise ValueError("Sleeper user not found.")
        target=next((r for r in rosters if r.get("owner_id")==user.get("user_id")),None)
        if not target: raise ValueError("User roster not found.")
        tm=next((m for m in matchups if m.get("roster_id")==target.get("roster_id")),None)
        if not tm: raise ValueError("No matchup found.")
        mid=tm.get("matchup_id"); oppm=next((m for m in matchups if m.get("matchup_id")==mid and m.get("roster_id")!=target.get("roster_id")),None)
        opp=next((r for r in rosters if r.get("roster_id")==oppm.get("roster_id")),None) if oppm else None
        return user,target,tm,oppm,opp,players

    def _resolve_player(self, players, pid):
        p=dict(players.get(str(pid),{}) if isinstance(players,dict) and isinstance(players.get(str(pid),{}),dict) else {})
        p["player_id"]=pid
        if not p.get("position") and normalize_team(pid) in DEF_TEAMS:
            p["position"]="DEF"
        # Team defenses are represented by team IDs in several fantasy feeds.
        # Give them a stable display identity instead of leaking an empty/Unknown name.
        if str(p.get("position") or "").upper() in {"DEF","DST"}:
            team = normalize_team(p.get("team") or p.get("nfl_team") or pid)
            p["team"] = team
            if not (p.get("full_name") or p.get("name")):
                p["full_name"] = f"{team} D/ST"
                p["name"] = p["full_name"]
        return p

    def predict_espn_team(self, espn, league_id, team_id, season, week):
        ctx=espn.normalized(league_id,team_id,week); players=ctx["players"]; starters=ctx["starters"]; roster=ctx.get("roster") or starters; settings=ctx.get("scoring_settings") or {}; all_results=[]
        starter_set={str(x) for x in starters}; roster_slots=ctx.get("roster_slots") or {}
        for pid in roster:
            p=self._resolve_player(players,pid); team=normalize_team(p.get("team") or p.get("nfl_team") or pid); game=self.nfl.team_game(season,week,team)
            is_starter=str(pid) in starter_set; slot_id=roster_slots.get(str(pid))
            if not game:
                row={"player_id":pid,"name":p.get("full_name") or p.get("name"),"position":p.get("position"),"eligible_positions":list(p.get("fantasy_positions") or ([p.get("position")] if p.get("position") else [])),"team":team,"error":"NFL game not found","projection":{"median_fantasy_points":0,"low":0,"high":0},"data_quality":{"status":"unavailable"}}
            else:
                opponent=normalize_team(game.get("away_team")) if normalize_team(game.get("home_team"))==team else normalize_team(game.get("home_team"))
                row=self._project_player(p,players,game,opponent,season,week,settings,starters)
            row["lineup_status"]="starter" if is_starter else ("ir" if slot_id==21 else "bench")
            row["espn_lineup_slot_id"]=slot_id
            all_results.append(row)
        results=[x for x in all_results if x.get("lineup_status")=="starter"]
        bench=[x for x in all_results if x.get("lineup_status")=="bench"]
        ir=[x for x in all_results if x.get("lineup_status")=="ir"]
        total=sum(x.get("projection",{}).get("median_fantasy_points",0) for x in results); gate=self._model_gate(results)
        lineup_slots=(ctx.get("lineup_settings") or {}).get("starter_slots") or []
        return {"platform":"espn","schedule_source":"nflverse","architecture_version":self.model_version,"season":season,"week":week,"league_id":league_id,"matchup_id":ctx.get("matchup_id"),"data_cutoff":cutoff(season,week),"scoring_settings":settings,"team":{"roster_id":ctx.get("team_id"),"owner_id":ctx.get("owner_id"),"username":str(team_id),"display_name":ctx.get("display_name"),"median_projected_fantasy_points":total,"starters":results,"bench":bench,"ir":ir,"roster":all_results,"lineup_slots":lineup_slots,"lineup_settings":ctx.get("lineup_settings") or {}},"opponent":{"roster_id":ctx.get("opponent_team_id"),"starters":[]},"integration":{"unresolved_roster_players":ctx.get("unresolved",[])},"model_gate":gate,"versioning":versioning(self.model_version)}

    def predict_team(self, league_id, username, season, week):
        user,target,tm,oppm,opp,players=self._context(league_id,username,season,week)
        settings=self.sleeper.get_scoring_settings(league_id) or {}
        league=self.sleeper.get_league(league_id) or {}
        starters=tm.get("starters") or []
        starter_set={str(x) for x in starters}
        roster=list(target.get("players") or starters)
        reserve_set={str(x) for x in (target.get("reserve") or [])}
        raw_positions=list(league.get("roster_positions") or [])
        starter_slot_by_id=sleeper_starter_slot_map(starters,raw_positions)
        all_results=[]
        for pid in roster:
            p=self._resolve_player(players,pid); team=normalize_team(p.get("team") or p.get("nfl_team") or pid); game=self.nfl.team_game(season,week,team)
            if not game:
                row={"player_id":pid,"name":p.get("full_name") or p.get("name"),"position":p.get("position"),"eligible_positions":list(p.get("fantasy_positions") or ([p.get("position")] if p.get("position") else [])),"team":team,"error":"NFL game not found","projection":{"median_fantasy_points":0,"low":0,"high":0},"data_quality":{"status":"unavailable"}}
            else:
                opponent=normalize_team(game.get("away_team")) if normalize_team(game.get("home_team"))==team else normalize_team(game.get("home_team"))
                row=self._project_player(p,players,game,opponent,season,week,settings,starters)
            spid=str(pid)
            row["lineup_status"]="starter" if spid in starter_set else ("ir" if spid in reserve_set else "bench")
            if row["lineup_status"] == "starter":
                row.update(starter_slot_by_id.get(spid, {}))
            all_results.append(row)
        results=[x for x in all_results if x.get("lineup_status")=="starter"]
        bench=[x for x in all_results if x.get("lineup_status")=="bench"]
        ir=[x for x in all_results if x.get("lineup_status")=="ir"]
        raw_positions=list(league.get("roster_positions") or [])
        lineup_slots=[str(x).upper() for x in raw_positions if str(x).upper() not in {"BN","BENCH","IR","RESERVE","TAXI"}]
        total=sum(x.get("projection",{}).get("median_fantasy_points",0) for x in results)
        gate=self._model_gate(results)
        return {"platform":"sleeper","schedule_source":"nflverse","architecture_version":self.model_version,"season":season,"week":week,"league_id":league_id,"matchup_id":tm.get("matchup_id"),"data_cutoff":cutoff(season,week),"scoring_settings":settings,"team":{"roster_id":target.get("roster_id"),"owner_id":target.get("owner_id"),"username":user.get("username"),"display_name":user.get("display_name"),"median_projected_fantasy_points":total,"starters":results,"bench":bench,"ir":ir,"roster":[x for x in all_results if x.get("lineup_status") != "ir"],"lineup_slots":lineup_slots,"lineup_settings":{"roster_positions":raw_positions}},"opponent":{"roster_id":opp.get("roster_id") if opp else None,"starters":oppm.get("starters",[]) if oppm else []},"model_gate":gate,"versioning":versioning(self.model_version)}

    def project_candidate(self, player, players, season, week, settings, starters=()):
        """Project one waiver/free-agent candidate through the same FME path as roster players."""
        pid=player.get("player_id") or player.get("player_id_sleeper") or player.get("sleeper_id")
        p=dict(player); p["player_id"]=pid
        team=normalize_team(p.get("team") or p.get("nfl_team") or pid)
        game=self.nfl.team_game(season,week,team)
        if not game:
            return None
        opponent=normalize_team(game.get("away_team")) if normalize_team(game.get("home_team"))==team else normalize_team(game.get("home_team"))
        row=self._project_player(p,players,game,opponent,season,week,settings,list(starters or []))
        if str(row.get("position") or p.get("position") or "").upper() in {"DEF", "DST"} and str(row.get("name") or "").strip().lower() in {"", "unknown", "none"}:
            row["name"] = f"{team} D/ST"
        row["lineup_status"]="waiver"
        row["waiver_role_intel"] = p.get("waiver_role_intel") or {}
        return row

    def _model_gate(self, results):
        missing=[p for p in results if p.get("data_quality",{}).get("status")=="unavailable"]
        pending=[p for p in results if not p.get("data_quality",{}).get("history_complete", True)]
        usable=[p for p in results if p.get("data_quality",{}).get("projection_status")=="usable"]
        active_fail=[]; ownership_fail=[]
        for p in results:
            for x in p.get("layer_audit",[]):
                if x.get("present") and x.get("status")=="missing":
                    active_fail.append({"player_id":p.get("player_id"),"layer":x.get("layer")})
            ledger=p.get("factor_ledger",{})
            if ledger.get("double_counting_detected"):
                ownership_fail.append({"player_id":p.get("player_id"),"duplicates":ledger.get("duplicate_predictive_owners")})
        return {"architecture_layers":len(PREDICTIVE_LAYERS),"functional":not active_fail and not ownership_fail,"starter_count":len(results),"usable_projection_count":len(usable),"missing_projection_count":len(missing),"data_pending_count":len(pending),"data_complete":not missing and not pending,"layer_propagation_failures":active_fail,"factor_ownership_failures":ownership_fail,"audit_ready":not missing and not pending and len(usable)==len(results) and not active_fail and not ownership_fail and all(p.get("confidence",0)>=.55 for p in results)}

    def validate_team(self, league_id, username, season, week):
        out=self.predict_team(league_id,username,season,week); checks=[]
        for p in out["team"]["starters"]:
            checks.append({"player_id":p.get("player_id"),"name":p.get("name"),"position":p.get("position"),"historical_games":p.get("historical_games",0),"has_projection":bool(p.get("projection")),"median":p.get("projection",{}).get("median_fantasy_points",0),"confidence":p.get("confidence",0),"qb_linked":p.get("data_quality",{}).get("qb_linked",False),"identity":p.get("identity"),"data_quality":p.get("data_quality"),"layer_audit":p.get("layer_audit",[]),"factor_ledger":p.get("factor_ledger",{})})
        failures=[]; warnings=[]
        for x in checks:
            if not x["has_projection"]: failures.append({"player_id":x["player_id"],"reason":"no_projection"})
            if x["confidence"]<.55: warnings.append({"player_id":x["player_id"],"reason":"low_confidence","confidence":x["confidence"]})
            if x.get("position")!="DEF" and not x.get("identity",{}).get("resolved_id"): warnings.append({"player_id":x["player_id"],"reason":"identity_unresolved"})
            if x.get("factor_ledger",{}).get("double_counting_detected"): failures.append({"player_id":x["player_id"],"reason":"factor_ownership_collision"})
        return {"architecture_version":self.model_version,"validation":"complete","checks":checks,"failures":failures,"warnings":warnings,"coverage":{"players":len(checks),"with_history":sum(x["historical_games"]>0 for x in checks),"with_identity":sum(bool(x.get("identity",{}).get("resolved_id")) for x in checks),"with_qb_link":sum(x["qb_linked"] for x in checks),"usable_confidence":sum(x["confidence"]>=.55 for x in checks)},"audit_ready":out["model_gate"]["audit_ready"],"model_gate":out["model_gate"]}

    def start_sit(self, league_id, username, season, week):
        out=self.predict_team(league_id,username,season,week)
        return {"architecture_version":self.model_version,"ranked_starters":sorted(out["team"]["starters"],key=lambda x:x.get("projection",{}).get("median_fantasy_points",0),reverse=True),"optimization":{"objective":"maximize_median_fantasy_points","eligible_count":len(out["team"]["starters"])}}


def scheme_offense_factor(pos, offense):
    """Offensive scheme owns distribution, not defensive efficiency."""
    pr=offense.get("pass_rate",.58)
    if pos in {"WR","TE","QB"}:
        return clamp(1+(pr-.58)*.22,.94,1.06)
    if pos=="RB":
        return clamp(1+((1-pr)-.42)*.16,.95,1.05)
    return 1.0


def scheme_defense_factor(pos, defense):
    """Defensive scheme owns matchup efficiency/pressure, not offensive distribution."""
    pressure=defense.get("pressure_factor",1.0)
    if pos=="QB": return clamp(1-(pressure-1)*.16,.90,1.10)
    if pos in {"WR","TE"}: return clamp(1-(pressure-1)*.06,.94,1.06)
    if pos=="RB": return clamp(1-(pressure-1)*.04,.96,1.04)
    return 1.0
