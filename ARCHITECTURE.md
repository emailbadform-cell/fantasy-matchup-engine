# Fantasy Matchup Engine — Unified Architecture

## Core rule

Every update must fix known bugs **and** advance the missing architecture when the two can be safely developed in parallel.

## Data flow

Sleeper
-> Player
-> NFL Team
-> NFLverse GameContext
-> Team Context
-> QB Engine
-> Offensive Scheme/Usage
-> Defensive Scheme/Matchup
-> Position Engine
-> Explosive/TD/Game Environment
-> Fantasy Projection

## Position-neutral

The model is not a WR model.

Supported architecture:
- QB
- RB
- WR
- TE
- K
- DEF

## QB dependency

QB is an upstream factor for:
- WR targets/receptions/yards/TD
- TE targets/receptions/yards/TD
- RB receiving opportunity
- team scoring
- kicker opportunity

The QB engine therefore cannot be an optional afterthought.

## Defensive architecture

Defense must eventually expose:
- run defense
- pass defense
- pressure
- coverage
- slot/outside tendencies
- TE coverage
- RB receiving defense
- explosive-play allowance
- red-zone defense
- touchdowns allowed

## Offensive architecture

Offense must eventually expose:
- pace
- neutral pass rate
- situation pass rate
- rush rate
- target concentration
- route/usage distribution
- red-zone usage
- goal-line usage
- explosive-play rate
- personnel/formational tendencies
- scheme tendencies

## Projection architecture

Each player receives:
1. baseline historical usage
2. QB adjustment
3. offensive scheme adjustment
4. defensive scheme adjustment
5. position matchup adjustment
6. game environment adjustment
7. explosive-play adjustment
8. touchdown adjustment
9. injury/status adjustment
10. uncertainty/confidence

## v0.2.2 scope

Implemented:
- NFLverse game resolution
- LA/LAR normalization for side detection
- opponent roster -> Sleeper user mapping
- shared GameContext
- QB/offense/defense/position engine contracts
- common factor pipeline
- architecture metadata

Not yet implemented:
- real historical performance data
- real scheme classification
- coverage/personnel data
- trained/calibrated prediction weights
- final fantasy scoring projection

Those are the next parallel layers.
