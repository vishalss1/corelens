import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from corelens.benchmark import measure, scheduled_benchmarks
from corelens.results import load, validate_report
from corelens.compare import counter_deltas
from corelens.remarks import read_remarks
from corelens.report import render
from corelens.stats import distribution, speedup_interval


def sample(runtime=1, output="same", counters=False):
    return {"elapsed_seconds": runtime, "output_sha256": output, "counters": {"cycles": {"value": 100 if counters else None,
            "running_percent": 75 if counters else None}}, "derived": {"ipc": 2 if counters else None}, "counter_error": ""}


class StatisticsTests(unittest.TestCase):
    def test_decisions_and_pairing(self):
        self.assertEqual(speedup_interval([2, 2, 2], [1, 1, 1])["verdict"], "improved")
        self.assertEqual(speedup_interval([1, 1, 1], [2, 2, 2])["verdict"], "regressed")
        self.assertEqual(speedup_interval([1, 1, 1], [1, 1, 1])["verdict"], "inconclusive")
        self.assertEqual(speedup_interval([2, 4, 6], [1, 2, 3], paired=True)["ci95"], [2, 2])
        for bad in ([0, 1], [float("nan"), 1]):
            with self.assertRaises(ValueError):
                speedup_interval(bad, [1, 1])

    def test_zero_and_missing(self):
        self.assertIsNone(distribution([0, 0])["relative_mad"])
        with self.assertRaises(ValueError):
            distribution([])


class BenchmarkTests(unittest.TestCase):
    def test_interleaving_and_separate_counter_trials(self):
        calls = []
        def fake(command, native, timeout, perf, cpu):
            calls.append((command, perf))
            return sample(10 if perf else 1, counters=perf)
        with patch("corelens.benchmark.measure", side_effect=fake):
            results, order = scheduled_benchmarks({"a": ["a"], "b": ["b"]}, repeats=3, warmups=1, perf=True)
        self.assertEqual(len(calls), 14)
        self.assertTrue(all(sorted(row) == ["a", "b"] for row in order))
        self.assertEqual(results["a"]["summary"]["runtime_seconds"]["median"], 1)
        self.assertEqual(results["a"]["summary"]["counters"]["cycles"]["minimum_running_percent"], 75)
        self.assertEqual(results["a"]["samples"][0]["counter_elapsed_seconds"], 10)
        self.assertEqual(counter_deltas(results["a"], results["b"])["cycles"]["relative_change"], 0)

    def test_mismatched_output_blocks_candidate(self):
        with patch("corelens.benchmark.measure", side_effect=[sample(output="a"), sample(output="b")]):
            with self.assertRaisesRegex(RuntimeError, "correctness"):
                scheduled_benchmarks({"a": ["a"], "b": ["b"]}, repeats=2, warmups=0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            scheduled_benchmarks({"a": ["a"]}, repeats=1)


class InputTests(unittest.TestCase):
    def test_invalid_schema_and_nonfinite_json(self):
        with self.assertRaises(ValueError):
            validate_report({"schema_version": 99})
        with self.assertRaises(ValueError):
            validate_report({"schema_version": 1, "variants": {}})
        with self.assertRaises(ValueError):
            validate_report({"schema_version": 1, "summary": {}})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"value": NaN}')
            with self.assertRaises(ValueError):
                load(path)

    def test_stdout_hash_restores_native_bytes(self):
        import hashlib
        import subprocess
        data = {"stdout": "é", "stderr": "", "exit_code": 0, "timed_out": False,
                "output_truncated": False, "elapsed_seconds": 1, "counter_error": "", "counters": {}, "derived": {}}
        completed = subprocess.CompletedProcess([], 0, json.dumps(data), "")
        with patch("corelens.benchmark.subprocess.run", return_value=completed):
            measured = measure(["program"])
        self.assertEqual(measured["output_sha256"], hashlib.sha256(bytes([233])).hexdigest())


class ArtifactTests(unittest.TestCase):
    def test_report_escaping(self):
        with patch("corelens.benchmark.measure", return_value=sample()):
            variants, _ = scheduled_benchmarks({"<script>alert(1)</script>": ["a"]}, repeats=2, warmups=0)
        data = {"variants": variants}
        report = render(data)
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertIn("Median seconds", render(data, "markdown"))
        json.dumps(data, allow_nan=False)

    def test_llvm_remark_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.opt.yaml"
            path.write_text("--- !Missed\nPass: loop-vectorize\nName: CantVectorize\nFunction: _Z4workv\n"
                            "DebugLoc: { File: test.cpp, Line: 8, Column: 3 }\nArgs:\n  - String: dependency\n...\n")
            remarks = read_remarks(path)["remarks"]
            self.assertEqual(remarks[0]["pass"], "loop-vectorize")
            self.assertIn("dependency", remarks[0]["arguments_yaml"])


if __name__ == "__main__":
    unittest.main()
