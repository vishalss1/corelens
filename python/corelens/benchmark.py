"""Repeated process timing with strict failure and correctness handling."""
import hashlib
import json
import math
import subprocess


def measure(command, native="corelens-native", timeout=30, perf=False, cpu=None):
    if not command or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("command and finite positive timeout required")
    target = list(command)
    if cpu is not None:
        if cpu < 0:
            raise ValueError("CPU index must be nonnegative")
        target = ["taskset", "-c", str(cpu), *target]
    invocation = [native, "run", "--timeout", str(timeout)]
    if perf:
        invocation.append("--perf")
    completed = subprocess.run([*invocation, "--", *target], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=timeout + 10, check=False)
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"native profiler failed: {completed.stderr.strip()}") from error
    if completed.returncode or result["exit_code"] or result["timed_out"]:
        raise RuntimeError(f"workload failed: exit={result['exit_code']}, timeout={result['timed_out']}, stderr={result['stderr']}")
    if result["output_truncated"]:
        raise RuntimeError("workload output exceeded capture limit; cannot check correctness")
    if perf and result["counter_error"]:
        raise RuntimeError(result["counter_error"] + ": " + result["stderr"])
    result["output_sha256"] = hashlib.sha256(result.pop("stdout").encode("utf-8")).hexdigest()
    return result


def benchmark(command, native="corelens-native", repeats=7, warmups=2, timeout=30, perf=False, cpu=None, units=1):
    if repeats < 2 or warmups < 0 or not math.isfinite(units) or units <= 0:
        raise ValueError("repeats >= 2, warmups >= 0, and finite positive units required")
    expected = None
    samples = []
    for i in range(warmups + repeats):
        sample = measure(command, native, timeout, perf, cpu)
        if expected is not None and sample["output_sha256"] != expected:
            raise RuntimeError("workload output changed between runs; use deterministic validation output")
        expected = sample["output_sha256"]
        if i >= warmups:
            samples.append(sample)
    from .stats import summarize
    return {"schema_version": 1, "command": list(command), "warmups": warmups, "units": units,
            "perf": perf, "cpu": cpu, "output_sha256": expected,
            "samples": samples, "summary": summarize(samples, units)}
