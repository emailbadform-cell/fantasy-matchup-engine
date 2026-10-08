# FME v1.9.18 — ESPN Defense Crosswalk + Starting-Lineup Waivers

Based on v1.9.17 supplied in the conversation (not a live fetch of the private GitHub repository).

- ESPN negative D/ST IDs (example `-16014` for Rams) resolve via NFL team ID even if ESPN omits defense metadata. ESPN's `LA` is aliased to Sleeper's `LAR`. Unresolved other identities remain explicit failures.
- Waiver pickup must appear in the new optimized starting lineup; no bench-only pickups are recommended.
- Drop can be from the bench or a starter displaced by the new optimized lineup, with existing bye and roster safeguards intact.
- Each suggestion reports starter replaced, starting slot of the pickup, bench/starter drop location, and actual optimized lineup points gain.
- Consecutive recommendations re-optimize the remaining roster.
- No rest-of-season valuation is asserted; results remain current-week recommendations.

Tests: 103 offline tests passed. One separate NFLverse defense-history test requires external network and couldn't run in the offline environment.

Deploy: update the source on Windows, commit/push to GitHub, and `git pull` on Oracle followed by `sudo systemctl restart fme`. Backup your current source before overwriting. Do not overwrite `.venv`, `.env`, or credentials.
