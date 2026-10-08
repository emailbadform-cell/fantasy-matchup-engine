# FME v1.9.19 — data status and waiver display patch

Apply these files onto v1.9.18 (which must already be installed):

- `backend/integrations/nflverse.py`: Verify required team-week statistics exist before labeling an unrecorded player as DATA PENDING. Does not claim to establish injury/inactive participation status.
- `backend/engine/waivers.py`: Include a conservative decision label; never claim an unmodeled rest-of-season upgrade.
- `fantasy-matchup-dashboard/index.html`: Render exactly Pickup, Roster Drop, New Starter, Projected Gain, Decision; show `No prior-week stats` for individual missing rows when team data exists.
- `backend/tests/test_v1919_waiver_data_quality.py`: Regression tests.

**Limitations:** This patch does NOT add a future-week projection engine or prove a player was inactive. Current-week projection numbers are unchanged. Waiver decisions remain advisory; all potential permanent drops require ROS review. It does not fix the underlying per-player refresh overhead or guarantee complete player identity mapping.
