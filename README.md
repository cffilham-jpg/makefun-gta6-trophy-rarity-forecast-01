# GTA VI trophy rarity forecast

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/cffilham-jpg/makefun-gta6-trophy-rarity-forecast-01/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/cffilham-jpg/makefun-gta6-trophy-rarity-forecast-01/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

Forecasts each PlayStation trophy's Exophase earn rate at the target time. The model collapses repeated page polls into distinct snapshots, estimates conservative logit trends from real refreshes, shrinks sparse trophy histories toward the shared trend, and adjusts for the known launch-night expansion of the tracked player sample. Tier and story-completion features temper the forecast, and the uncertainty band widens with the horizon.

Bounty: [Forecast how many GTA VI players earn each trophy in week one](https://make.fun/bounty/gta6-trophy-rarity-forecast-01).

## Run locally

Copy the practice cases from the kit into an `input/` directory, then run:

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

The program uses only Python's standard library and reads every `*.in` case in the input directory.

[Join make.fun](https://make.fun/r/fpna5aje)
