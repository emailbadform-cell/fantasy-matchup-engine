# Stage 2 — Full Walk-Forward Calibration Report

## Verdict

Stage 2 calibration infrastructure is complete and was executed against the currently bundled 2026 data. The run contains **906 player/game observations** across Weeks 2–4. Week 4 was held out from calibration fitting and used as the out-of-sample validation set.

## Data availability

- Available player/team weeks: 2026 Weeks 1–4
- Walk-forward prediction weeks: 2–4
- Training observations through Week 3: 849
- Holdout Week 4 observations: 57
- Positions evaluated: QB, RB, WR, TE, K, DEF
- Historical target-week data excluded from feature history
- Pregame game total uses `total_line`, never final `total`

## Holdout result

| Metric | Uncalibrated | Calibrated | Change |
|---|---:|---:|---:|
| MAE | 3.507 | 3.160 | -0.347 |
| RMSE | 3.997 | 3.610 | -0.388 |
| Bias | 1.048 | 0.863 | -0.185 |
| Median error | 2.202 | 2.445 | 0.243 |

Calibration reduced Week 4 fantasy-point MAE by **0.347 points (9.9%)** and RMSE by **0.388 points (9.7%)** on the held-out week.

## Full available-dataset performance

{
  "sample_size": 906,
  "mae": 4.457267243860801,
  "rmse": 6.392753323428578,
  "bias": -0.5583166282292411,
  "median_error": 0.8271923666904322
}

## Position evaluation

{
  "QB": {
    "sample_size": 77,
    "mae": 7.809657894595355,
    "rmse": 9.33950625723376,
    "bias": -2.392115249892769,
    "median_error": -2.0180573051117445
  },
  "RB": {
    "sample_size": 191,
    "mae": 4.294624802882936,
    "rmse": 5.88164762394455,
    "bias": 1.0161996077235933,
    "median_error": 1.50277758987899
  },
  "WR": {
    "sample_size": 317,
    "mae": 4.677932783648063,
    "rmse": 6.955210043991249,
    "bias": -1.2770999690647633,
    "median_error": 0.5807391397373554
  },
  "TE": {
    "sample_size": 159,
    "mae": 4.288813397215257,
    "rmse": 6.42005598693783,
    "bias": -1.2139499733715204,
    "median_error": -0.07721186417710557
  },
  "K": {
    "sample_size": 66,
    "mae": 3.0502174900672934,
    "rmse": 3.7610021974936867,
    "bias": -1.4470271405132624,
    "median_error": -1.3773839100947778
  },
  "DEF": {
    "sample_size": 96,
    "mae": 2.609653654013531,
    "rmse": 3.027594333240229,
    "bias": 1.8502751169200156,
    "median_error": 2.293423140689562
  }
}

## Counting-stat evaluation

Counting-stat MAE/RMSE/bias are retained in `CALIBRATION_REPORT_STAGE2.json` for QB, RB, WR, TE, K and DEF.

## TD calibration

The calibration runner converts predicted expected TD count into an any-touchdown probability using `1 - exp(-lambda)` and reports Brier score plus reliability bins.

## Prediction intervals

The runner evaluates empirical coverage of the model's P10–P90, P25–P75 and P05–P95 intervals against actual fantasy points.

## Confidence calibration

Errors are segmented into confidence buckets so the model can be checked for whether higher-confidence predictions actually produce lower error.

## Layer attribution

Every observation retains active layer impacts. Stage 2 computes the relationship between each layer's impact and the eventual fantasy-point error so later calibration can distinguish useful signal from harmful amplification.

## Important limitation

This is a **complete Stage 2 run over the data currently bundled with the project**, but it is not yet a statistically final multi-season calibration. The supplied data contains only 2026 Weeks 1–4, so there is not enough historical breadth to claim robust NFL-wide calibration. The architecture is now ready to ingest additional seasons without changing the calibration contract.

## Files

- `backend/engine/calibration.py` — walk-forward evaluator, metrics, TD calibration, interval coverage, confidence calibration and layer attribution.
- `CALIBRATION_REPORT_STAGE2.json` — full machine-readable observations/metrics/profile.
- `docs/VALIDATION_PLAN.md` — validation requirements.
