"""Heuristic suggestions are experiments, never a claim of dynamic hotspots."""
import json
import subprocess


def analyze(binary, native="corelens-native", objdump="llvm-objdump", function=None):
    command = [native, "analyze", binary, "--objdump", objdump]
    if function:
        command.extend(["--function", function])
    completed = subprocess.run(command, capture_output=True, text=True, timeout=70, check=False)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip())
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("invalid native assembly result") from error


def advise(assembly, benchmark=None):
    suggestions = [{"evidence": "static_assembly", **finding} for finding in assembly["findings"]]
    if benchmark:
        metrics = benchmark["summary"]["derived"]
        for metric, threshold, experiment in (
            ("branch_miss_ratio", .05, "Compare branchless code or data ordering; remeasure branch-misses and runtime."),
            ("cache_miss_ratio", .10, "Compare contiguous storage, loop tiling, or working-set reduction; remeasure cache-misses and runtime."),
        ):
            entry = metrics.get(metric)
            if entry and entry["median"] > threshold:
                suggestions.append({"evidence": "hardware_counters", "kind": metric, "value": entry["median"],
                                    "explanation": "Aggregate miss ratio exceeds a heuristic threshold; it does not locate a hot function.",
                                    "experiment": experiment})
    return {"schema_version": 1, "suggestions": suggestions,
            "compiler_experiments": [{"flags": ["-O3"], "purpose": "Compare stronger inlining and loop optimizations against O2."},
                                     {"flags": ["-funroll-loops"], "purpose": "Test loop overhead versus code size and instruction-cache pressure."},
                                     {"flags": ["-flto"], "purpose": "Test cross-translation-unit optimization; requires compatible linker support."}],
            "limitations": ["Static instruction counts are not execution counts or hotspots.",
                            "Counter ratios depend on CPU event semantics and multiplexing.",
                            "Accept an experiment only after output validation and repeated measurement."]}
