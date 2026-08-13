"""Command line entry point. All subprocess arguments are passed without a shell."""
import argparse
import json
import sys
from pathlib import Path


def parser():
    p = argparse.ArgumentParser(prog="corelens", description="Profile programs and measure optimization experiments")
    p.add_argument("--native", default="corelens-native", help="path to native profiler")
    p.add_argument("--version", action="version", version="CoreLens 0.1.0")
    p.add_subparsers(dest="command", required=True)
    return p


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
