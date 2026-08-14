"""Evaluate candidate flags or a candidate source against an O2 baseline."""
from .benchmark import scheduled_benchmarks
from .build import build_matrix
from .compare import comparison, environment


def experiment(source, build_dir="out/experiment", compiler="clang++", flags=(), candidate_flags=(),
               baseline_flags=(), candidate_source=None, program_args=(), **measurement):
    from pathlib import Path
    if not candidate_flags and not candidate_source:
        raise ValueError("provide candidate compiler flags or a candidate source")
    directory = Path(build_dir)
    baseline = build_matrix(source, directory / "baseline", compiler, ("O2",), [*flags, *baseline_flags])
    candidate = build_matrix(candidate_source or source, directory / "candidate", compiler, ("O2",), [*flags, *candidate_flags])
    commands = {"baseline": [baseline["builds"][0]["binary"], *program_args],
                "candidate": [candidate["builds"][0]["binary"], *program_args]}
    results, order = scheduled_benchmarks(commands, **measurement)
    verdict = comparison(results["baseline"], results["candidate"])
    return {"schema_version": 1, "kind": "experiment", "environment": environment(),
            "manifests": {"baseline": baseline, "candidate": candidate}, "baseline": "baseline",
            "variants": results, "trial_order": order, "comparisons": {"candidate": verdict},
            "decision": verdict["verdict"],
            "correctness_scope": "Exact stdout agreement for the supplied input only; this is not a proof for all inputs."}
