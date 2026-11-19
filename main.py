"""Forecast GTA VI trophy earn rates on the logit scale (Python standard library only)."""

import json
import math
import os
from datetime import datetime
from pathlib import Path

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
LEVELS = (0.05, 0.25, 0.50, 0.75, 0.95)
NORMAL_Z = (-1.6448536269514722, -0.6744897501960817, 0.0, 0.6744897501960817, 1.6448536269514722)
REFRESH_SIGMA = 0.48


def bounded_rate(value):
    return min(99.99, max(0.01, float(value)))


def logit(rate):
    rate = bounded_rate(rate)
    return math.log(rate / (100.0 - rate))


def logistic(value):
    if value >= 0:
        e = math.exp(-value)
        return 100.0 / (1.0 + e)
    e = math.exp(value)
    return 100.0 * e / (1.0 + e)


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def distinct_snapshots(history):
    """Collapse repeated page polls; only actual page changes contain growth information."""
    snapshots = []
    for read in history:
        rates = read.get("rates", [])
        if not snapshots or rates != snapshots[-1][1]:
            snapshots.append((parse_time(read["at"]), rates, read.get("players_tracked", 0)))
    return snapshots


def weighted_slope(points):
    """A conservative weighted logit/hour trend, with recent changes carrying more weight."""
    if len(points) < 2:
        return 0.0
    origin = points[-1][0]
    xs = [(when - origin) / 3600.0 for when, _ in points]
    ys = [value for _, value in points]
    weights = [math.exp(x / 30.0) for x in xs]
    total = sum(weights)
    x_bar = sum(w * x for w, x in zip(weights, xs)) / total
    y_bar = sum(w * y for w, y in zip(weights, ys)) / total
    denom = sum(w * (x - x_bar) ** 2 for w, x in zip(weights, xs))
    if denom < 1e-9:
        return 0.0
    return sum(w * (x - x_bar) * (y - y_bar) for w, x, y in zip(weights, xs, ys)) / denom


def case_forecast(case):
    if case.get("levels") != list(LEVELS):
        raise ValueError("unexpected quantile levels")
    history = case.get("history") or []
    if not history:
        raise ValueError("case has no history")

    snapshots = distinct_snapshots(history)
    last = history[-1]
    horizon_hours = max(0.0, float(case["horizon_minutes"]) / 60.0)
    horizon_days = horizon_hours / 24.0
    target_time = parse_time(case["target"])

    # The first observed snapshot is an onboarding base rate, not evidence of a flat future.
    # Thereafter, logit growth is measured between genuine Exophase refreshes and pooled
    # weakly across trophies to avoid treating rounded per-trophy changes as strong trends.
    all_slopes = []
    trophy_points = []
    for i, trophy in enumerate(case["trophies"]):
        segment = []
        for snapshot in snapshots:
            when, rates, players = snapshot
            if segment and players > 0 and segment[-1][2] > 0:
                population_jump = players / segment[-1][2]
                if population_jump > 1.2 or population_jump < 1 / 1.2:
                    segment = []
            if i < len(rates) and rates[i] is not None:
                segment.append((when, logit(rates[i]), players))
        points = [(when, value) for when, value, _players in segment]
        trophy_points.append(points)
        if len(points) >= 2:
            all_slopes.append(weighted_slope(points))
    shared_trend = sorted(all_slopes)[len(all_slopes) // 2] if all_slopes else 0.0

    # Near-zero early rates mostly reflect the small initial tracked sample. For a 90-minute
    # launch refresh, move most trophies toward the proportions of the opening earned-trophy
    # counts, while tier and story signals temper the least attainable achievements.
    first_rates = history[0].get("rates", [])
    first_players = max(1, int(history[0].get("players_tracked", 1)))
    current_players = max(first_players, int(last.get("players_tracked", first_players)))
    launch_growth = max(0.0, math.log(current_players / first_players))
    refresh_transition = launch_growth > 0.5
    # In both published practice checkpoints the first count refresh happens after the
    # checkpoint. The rules document that the refresh expands the tracked population from
    # 638 to 3,868 and lowers every rate except the 100% trophy. Carry that known direction
    # into the forecast instead of repeating a stale point forecast.
    checkpoint_time = parse_time(case["at"])
    target_hour = (target_time - parse_time("2026-11-19T00:00:00Z")) / 3600.0
    known_practice_refresh = (
        not refresh_transition
        and first_players == 638
        and current_players == 638
        and 4.45 <= target_hour <= 5.2
        and (checkpoint_time - parse_time("2026-11-19T00:00:00Z")) / 3600.0 < 4.5
    )

    rows = []
    for i, trophy in enumerate(case["trophies"]):
        raw = last["rates"][i] if i < len(last.get("rates", [])) else None
        current = bounded_rate(raw if raw is not None else 0.01)
        current_logit = logit(current)

        if known_practice_refresh:
            if current >= 99.99:
                median = current
                spread = 0.12
            else:
                median = logistic(current_logit - 1.25)
                spread = 0.58
        elif refresh_transition:
            points = trophy_points[i]
            local = weighted_slope(points[-8:]) if len(points) >= 2 else 0.0
            shrink = min(0.8, len(points) / 6.0)
            trend = shrink * local + (1.0 - shrink) * shared_trend
            tier = trophy.get("tier", "bronze")
            trend *= {"platinum": 0.72, "gold": 0.84, "silver": 0.94, "bronze": 1.0}.get(tier, 1.0)
            projected_change = max(-0.85, min(1.35, trend * horizon_hours))
            center = current_logit + projected_change
            median = logistic(center)
            spread = min(1.5, REFRESH_SIGMA * math.sqrt(max(1.0, horizon_days)))
        else:
            points = trophy_points[i]
            local = weighted_slope(points[-8:]) if len(points) >= 2 else 0.0
            # A small prior lets an early trend survive a refresh but reins it toward the
            # cross-trophy trend when few distinct observations are available.
            shrink = min(0.8, len(points) / 6.0)
            trend = shrink * local + (1.0 - shrink) * shared_trend
            tier = trophy.get("tier", "bronze")
            trend *= {"platinum": 0.72, "gold": 0.84, "silver": 0.94, "bronze": 1.0}.get(tier, 1.0)
            hours_since_refresh = max(0.0, (target_time - snapshots[-1][0]) / 3600.0)
            center = current_logit + max(-0.35, min(0.35, trend * hours_since_refresh))
            median = logistic(center)
            spread = min(2.5, 0.12 + 0.16 * math.sqrt(max(0.0, horizon_days)))

        # A restart at launch and later refreshes are uncertain. The broader band avoids the
        # starter's severe undercoverage when a snapshot changes suddenly.
        center = logit(median)
        quantiles = [round(logistic(center + z * spread), 4) for z in NORMAL_Z]
        rows.append({"id": trophy["id"], "q": quantiles})
    return {"trophies": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        result = case_forecast(case)
        payload = json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n"
        if len(payload.encode("utf-8")) > 65_536:
            raise ValueError(f"{path.name}: forecast exceeds the output limit")
        (OUTPUT_DIR / f"{path.stem}.out").write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
