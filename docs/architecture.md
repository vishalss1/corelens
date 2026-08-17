# Architecture

```text
Python CLI
  build.py       Clang invocation -> binary + digest + manifest + optional LLVM records
  benchmark.py   seeded trial scheduling -> native run JSON -> output digest checks
  stats.py       medians, dispersion, counter summaries, bootstrap intervals
  compare.py     O0/O2/O3 matrix -> timings + optional assembly explanations
  experiment.py  O2 baseline + candidate flags/source -> correctness + measured verdict
  advice.py      static findings + counter evidence -> experiment suggestions
  report.py      result JSON -> standalone HTML / Markdown

C++ native CLI
  process.cpp    isolated process tree, deadline, bounded stdout/stderr capture
  perf.cpp       perf stat -> event states + multiplexing + derived ratios
  assembly.cpp   llvm-objdump -> per-function instructions -> heuristic patterns
  json.cpp       strict JSON transport, including byte-safe stdout encoding
```

LLVM is integrated through its command line tools, allowing LLVM versions to
be upgraded without linking CoreLens against a particular libLLVM ABI. Clang
is the default driver. LLVM disassembly works on supported ELF, PE/COFF, and
Mach-O inputs; heuristics currently target x86 and AArch64 mnemonics. Python
uses only the standard library at runtime. Optimization-record summaries
extract selected top-level fields and preserve raw argument YAML; original
records are the authoritative detailed explanation.

Native `run` accepts an argv vector after `--`. No shell interprets workload
arguments. Linux starts a process group and kills it at the deadline. Windows
starts a suspended process, assigns a job object, resumes it, and terminates
the job on timeout or parent completion. Child stdout and stderr are capped
at 4 MiB each but drained to prevent blocked producers. Exceeding the cap
invalidates Python correctness checking.

All JSON documents use `schema_version: 1`. The native profile contains
`elapsed_seconds`, `exit_code`, `timed_out`, `output_truncated`, `stdout`,
`stderr`, `counter_error`, `counters`, and `derived`. Arbitrary stdout bytes
are serialized as Latin-1 Unicode code points; Python restores those bytes
before SHA-256 hashing. Counter entries have nullable `value`, nullable
`running_percent`, and a status: `ok`, `missing`, `unsupported`, `not_counted`,
or `invalid`. Missing values never become zero.

Python benchmark results contain `samples` and `summary`. Comparison and
experiment documents contain named `variants`, `comparisons`, `trial_order`,
and provenance. Runtime and counter data in a sample come from different
process invocations; `counter_elapsed_seconds` marks the latter. Output
agreement is mandatory across both measurement types. Binary stdout alone
cannot prove source-change equivalence; external correctness tests remain
necessary for production changes.

Native exit codes: 0 for successful workloads/analysis, 1 for failed workloads,
2 for invocation/tool errors, and 124 for workload timeouts. The Python CLI
returns 2 for failed operations. Individual failed trials are rejected rather
than included in summaries.
