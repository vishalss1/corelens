"""Deterministic bootstrap estimates; intervals describe observed sampling noise."""
import math
import random
import statistics


def quantile(values, probability):
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    low = math.floor(index)
    high = math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def distribution(values):
    if not values or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("samples must be nonempty, finite, and nonnegative")
    median = statistics.median(values)
    return {"count": len(values), "median": median, "min": min(values), "max": max(values),
            "mean": statistics.mean(values), "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "relative_mad": statistics.median(abs(v - median) for v in values) / median if median else None}


def summarize(samples, units=1):
    runtime = distribution([s["elapsed_seconds"] for s in samples])
    counters = {}
    names = sorted({name for s in samples for name in s["counters"]})
    for name in names:
        available = [s["counters"].get(name, {}).get("value") for s in samples]
        valid = [v for v in available if v is not None]
        percentages = [s["counters"].get(name, {}).get("running_percent") for s in samples]
        valid_percentages = [v for v in percentages if v is not None]
        counters[name] = {"available_runs": len(valid), "total_runs": len(samples),
                          "values": distribution(valid) if valid else None,
                          "minimum_running_percent": min(valid_percentages) if valid_percentages else None}
    derived = {}
    for name in sorted({name for s in samples for name in s["derived"]}):
        valid = [s["derived"].get(name) for s in samples if s["derived"].get(name) is not None]
        derived[name] = distribution(valid) if valid else None
    return {"runtime_seconds": runtime, "throughput_per_second": units / runtime["median"] if runtime["median"] else None,
            "counters": counters, "derived": derived}


def speedup_interval(baseline, candidate, paired=False, draws=2000):
    if len(baseline) < 2 or len(candidate) < 2 or draws < 100:
        raise ValueError("at least two samples and 100 bootstrap draws required")
    if any(not math.isfinite(v) or v <= 0 for v in [*baseline, *candidate]):
        raise ValueError("speedup requires finite positive runtimes")
    if paired and len(baseline) != len(candidate):
        raise ValueError("paired samples must have equal length")
    rng = random.Random(713)
    estimates = []
    if paired:
        ratios = [b / c for b, c in zip(baseline, candidate)]
        point = statistics.median(ratios)
        for _ in range(draws):
            estimates.append(statistics.median(rng.choices(ratios, k=len(ratios))))
    else:
        point = statistics.median(baseline) / statistics.median(candidate)
        for _ in range(draws):
            estimates.append(statistics.median(rng.choices(baseline, k=len(baseline))) /
                             statistics.median(rng.choices(candidate, k=len(candidate))))
    low, high = quantile(estimates, .025), quantile(estimates, .975)
    return {"speedup": point, "ci95": [low, high], "paired": paired,
            "verdict": "improved" if low > 1 else "regressed" if high < 1 else "inconclusive"}
