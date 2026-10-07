# Model Build Status

## Current version

**1.7.0-stage1-audited**

The primary `backend.engine.predictor.PredictionEngine` is the authoritative prediction path.

### Stage 1 status: COMPLETE

The model has completed structural pre-calibration remediation:

- single-owner factor architecture
- offensive/defensive scheme separation
- no duplicate play-volume multiplier
- replacement used for uncertainty only
- explosive-play context used for uncertainty only
- red-zone proxy isolated to touchdown expectation
- explicit factor ownership ledger
- formula-slot collision guard
- calibration-readiness contract
- historical cutoff preserved

### Stage 2 status: NEXT

Statistical calibration has not yet been run. The next stage is a strict walk-forward historical evaluation using only information available before each target game.

Legacy modules under `backend.engines.*` remain compatibility/architecture contracts and are not counted as authoritative prediction engines.
