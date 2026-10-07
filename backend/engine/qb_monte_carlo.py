"""Stat-level Monte Carlo for corrected QB projections.

Uses only pre-target-week history supplied by PredictionEngine.  The projection
center remains authoritative; history controls uncertainty.  NumPy is used so
1,000,000 draws remain practical.
"""
from __future__ import annotations

import math
import numpy as np


def _f(row, *keys):
    for key in keys:
        value = row.get(key) if isinstance(row, dict) else None
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return 0.0


def _sd(history, keys, floor):
    vals = np.asarray([_f(r, *keys) for r in history], dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size >= 2:
        return max(float(vals.std(ddof=1)), floor)
    return floor


def _score_coeff(settings, key, default):
    try:
        return float((settings or {}).get(key, default))
    except (TypeError, ValueError):
        return default


def _summary(a):
    q = np.quantile(a, [.01,.05,.10,.25,.50,.75,.90,.95,.99])
    return {
        "mean": float(a.mean()), "stdev": float(a.std()),
        "p01": float(q[0]), "p05": float(q[1]), "p10": float(q[2]),
        "p25": float(q[3]), "p50": float(q[4]), "p75": float(q[5]),
        "p90": float(q[6]), "p95": float(q[7]), "p99": float(q[8]),
    }


def simulate_qb_stats(projected, history, settings=None, n=1_000_000, seed=13):
    n = max(1_000, int(n))
    rng = np.random.default_rng(seed)

    pa_mu = max(float(projected.get("pass_attempts", 0)), 1.0)
    comp_rate = min(.80, max(.45, float(projected.get("completions",0))/pa_mu))
    ypa = max(3.0, float(projected.get("passing_yards",0))/pa_mu)
    td_rate = max(0.0, float(projected.get("passing_tds",0))/pa_mu)
    int_rate = max(0.0, float(projected.get("interceptions",0))/pa_mu)

    # Attempt volatility comes from chronology-safe historical starts.  Efficiency
    # volatility is estimated from historical YPA, with conservative floors for
    # small samples so two-game histories cannot become falsely certain.
    att_sd = _sd(history, ("attempts","passing_attempts","pass_attempts"), 4.5)
    hist_ypa = []
    for r in history:
        a = _f(r,"attempts","passing_attempts","pass_attempts")
        if a > 0:
            hist_ypa.append(_f(r,"passing_yards","pass_yards")/a)
    ypa_sd = max(float(np.std(hist_ypa, ddof=1)) if len(hist_ypa)>=2 else 0.0, 1.15)

    attempts = np.rint(np.clip(rng.normal(pa_mu, att_sd, n), 10, 60)).astype(np.int16)
    completions = rng.binomial(attempts, comp_rate).astype(np.int16)
    sim_ypa = np.clip(rng.normal(ypa, ypa_sd, n), 2.5, 13.0)
    pass_yards = np.maximum(0.0, attempts * sim_ypa)
    pass_tds = rng.poisson(attempts * td_rate).astype(np.int16)
    interceptions = rng.poisson(attempts * int_rate).astype(np.int16)

    rush_mu = float(projected.get("rushing_yards",0))
    rush_sd = _sd(history, ("rushing_yards","rush_yards"), max(4.0, abs(rush_mu)*.45))
    rushing_yards = rng.normal(rush_mu, rush_sd, n)
    rush_td_mu = max(0.0, float(projected.get("rushing_tds",0)))
    rushing_tds = rng.poisson(rush_td_mu, n).astype(np.int16)

    fp = (pass_yards * _score_coeff(settings,"pass_yd",.04)
          + pass_tds * _score_coeff(settings,"pass_td",4)
          + interceptions * _score_coeff(settings,"pass_int",-2)
          + rushing_yards * _score_coeff(settings,"rush_yd",.1)
          + rushing_tds * _score_coeff(settings,"rush_td",6))

    out = {
        "n": n, "seed": seed, "method": "stat_level_numpy",
        "pass_attempts": _summary(attempts),
        "completions": _summary(completions),
        "passing_yards": _summary(pass_yards),
        "passing_tds": _summary(pass_tds),
        "interceptions": _summary(interceptions),
        "rushing_yards": _summary(rushing_yards),
        "rushing_tds": _summary(rushing_tds),
        "fantasy_points": _summary(fp),
        "thresholds": {
            "pass_200": float(np.mean(pass_yards >= 200)),
            "pass_225": float(np.mean(pass_yards >= 225)),
            "pass_250": float(np.mean(pass_yards >= 250)),
            "pass_275": float(np.mean(pass_yards >= 275)),
            "pass_300": float(np.mean(pass_yards >= 300)),
            "pass_325": float(np.mean(pass_yards >= 325)),
            "pass_350": float(np.mean(pass_yards >= 350)),
            "pass_td_1": float(np.mean(pass_tds >= 1)),
            "pass_td_2": float(np.mean(pass_tds >= 2)),
            "pass_td_3": float(np.mean(pass_tds >= 3)),
            "fp_10": float(np.mean(fp >= 10)), "fp_15": float(np.mean(fp >= 15)),
            "fp_20": float(np.mean(fp >= 20)), "fp_25": float(np.mean(fp >= 25)),
            "fp_30": float(np.mean(fp >= 30)), "fp_35": float(np.mean(fp >= 35)),
            "fp_40": float(np.mean(fp >= 40)),
        },
    }
    return out
