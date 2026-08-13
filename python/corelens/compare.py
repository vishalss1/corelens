"""Compile and compare a randomized optimization-level matrix."""
import platform
from datetime import datetime, timezone
from .benchmark import scheduled_benchmarks
from .build import build_matrix
from .stats import speedup_interval


def counter_deltas(baseline, candidate):
    result = {}
    for name, entry in baseline["summary"]["counters"].items():
        other = candidate["summary"]["counters"].get(name, {})
        b, c = entry.get("values"), other.get("values")
        if b and c:
            result[name] = {"baseline_median": b["median"], "candidate_median": c["median"],
                            "relative_change": c["median"] / b["median"] - 1 if b["median"] else None}
    return result


def environment():
    return {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "system": platform.system(),
            "release": platform.release(), "machine": platform.machine(), "processor": platform.processor(),
            "python": platform.python_version()}


def comparison(baseline, candidate, paired=True):
    b = [s["elapsed_seconds"] for s in baseline["samples"]]
    c = [s["elapsed_seconds"] for s in candidate["samples"]]
    return {**speedup_interval(b, c, paired), "counter_deltas": counter_deltas(baseline, candidate),
            "output_matches": baseline["output_sha256"] == candidate["output_sha256"]}


def compare(source, build_dir="out/compare", compiler="clang++", flags=(), program_args=(), **measurement):
    manifest = build_matrix(source, build_dir, compiler, flags=flags)
    commands = {b["name"]: [b["binary"], *program_args] for b in manifest["builds"]}
    results, order = scheduled_benchmarks(commands, **measurement)
    return {"schema_version": 1, "kind": "comparison", "environment": environment(), "manifest": manifest,
            "baseline": "O0", "variants": results, "trial_order": order,
            "comparisons": {name: comparison(results["O0"], result) for name, result in results.items() if name != "O0"}}
