"""Command line entry point. All subprocess arguments are passed without a shell."""
import argparse
import json
import sys
from pathlib import Path


def parser():
    p = argparse.ArgumentParser(prog="corelens", description="Profile programs and measure optimization experiments")
    p.add_argument("--native", default="corelens-native", help="path to native profiler")
    p.add_argument("--version", action="version", version="CoreLens 0.1.0")
    sub = p.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="compile a source at O0, O2, and O3")
    build.add_argument("source")
    build.add_argument("--compiler", default="clang++")
    build.add_argument("--build-dir", default="out/builds")
    build.add_argument("--flag", action="append", default=[], help="extra compiler flag; use --flag=-march=native")
    build.add_argument("--output")
    build.set_defaults(handler=lambda a: __import__("corelens.build", fromlist=["build_matrix"]).build_matrix(
        a.source, a.build_dir, a.compiler, flags=a.flag))
    bench = sub.add_parser("bench", help="benchmark an existing executable")
    measurement_options(bench)
    bench.add_argument("program", nargs=argparse.REMAINDER)
    bench.set_defaults(handler=lambda a: __import__("corelens.benchmark", fromlist=["benchmark"]).benchmark(
        strip_separator(a.program), a.native, a.repeats, a.warmups, a.timeout, a.perf, a.cpu, a.units))
    compare = sub.add_parser("compare", help="build and compare O0, O2, and O3")
    source_options(compare)
    measurement_options(compare)
    compare.set_defaults(handler=lambda a: __import__("corelens.compare", fromlist=["compare"]).compare(
        a.source, a.build_dir, a.compiler, a.flag, a.arg, **measurement_kwargs(a)))
    analysis = sub.add_parser("analyze", help="inspect LLVM assembly and suggest experiments")
    analysis.add_argument("binary")
    analysis.add_argument("--objdump", default="llvm-objdump")
    analysis.add_argument("--function")
    analysis.add_argument("--benchmark", help="optional bench JSON for counter evidence")
    analysis.add_argument("--output")
    analysis.set_defaults(handler=analyze_handler)
    experiment = sub.add_parser("experiment", help="measure candidate compiler flags or source changes")
    source_options(experiment)
    experiment.set_defaults(build_dir="out/experiment")
    measurement_options(experiment)
    experiment.add_argument("--candidate-flag", action="append", default=[])
    experiment.add_argument("--baseline-flag", action="append", default=[])
    experiment.add_argument("--candidate-source")
    experiment.set_defaults(handler=lambda a: __import__("corelens.experiment", fromlist=["experiment"]).experiment(
        a.source, a.build_dir, a.compiler, a.flag, a.candidate_flag, a.baseline_flag, a.candidate_source, a.arg,
        **measurement_kwargs(a)))
    return p


def strip_separator(command):
    return command[1:] if command and command[0] == "--" else command


def analyze_handler(a):
    from .advice import analyze, advise
    assembly = analyze(a.binary, a.native, a.objdump, a.function)
    benchmark = json.loads(Path(a.benchmark).read_text(encoding="utf-8")) if a.benchmark else None
    return {**assembly, "advice": advise(assembly, benchmark)}


def source_options(p):
    p.add_argument("source")
    p.add_argument("--compiler", default="clang++")
    p.add_argument("--build-dir", default="out/compare")
    p.add_argument("--flag", action="append", default=[])
    p.add_argument("--arg", action="append", default=[], help="one workload argument; repeat for multiple arguments")


def measurement_kwargs(a):
    return {"native": a.native, "repeats": a.repeats, "warmups": a.warmups, "timeout": a.timeout,
            "perf": a.perf, "cpu": a.cpu, "units": a.units}


def measurement_options(p):
    p.add_argument("--repeats", type=int, default=7)
    p.add_argument("--warmups", type=int, default=2)
    p.add_argument("--timeout", type=float, default=30)
    p.add_argument("--perf", action="store_true")
    p.add_argument("--cpu", type=int, help="Linux taskset CPU index")
    p.add_argument("--units", type=float, default=1, help="work units processed per invocation")
    p.add_argument("--output")


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        result = args.handler(args)
        output = getattr(args, "output", None)
        content = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if output:
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        else:
            print(content, end="")
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        print(f"corelens: {error}", file=sys.stderr)
        return 2
