# Data sources

Primary:
- Sleeper API: league, roster, matchup, player identity and scoring settings.
- nflverse schedule/game data.
- nflverse weekly player stats.
- nflverse team stats.
- nflverse players and weekly rosters.
- nflverse PBP when available.

nflverse's current release repository documents automated releases for schedules, player stats, team stats, players, rosters and related datasets. The project recommends using nflreadr/nflreadpy or direct release URLs. Direct URLs in this package have fallbacks and local caching.

Advanced charting/coverage assignments are treated as optional. If the source does not contain a defensible assignment, the model uses a neutral factor rather than inventing one.
