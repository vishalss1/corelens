# CoreLens

**A C++ CPU performance profiler and optimization advisor.** Collect Linux
hardware counters, inspect LLVM assembly, compare `-O0` / `-O2` / `-O3`, and
measure whether an optimization experiment improves a supplied workload.

CoreLens has a C++17 measurement engine and a Python 3.10+ command line tool.
It uses `perf stat`, Clang optimization records, and `llvm-objdump`. Timing and
assembly analysis also work on Windows. Hardware counters require Linux and
an accessible PMU; virtual machines and WSL may not expose these events.

## Build and install

Install CMake 3.20+, a C++17 compiler, Python, Clang, and LLVM tools. On an
Ubuntu system, the usual development packages are:

```sh
sudo apt-get update
sudo apt-get install cmake ninja-build clang llvm python3 python3-venv linux-tools-common linux-tools-generic
cmake -S . -B build -G Ninja -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release
cmake --build build
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
```

`perf` must match/support your running kernel. Distribution packages vary;
check `perf --version` and `perf stat -e cycles -- true` before requesting
counters. The native executable is `build/corelens-native`. Either install it
with `cmake --install build --prefix "$HOME/.local"` and add that bin directory
to PATH, or pass `--native ./build/corelens-native` before a Python subcommand.

For Windows, build from a Visual Studio developer shell with CMake, or use
Clang/MinGW and Ninja. Use `build/Release/corelens-native.exe` for a Visual
Studio generator or `build/corelens-native.exe` for Ninja. With MinGW, put its
`bin` directory first on PATH so its runtime DLLs match the compiler. Omit
`--perf` and `--cpu` on Windows.

## Compare compiler optimization levels

```sh
corelens --native ./build/corelens-native compare workloads/arithmetic.cpp   --repeats 9 --warmups 2 --arg 10000000 --units 10000000   --assembly --remarks --output out/comparison.json

# Add counters and pin to an allowed CPU on Linux:
corelens --native ./build/corelens-native compare workloads/cache.cpp   --arg 1024 --repeats 9 --perf --cpu 2 --output out/cache.json
```

Build manifests record the compiler version, exact commands, source digest,
binary digests, and compiler diagnostics. Trials use seeded randomized order.
Runtime trials run without perf; separate trials collect cycles, instructions,
cache references/misses, branches, and branch misses. Results include IPC,
miss ratios, medians, throughput, raw samples, and paired bootstrap intervals.
The supplied `--units` is the work completed by one whole process invocation.

## Profile and inspect an existing binary

```sh
./build/corelens-native run --perf --timeout 30 -- ./my-program input.dat
corelens --native ./build/corelens-native bench --repeats 9 --warmups 2   --output out/bench.json -- ./my-program input.dat
corelens --native ./build/corelens-native analyze ./my-program   --function compute --benchmark out/bench.json --output out/assembly.json
```

Assembly findings cover division, conditional branches, call density, stack
traffic, and scalar floating point patterns on x86 and AArch64. Every finding
includes an explanation and an experiment. Static counts do not locate hot
functions or establish wasted cycles. Counter evidence can suggest cache
locality or branch prediction experiments. Function filtering is a substring
match on LLVM's demangled names; optimized functions may have been inlined.

## Measure an optimization experiment

```sh
corelens --native ./build/corelens-native experiment workloads/vector.cpp   --candidate-flag=-O3 --arg 2000000 --repeats 9 --warmups 2   --output out/experiment.json

# Compare a source change against the original with the same input:
corelens --native ./build/corelens-native experiment original.cpp   --candidate-source optimized.cpp --arg 1000000 --perf   --output out/source-experiment.json
```

Experiments use an O2 baseline. Candidate flags appear after `-O2`, allowing an
explicit candidate `-O3`. Shared flags use `--flag=...`; baseline-only flags
use `--baseline-flag=...`. Candidates must produce exactly matching stdout on
all supplied trials, including warmups and counter runs. A mismatch or failed
process aborts the experiment. Use deterministic stdout checksums; correctness
checks cover the chosen inputs, not all possible inputs or side effects.

A speedup interval wholly above 1 yields `improved`, wholly below 1 yields
`regressed`, and an interval containing 1 yields `inconclusive`. This is an
observed measurement result, not a guarantee. Use representative inputs,
enough repetitions, and stable system conditions before adopting a change.

## Export results

```sh
corelens report out/comparison.json --destination out/report.html
corelens report out/experiment.json --format markdown --destination out/report.md
corelens build workloads/vector.cpp --remarks --output out/build.json
```

HTML reports are standalone and escape workload content. JSON retains raw
measurements, counter availability/multiplexing, assembly explanations, LLVM
remark summaries, environment details, and build provenance.

## Development checks

```sh
cmake -S . -B build -DCORELENS_BUILD_TESTS=ON
cmake --build build
ctest --test-dir build --output-on-failure
python -m unittest discover -s tests -p test_python.py -v
python tests/integration.py --native build/corelens-native
```

Integration checks require Clang and `llvm-objdump`; they cover compilation,
C and C++ output agreement, assembly, remarks, experiment rejection, and
reports. The Linux perf integration fixture uses synthetic counters and does
not establish real PMU availability. CI runs portable tests on Linux/Windows
and the full compiler workflow on Linux.

See [measurement methodology](docs/methodology.md),
[architecture](docs/architecture.md), and [workload guide](docs/workloads.md).
Licensed under MIT.
