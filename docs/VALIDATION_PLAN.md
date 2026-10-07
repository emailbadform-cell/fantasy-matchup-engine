# Final validation gate

Do not call the model validated until:
1. Historical walk-forward predictions run for multiple seasons/weeks.
2. Target-week leakage checks pass.
3. QB/RB/WR/TE/K/DEF are evaluated separately.
4. MAE/RMSE are reported for each counting stat.
5. Fantasy-point MAE and bias are reported.
6. TD calibration is reported.
7. Low/median/high interval coverage is measured.
8. Confidence calibration is measured.
9. Errors are segmented by QB tier, game total, spread, injury/status and matchup type.
10. Week 4 is treated as an out-of-sample audit, not a tuning set.

The audit must retain factor-level explanations so misses can be attributed to QB, offense, defense, usage, matchup, game environment, explosive plays or TD assumptions.
