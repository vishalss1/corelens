"""Explicit integration checks; requires a built native executable and Clang/LLVM."""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from corelens.advice import analyze, advise
from corelens.benchmark import benchmark
from corelens.build import build_matrix
from corelens.compare import compare
from corelens.experiment import experiment
from corelens.report import render


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--native", required=True)
    p.add_argument("--compiler", default="clang++")
    p.add_argument("--objdump", default="llvm-objdump")
    args = p.parse_args()
    native = str(Path(args.native).resolve())
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        data = compare(root / "workloads/arithmetic.cpp", folder / "matrix", args.compiler,
                       program_args=["10000"], native=native, repeats=2, warmups=0)
        assert set(data["variants"]) == {"O0", "O2", "O3"}
        assert all(c["output_matches"] for c in data["comparisons"].values())
        assembly = analyze(data["manifest"]["builds"][1]["binary"], native, args.objdump, "main")
        assert assembly["functions"]
        assert advise(assembly)["limitations"]
        assert "CoreLens" in render(data)
        assert "Hardware counter" in render(data, "markdown")
        result = experiment(root / "workloads/arithmetic.cpp", folder / "experiment", args.compiler,
                            candidate_flags=["-O3"], program_args=["10000"], native=native, repeats=2, warmups=0)
        assert result["comparisons"]["candidate"]["output_matches"]
        candidate = folder / "incorrect.cpp"
        candidate.write_text('#include <iostream>\nint main(){std::cout << "wrong";}\n')
        try:
            experiment(root / "workloads/arithmetic.cpp", folder / "wrong", args.compiler,
                       candidate_source=candidate, program_args=["10000"], native=native, repeats=2, warmups=0)
        except RuntimeError as error:
            assert "correctness" in str(error)
        else:
            raise AssertionError("incorrect candidate was accepted")
        c_build = build_matrix(root / "workloads/c_sum.c", folder / "c", args.compiler)
        digest = None
        for build in c_build["builds"]:
            measured = benchmark([build["binary"], "10000"], native, repeats=2, warmups=0)
            assert digest is None or digest == measured["output_sha256"]
            digest = measured["output_sha256"]
        remarks = build_matrix(root / "workloads/vector.cpp", folder / "remarks", args.compiler, ("O2",), remarks=True)
        assert remarks["builds"][0]["optimization_remarks"]["remarks"]
        # Exercise the real native collector using an explicitly synthetic perf fixture.
        if os.name != "nt":
            fake = folder / "perf"
            fake.write_text("#!/usr/bin/env python3\nimport subprocess, sys\n"
                            "args=sys.argv[1:]\np=args[args.index('-o')+1]\n"
                            "open(p,'w').write('100;;cycles;1000;100;;\\n200;;instructions;1000;100;;\\n')\n"
                            "raise SystemExit(subprocess.call(args[args.index('--')+1:]))\n")
            fake.chmod(0o755)
            env = dict(os.environ, PATH=str(folder) + os.pathsep + os.environ["PATH"])
            binary = c_build["builds"][0]["binary"]
            completed = subprocess.run([native, "run", "--perf", "--", binary, "10000"], env=env,
                                       capture_output=True, text=True, check=True)
            profiled = json.loads(completed.stdout)
            assert profiled["counters"]["cycles"]["value"] == 100
            assert profiled["derived"]["ipc"] == 2
    print("All compiler, LLVM, benchmark, experiment, and report integration checks passed")


if __name__ == "__main__":
    main()
