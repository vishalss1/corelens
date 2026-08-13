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


def scheduled_benchmarks(commands, native="corelens-native", repeats=7, warmups=2, timeout=30, perf=False, cpu=None, units=1, seed=713):
    import random
    from .stats import summarize
    if not commands or repeats < 2 or warmups < 0 or not math.isfinite(units) or units <= 0:
        raise ValueError("commands, repeats >= 2, warmups >= 0, and finite positive units required")
    rng = random.Random(seed)
    samples = {name: [] for name in commands}
    order_log = []
    expected = None

    def checked(command, counters=False):
        nonlocal expected
        sample = measure(command, native, timeout, counters, cpu)
        if expected is not None and sample["output_sha256"] != expected:
            raise RuntimeError("workload output differs across trials or variants; candidate correctness is unverified")
        expected = sample["output_sha256"]
        return sample

    for round_number in range(warmups + repeats):
        order = list(commands)
        rng.shuffle(order)
        if round_number >= warmups:
            order_log.append(order)
        for name in order:
            sample = checked(commands[name])
            if round_number >= warmups:
                samples[name].append(sample)
    # Collect counters in separate trials, keeping perf startup and instrumentation out of runtime comparisons.
    if perf:
        for index in range(repeats):
            order = list(commands)
            rng.shuffle(order)
            for name in order:
                counted = checked(commands[name], True)
                samples[name][index]["counters"] = counted["counters"]
                samples[name][index]["derived"] = counted["derived"]
                samples[name][index]["counter_elapsed_seconds"] = counted["elapsed_seconds"]
                samples[name][index]["counter_error"] = counted["counter_error"]
    results = {}
    for name, command in commands.items():
        results[name] = {"schema_version": 1, "command": list(command), "warmups": warmups, "units": units,
                         "perf": perf, "cpu": cpu, "output_sha256": expected, "samples": samples[name],
                         "summary": summarize(samples[name], units)}
    return results, order_log


def benchmark(command, native="corelens-native", repeats=7, warmups=2, timeout=30, perf=False, cpu=None, units=1):
    results, order = scheduled_benchmarks({"workload": command}, native, repeats, warmups, timeout, perf, cpu, units)
    return {**results["workload"], "trial_order": order}
