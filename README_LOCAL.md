# Fantasy Matchup Engine v0.2.1

Local-first unified foundation.

## Run
Double-click `run_local.bat`.

Then open:
- http://127.0.0.1:8000/
- http://127.0.0.1:8000/health

Week 4 test:
http://127.0.0.1:8000/api/v1/fantasy/league/1394139092932907008/team/xthesleepersyndicate/week/4/matchup?season=2026

## Architecture
Sleeper -> player -> team -> NFLverse game -> GameContext -> QB/offense/defense -> matchup -> position projection -> scoring.

The current release implements the data bridge and model contracts. Projection engines are intentionally deterministic placeholders until historical player/play-by-play inputs are wired in.

## Corrected QB model (v1.8.0)
QB projections now use chronology-safe recency-weighted attempt volume, damped game-script direction, bounded contextual YPA stacking, and QB-specific passing-TD rate. The generic team TD/play red-zone proxy no longer suppresses QB passing TDs.

QB responses also include `stat_distribution`, a stat-level Monte Carlo distribution. It defaults to 1,000,000 draws. To use fewer draws while developing on Windows PowerShell:

    $env:FME_QB_STAT_MC_N="10000"

Remove the variable (or set it to `1000000`) for the full run.
