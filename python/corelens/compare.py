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
    context = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "system": platform.system(),
            "release": platform.release(), "machine": platform.machine(), "processor": platform.processor(),
            "python": platform.python_version()}
    if platform.system() == "Linux":
        from pathlib import Path
        import os
        for key, path in (("cpuinfo", "/proc/cpuinfo"), ("governor_cpu0", "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
                          ("perf_event_paranoid", "/proc/sys/kernel/perf_event_paranoid")):
            try:
                text = Path(path).read_text().strip()
                if key == "cpuinfo":
                    text = next((line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("model name")), "unknown")
                context[key] = text
            except OSError:
                context[key] = None
        if hasattr(os, "sched_getaffinity"):
            context["allowed_cpus"] = sorted(os.sched_getaffinity(0))
    return context


def comparison(baseline, candidate, paired=True):
    b = [s["elapsed_seconds"] for s in baseline["samples"]]
    c = [s["elapsed_seconds"] for s in candidate["samples"]]
    return {**speedup_interval(b, c, paired), "counter_deltas": counter_deltas(baseline, candidate),
            "output_matches": baseline["output_sha256"] == candidate["output_sha256"]}


def compare(source, build_dir="out/compare", compiler="clang++", flags=(), program_args=(), assembly=False, remarks=False, objdump="llvm-objdump", **measurement):
    if any(flag.startswith("-O") for flag in flags):
        raise ValueError("compare controls optimization levels; pass other compiler flags with --flag")
    manifest = build_matrix(source, build_dir, compiler, flags=flags, remarks=remarks)
    commands = {b["name"]: [b["binary"], *program_args] for b in manifest["builds"]}
    results, order = scheduled_benchmarks(commands, **measurement)
    explanations = {}
    if assembly:
        from .advice import analyze
        for build in manifest["builds"]:
            explanations[build["name"]] = analyze(build["binary"], measurement.get("native", "corelens-native"), objdump)
        baseline_count = sum(f["instruction_count"] for f in explanations["O0"]["functions"])
        for explanation in explanations.values():
            count = sum(f["instruction_count"] for f in explanation["functions"])
            explanation["total_instruction_sites"] = count
            explanation["instruction_site_delta_from_O0"] = count - baseline_count
            explanation["scope"] = "Whole binary static instruction sites, including runtime code; not executed instruction counts."
    return {"schema_version": 1, "kind": "comparison", "assembly": explanations, "environment": environment(), "manifest": manifest,
            "baseline": "O0", "variants": results, "trial_order": order,
            "comparisons": {name: comparison(results["O0"], result) for name, result in results.items() if name != "O0"}}
