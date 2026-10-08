from pathlib import Path
import threading, time, uuid

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.integrations.sleeper import SleeperClient, SleeperAPIError
from backend.integrations.espn import ESPNClient, ESPNAPIError
from backend.integrations.nflverse import NFLVerseClient, NFLVerseAPIError
from backend.engine.predictor import PredictionEngine
from backend.engine.audit import audit_predictions
from backend.engine.calibration import (
    evaluate as evaluate_calibration,
    walk_forward,
    summarize,
    fit_affine_profile,
    apply_affine_profile,
)
from backend.engine.optimizer import optimize_lineup
from backend.engine.waivers import recommend_waiver_moves

MODEL_VERSION = "1.9.18-espn-defense-starter-waivers"

LAYERS = [
    "injury_availability", "depth_chart_replacement", "offensive_line", "defensive_front",
    "ol_vs_dl", "game_script", "play_volume", "opportunity_distribution", "route_alignment",
    "coverage_assignment", "weather", "surface_stadium", "referee", "coaching", "red_zone",
    "explosive_plays", "qb_correlation", "position_matchup", "offensive_scheme", "defensive_scheme",
    "defensive_fantasy", "monte_carlo", "league_scoring", "calibration", "data_cutoff",
    "feature_provenance", "model_versioning", "player_identity_crosswalk", "position_projection_models",
    "lineup_optimization", "static_model_audit", "confidence_uncertainty",
]

_WAIVER_JOBS = {}
_WAIVER_LOCK = threading.Lock()

def _job_update(job_id, **kw):
    if not job_id: return
    with _WAIVER_LOCK:
        if job_id in _WAIVER_JOBS: _WAIVER_JOBS[job_id].update(kw)

def _job_cancelled(job_id):
    with _WAIVER_LOCK: return bool(job_id and _WAIVER_JOBS.get(job_id,{}).get("cancel_requested"))

def _role_intel(player, universe):
    pos=str(player.get("position") or "").upper(); team=str(player.get("team") or "").upper()
    if pos not in {"RB","WR","TE"} or not team: return {"injury_status":player.get("injury_status") or player.get("status") or "Unknown","role_change":"No injury-driven promotion detected","opportunity_multiplier":1.0,"teammate_injuries":[],"depth_chart_promotion":False,"rest_of_season_value":"Baseline"}
    def depth(x):
        for k in ("depth_chart_order","depth_chart_position"):
            try: return int(x.get(k))
            except (TypeError,ValueError): pass
        return 99
    d=depth(player); hurt=[]
    for q in universe.values():
        if not isinstance(q,dict) or str(q.get("team") or "").upper()!=team: continue
        qp=str(q.get("position") or "").upper()
        same = qp==pos or (pos in {"WR","TE"} and qp in {"WR","TE"})
        if not same: continue
        st=str(q.get("injury_status") or q.get("status") or "").lower()
        if st not in {"out","ir","injured_reserve","doubtful"}: continue
        qd=depth(q)
        if qd < d or (d==99 and qd<99): hurt.append({"name":q.get("full_name") or q.get("name") or "Unknown","position":qp,"status":st,"depth":qd})
    n=len(hurt); mult=1.0
    if n:
        if pos=="RB": mult=min(1.45,1.18+.09*(n-1))
        elif pos=="WR": mult=min(1.28,1.10+.05*(n-1))
        else: mult=min(1.22,1.08+.04*(n-1))
    return {"injury_status":player.get("injury_status") or player.get("status") or "Active","role_change":("Expected increased role from unavailable teammate(s)" if n else "No injury-driven promotion detected"),"opportunity_multiplier":round(mult,3),"teammate_injuries":hurt,"depth_chart_promotion":bool(n),"rest_of_season_value":("High while role persists" if mult>=1.18 else "Medium while role persists" if mult>1 else "Baseline") }

app = FastAPI(
    title="Fantasy Matchup Engine",
    version=MODEL_VERSION,
    description="Full fantasy football projection, matchup, simulation, optimization and audit engine.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path.cwd()
DASHBOARD_INDEX = BASE_DIR / "fantasy-matchup-dashboard" / "index.html"


@app.get("/", include_in_schema=False)
def dashboard():
    if not DASHBOARD_INDEX.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Dashboard file not found: {DASHBOARD_INDEX}",
        )
    return FileResponse(DASHBOARD_INDEX)


@app.get("/health")
def health():
    return {"status": "ok", "version": MODEL_VERSION}


@app.get("/api/v1/status")
def status():
    return {
        "app": "fantasy-matchup-engine",
        "version": MODEL_VERSION,
        "architecture": "full_model",
        "model_status": "data_driven_end_to_end",
        "layers": len(LAYERS),
        "layer_names": LAYERS,
        "position_models": ["QB", "RB", "WR", "TE", "K", "DEF"],
        "integrations": ["sleeper", "espn", "nflverse"],
        "audit_ready": False,
        "audit_gate": "Prediction-specific audit readiness is determined from live data propagation; architecture status is separate.",
    }


@app.get("/api/v1/architecture")
def architecture():
    wired_layers = {
        "injury_availability", "depth_chart_replacement", "offensive_line",
        "defensive_front", "ol_vs_dl", "game_script", "opportunity_distribution",
        "route_alignment", "coverage_assignment", "weather", "surface_stadium",
        "red_zone", "explosive_plays", "qb_correlation", "position_matchup",
        "offensive_scheme", "defensive_scheme", "defensive_fantasy",
        "monte_carlo", "league_scoring", "data_cutoff", "feature_provenance",
        "model_versioning", "player_identity_crosswalk", "position_projection_models",
    }

    return {
        "version": MODEL_VERSION,
        "layers": [
            {
                "id": i + 1,
                "name": name,
                "implemented": True,
                "wired_to_prediction": name in wired_layers,
            }
            for i, name in enumerate(LAYERS)
        ],
        "engines": [
            "identity", "historical_data", "opportunity", "matchup",
            "scheme", "defense", "projection", "scoring", "simulation",
            "optimization", "calibration", "audit",
        ],
        "stage1_rules": {
            "single_owner_factors": True,
            "double_counting_guard": True,
            "proxy_transparency": True,
            "replacement_affects_uncertainty_only": True,
            "referee_predictive": False,
            "coaching_predictive": False,
        },
        "legacy_unwired_engines": [
            "backend.engines.model_pipeline.ModelPipeline",
            "backend.engines.offense_engine.OffenseEngine",
            "backend.engines.defense_engine.DefenseEngine",
            "backend.engines.position_engines.*",
        ],
    }


def _engine():
    return PredictionEngine(
        SleeperClient(),
        NFLVerseClient(),
        model_version=MODEL_VERSION,
    )


@app.get("/api/v1/model/gate")
def model_gate():
    return {
        "architecture_version": MODEL_VERSION,
        "layer_count": len(LAYERS),
        "layers": LAYERS,
        "functional_complete": True,
        "requires_data_propagation": True,
        "note": "Functional completeness describes the primary PredictionEngine path; legacy architecture contracts are not counted as wired predictive engines.",
    }


@app.get("/api/v1/fantasy/espn/league/{league_id}/team/{team_id}/week/{week}/prediction")
def espn_fantasy_prediction(league_id: str, team_id: int, week: int, season: int = Query(2026)):
    if not 1 <= week <= 18: raise HTTPException(400, "NFL week must be between 1 and 18.")
    try:
        espn=ESPNClient(season=season)
        return _engine().predict_espn_team(espn,league_id,team_id,season,week)
    except (ESPNAPIError, SleeperAPIError, NFLVerseAPIError) as exc:
        raise HTTPException(502,str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500,f"{type(exc).__name__}: {exc}") from exc

@app.get("/api/v1/fantasy/league/{league_id}/team/{username}/week/{week}/prediction")
def fantasy_prediction(
    league_id: str,
    username: str,
    week: int,
    season: int = Query(2026),
):
    if not 1 <= week <= 18:
        raise HTTPException(400, "NFL week must be between 1 and 18.")

    try:
        return _engine().predict_team(
            league_id, username, season, week
        )
    except (SleeperAPIError, NFLVerseAPIError) as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/v1/fantasy/league/{league_id}/team/{username}/week/{week}/validation")
def fantasy_validation(
    league_id: str,
    username: str,
    week: int,
    season: int = Query(2026),
):
    try:
        return _engine().validate_team(
            league_id, username, season, week
        )
    except (SleeperAPIError, NFLVerseAPIError) as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/v1/fantasy/league/{league_id}/team/{username}/week/{week}/start-sit")
def fantasy_start_sit(
    league_id: str,
    username: str,
    week: int,
    season: int = Query(2026),
):
    try:
        return _engine().start_sit(
            league_id, username, season, week
        )
    except (SleeperAPIError, NFLVerseAPIError) as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/v1/fantasy/league/{league_id}/team/{username}/week/{week}/audit")
def fantasy_audit(
    league_id: str,
    username: str,
    week: int,
    season: int = Query(2026),
):
    try:
        prediction = _engine().predict_team(
            league_id, username, season, week
        )
        return {
            "architecture_version": MODEL_VERSION,
            "prediction_gate": prediction["model_gate"],
            "audit": audit_predictions(prediction),
        }
    except (SleeperAPIError, NFLVerseAPIError) as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"{type(exc).__name__}: {exc}") from exc


@app.get("/api/v1/calibration/readiness")
def calibration_readiness():
    return {
        "architecture_version": MODEL_VERSION,
        "stage1_complete": True,
        "walk_forward_required": True,
        "future_data_allowed": False,
        "required_observations": [
            "predicted_stats",
            "actual_stats",
            "predicted_fantasy_points",
            "actual_fantasy_points",
            "confidence",
            "position",
            "team",
            "opponent",
            "season",
            "week",
            "layer_impacts",
        ],
        "required_metrics": [
            "MAE",
            "RMSE",
            "bias",
            "median_error",
            "TD_probability_calibration",
            "interval_coverage",
            "confidence_calibration",
        ],
        "segmentation": [
            "QB", "RB", "WR", "TE", "K", "DEF",
            "history_depth", "injury_status", "game_total",
            "spread", "confidence_bucket",
        ],
        "layer_attribution_ready": True,
    }


@app.post("/api/v1/calibration/walk-forward")
def calibration_walk_forward(payload: dict):
    payload = payload or {}

    season = int(payload.get("season", 2026))
    start_week = int(payload.get("start_week", 2))
    end_week = payload.get("end_week")
    settings = payload.get("scoring_settings") or {}

    obs = walk_forward(
        NFLVerseClient(),
        season,
        start_week,
        int(end_week) if end_week is not None else None,
        settings=settings,
        max_players=payload.get("max_players"),
    )

    return {
        "architecture_version": MODEL_VERSION,
        "season": season,
        "start_week": start_week,
        "end_week": end_week,
        "observations": obs,
        "summary": summarize(obs),
        "leakage_policy": {
            "historical_cutoff": "target_week_excluded",
            "schedule_total": "pregame_total_line_only",
            "actuals_used_only_for_evaluation": True,
        },
    }


@app.post("/api/v1/calibration/full")
def calibration_full(payload: dict):
    payload = payload or {}

    seasons = payload.get("seasons") or [2026]
    all_obs = []
    reports = []

    validation_week = int(
        payload.get(
            "validation_week",
            payload.get("end_week", 4),
        )
    )

    for season in seasons:
        obs = walk_forward(
            NFLVerseClient(),
            int(season),
            int(payload.get("start_week", 2)),
            (
                int(payload["end_week"])
                if payload.get("end_week") is not None
                else None
            ),
            settings=payload.get("scoring_settings") or {},
            max_players=payload.get("max_players"),
        )

        train = [
            x for x in obs
            if int(x["week"]) < validation_week
        ]

        holdout = [
            x for x in obs
            if int(x["week"]) == validation_week
        ]

        profile = (
            fit_affine_profile(obs, validation_week - 1)
            if train
            else {"status": "not_available"}
        )

        calibrated = (
            apply_affine_profile(holdout, profile)
            if holdout and profile.get("global")
            else []
        )

        reports.append({
            "season": int(season),
            "sample_size": len(obs),
            "training_sample_size": len(train),
            "holdout_sample_size": len(holdout),
            "summary": summarize(obs),
            "holdout_uncalibrated": summarize(holdout),
            "holdout_calibrated": (
                summarize(calibrated)
                if calibrated
                else {"sample_size": 0}
            ),
            "calibration_profile": profile,
        })

        all_obs.extend(obs)

    return {
        "architecture_version": MODEL_VERSION,
        "stage": "2-full-calibration",
        "validation_week": validation_week,
        "seasons": reports,
        "pooled": {
            "sample_size": len(all_obs),
            "summary": summarize(all_obs),
        },
        "data_availability": {
            "requested_seasons": len(seasons),
            "seasons_with_observations": sum(
                1 for r in reports
                if r["sample_size"] > 0
            ),
        },
        "leakage_policy": {
            "historical_cutoff": "target_week_excluded",
            "schedule_total": "pregame_total_line_only",
            "actuals_used_only_for_evaluation": True,
            "calibration_training_excludes_holdout_week": True,
        },
    }


@app.post("/api/v1/calibration/evaluate")
def calibration_evaluate(payload: dict):
    """Accepts [{predicted, actual}, ...] and returns MAE/bias/RMSE."""
    rows = (
        payload.get("predictions", [])
        if isinstance(payload, dict)
        else []
    )

    return {
        "architecture_version": MODEL_VERSION,
        **evaluate_calibration(rows),
    }


@app.post("/api/v1/lineup/optimize")
def lineup_optimize(payload: dict):
    players = (
        payload.get("players", [])
        if isinstance(payload, dict)
        else []
    )

    slots = (
        payload.get("slots", [])
        if isinstance(payload, dict)
        else []
    )

    return {
        "architecture_version": MODEL_VERSION,
        "optimization": optimize_lineup(players, slots),
    }


@app.post("/api/v1/waivers/start/{platform}/league/{league_id}/team/{team_ref}/week/{week}")
def start_waiver_job(platform: str, league_id: str, team_ref: str, week: int, season: int = Query(2026)):
    jid=uuid.uuid4().hex
    with _WAIVER_LOCK: _WAIVER_JOBS[jid]={"job_id":jid,"status":"queued","stage":"Queued","percent":0,"processed":0,"total":0,"started_at":time.time(),"cancel_requested":False}
    def run():
        try:
            result=waiver_recommendations(platform,league_id,team_ref,week,season,jid)
            with _WAIVER_LOCK: _WAIVER_JOBS[jid].update(status="complete",stage="Complete",percent=100,result=result,finished_at=time.time())
        except Exception as exc:
            with _WAIVER_LOCK:
                cancelled=_WAIVER_JOBS.get(jid,{}).get("cancel_requested")
                _WAIVER_JOBS[jid].update(status="cancelled" if cancelled else "error",stage="Cancelled" if cancelled else "Failed",error=str(getattr(exc,"detail",exc)),finished_at=time.time())
    threading.Thread(target=run,daemon=True).start()
    return {"job_id":jid}

@app.get("/api/v1/waivers/status/{job_id}")
def waiver_job_status(job_id: str):
    with _WAIVER_LOCK:
        j=dict(_WAIVER_JOBS.get(job_id) or {})
    if not j: raise HTTPException(404,"Waiver job not found")
    j["elapsed_seconds"]=round(time.time()-j.get("started_at",time.time()),1)
    if j.get("processed") and j.get("total") and j["processed"]>0 and j["status"]=="running":
        elapsed=max(.1,j["elapsed_seconds"]); j["eta_seconds"]=round(elapsed*(j["total"]-j["processed"])/j["processed"],1)
    return j

@app.post("/api/v1/waivers/cancel/{job_id}")
def cancel_waiver_job(job_id: str):
    with _WAIVER_LOCK:
        if job_id not in _WAIVER_JOBS: raise HTTPException(404,"Waiver job not found")
        _WAIVER_JOBS[job_id]["cancel_requested"]=True
    return {"job_id":job_id,"cancel_requested":True}

@app.get("/api/v1/waivers/{platform}/league/{league_id}/team/{team_ref}/week/{week}")
def waiver_recommendations(platform: str, league_id: str, team_ref: str, week: int, season: int = Query(2026), job_id: str = None):
    if platform not in {"sleeper","espn"}: raise HTTPException(400,"platform must be sleeper or espn")
    if not 1 <= week <= 18: raise HTTPException(400,"NFL week must be between 1 and 18.")
    try:
        _job_update(job_id,status="running",stage="Loading waiver pool",percent=3,started_at=_WAIVER_JOBS.get(job_id,{}).get("started_at",time.time()) if job_id else time.time())
        engine=_engine(); sleeper=engine.sleeper; universe=sleeper.get_players()
        if platform=="espn":
            espn=ESPNClient(season=season); team_id=int(team_ref)
            prediction=engine.predict_espn_team(espn,league_id,team_id,season,week)
            settings=prediction.get("scoring_settings") or {}; starters=[x.get("player_id") for x in prediction["team"]["starters"]]
            wanted=set(espn.available_player_ids(league_id,week,1000))
            # Stable ESPN-ID -> Sleeper player mapping. This is the same canonical universe used by FME.
            ids=[]; mapped_espn=set(); gsis_to_sid={}
            for sid,p in universe.items():
                if not isinstance(p,dict): continue
                gs=p.get("gsis_id") or p.get("gsis")
                if gs: gsis_to_sid[str(gs)]=str(sid)
                eid=p.get("espn_id") or p.get("espn")
                if eid is not None and str(eid) in wanted:
                    ids.append(str(sid)); mapped_espn.add(str(eid))
            # Same universal bridge used by ESPN roster identity: ESPN -> nflverse GSIS -> Sleeper.
            for eid,gs in espn._nflverse_identity_index().items():
                if eid in wanted and eid not in mapped_espn and str(gs) in gsis_to_sid:
                    ids.append(gsis_to_sid[str(gs)])
        else:
            prediction=engine.predict_team(league_id,team_ref,season,week)
            settings=prediction.get("scoring_settings") or {}; starters=[x.get("player_id") for x in prediction["team"]["starters"]]
            rostered=set()
            for r in sleeper.get_rosters(league_id): rostered.update(str(x) for x in (r.get("players") or []))
            ids=[str(sid) for sid,p in universe.items() if str(sid) not in rostered and isinstance(p,dict)]
        # Keep only active NFL fantasy positions with a current team. ESPN is already ownership-ranked;
        # Sleeper candidates are reduced to active rosterable players before FME projection.
        eligible=[]
        for sid in ids:
            p=universe.get(str(sid)) or {}
            pos=str(p.get("position") or "").upper()
            if pos not in {"QB","RB","WR","TE","K","DEF","DST"}: continue
            if not (p.get("team") or (pos in {"DEF","DST"} and str(sid).upper() in {"ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL","DEN","DET","GB","HOU","IND","JAX","KC","LV","LAC","LA","MIA","MIN","NE","NO","NYG","NYJ","PHI","PIT","SF","SEA","TB","TEN","WAS"})): continue
            status=str(p.get("status") or "Active").lower()
            if status in {"retired","inactive"}: continue
            q=dict(p); q["player_id"]=sid; eligible.append(q)
        eligible=eligible[:1000] if platform=="espn" else eligible
        _job_update(job_id,stage="Projecting viable players",processed=0,total=len(eligible),percent=12)
        projected=[]
        for i,p in enumerate(eligible,1):
            if _job_cancelled(job_id): raise RuntimeError("Waiver search cancelled")
            intel=_role_intel(p,universe); p=dict(p); p["waiver_role_intel"]=intel; p["role_opportunity_multiplier"]=intel["opportunity_multiplier"]
            row=engine.project_candidate(p,universe,season,week,settings,starters)
            if i==1 or i%5==0 or i==len(eligible): _job_update(job_id,processed=i,total=len(eligible),percent=12+int(58*i/max(1,len(eligible))))
            if row and (row.get("data_quality") or {}).get("history_complete",True): projected.append(row)
        projected.sort(key=lambda x: float((x.get("projection") or {}).get("median_fantasy_points") or 0), reverse=True)
        # Exact swap evaluation is expensive; the highest current-week projections contain the actionable pool.
        candidates=projected[:80]
        roster=prediction["team"].get("roster") or []
        # Use the actual NFL schedule: absence of a team game identifies a bye.
        # Do not infer a bye from a zero projection or an injury status.
        games=engine.nfl.week_games(season,week)
        from backend.engine.features import normalize_team
        playing={normalize_team(g.get(k)) for g in games for k in ('home_team','away_team')}
        for p in roster:
            team=normalize_team(p.get('team'))
            p['on_bye']=bool(team and team not in playing)
        slots=prediction["team"].get("lineup_slots") or []
        def swap_progress(done,total,move_idx): _job_update(job_id,stage="Evaluating waiver candidates",processed=done,total=total,percent=72+int(24*done/max(1,total)))
        advice=recommend_waiver_moves(roster,candidates,slots,max_moves=12,min_gain=.01,progress=swap_progress,cancelled=lambda:_job_cancelled(job_id))
        advice["platform"]=platform; advice["week"]=week; advice["available_projected_count"]=len(projected)
        advice["top_available"]=[{"player_id":x.get("player_id"),"name":x.get("name"),"position":x.get("position"),"team":x.get("team"),"median_fantasy_points":round(float((x.get("projection") or {}).get("median_fantasy_points") or 0),2)} for x in candidates[:20]]
        _job_update(job_id,stage="Complete",percent=100,processed=len(projected),total=len(projected))
        return {"architecture_version":MODEL_VERSION,"waiver_advisor":advice}
    except (ESPNAPIError,SleeperAPIError,NFLVerseAPIError) as exc: raise HTTPException(502,str(exc)) from exc
    except Exception as exc: raise HTTPException(500,f"{type(exc).__name__}: {exc}") from exc
