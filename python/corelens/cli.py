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
    return p


def strip_separator(command):
    return command[1:] if command and command[0] == "--" else command


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
