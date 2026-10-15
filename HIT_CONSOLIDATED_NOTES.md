# FME Hit Consolidated — local experimental integration

Changes:
- Restores independent Individual Player Projections name-search for both Sleeper and ESPN, up to 20 players, with Low / Median / High / Hit.
- Searches players outside the loaded roster. With a loaded league, scoring is fetched from the selected platform; without a league, PPR / half-PPR / standard defaults are supported.
- Optimizer displays Low / Median / High / Hit columns and separate Hit team total.
- Waiver UI displays Low / Median / High / Hit. ESPN availability is restricted to ESPN league free-agent/waiver IDs, with NFL/Sleeper player identities used for projection only; no Sleeper roster-ownership fallback.
- Sleeper waiver scans at most 529 prioritized candidates; this is NOT exhaustive, and the response indicates truncation.
- Hit QB passing-yard allowances use historical defense allowances when present, or opposing QB historical production if not. Missing data remains N/A instead of silently substituting Median.

Validation: 54 tests passed (backend tests + focused integration). The full suite has one existing failure: `test_history_status_marks_expected_missing_week_pending`, which expects data pending even though published team-week statistics allow `player_week_unrecorded`. No live ESPN or Sleeper league calls have been made.

Known limits:
- Missing NFL matchup and zero projections (e.g. Goff, LaPorta, Mevis) are NOT resolved; must validate nflverse schedule, player identity, and source freshness on the user's live installation.
- ESPN live waiver ownership must be tested against the specific ESPN league; current ESPN player metadata is projected through a shared NFL/Sleeper identity universe.
- The Hit algorithm remains experimental and is not calibrated against historical outcomes.
- A 529-player scan may exclude waiver options; the limit is a performance cap, not an eligibility definition.

Install in a new folder. Do not overwrite production. Run `run_local.bat` from the extracted `fantasy-matchup-engine-main` directory. Check the browser at http://127.0.0.1:8000 and hard-refresh.
