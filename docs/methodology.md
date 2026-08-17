# Measurement methodology

## Runtime and throughput

A monotonic clock measures wall time from process creation to exit detection.
This includes startup, dynamic loading, workload execution, output capture,
and scheduling overhead. It does not isolate an inner loop or CPU time.
Use workloads long enough for startup costs to be small; warmups do not remove
process startup because each trial launches a fresh process.

For each round, CoreLens shuffles the variants with a reproducible seed and
measures each once. The preceding warmup rounds are discarded. Measured
rounds form paired observations for comparisons. The median of per-round
baseline/candidate ratios is the reported speedup. A deterministic percentile
bootstrap resamples those ratios 2,000 times and reports a 95% interval.
Single-binary reports contain distribution statistics and relative median
absolute deviation. Throughput is supplied work units divided by median
whole-process runtime.

These intervals describe observed sampling variability, not systematic bias,
thermal drift, frequency differences, compiler semantics, or correctness.
Very few repeats can produce unstable or narrow intervals. Prefer at least
9 runs, larger representative inputs, and repeat experiments independently.
Record background activity and power policy. `--cpu` uses Linux taskset with
an allowed CPU index; CoreLens records the parent's available affinity mask.
The reported governor for CPU 0 may differ from the pinned CPU's policy.

## Hardware counters

`perf stat` requests `cycles`, `instructions`, `cache-references`,
`cache-misses`, `branches`, and `branch-misses`. These are generic hardware
events with CPU-specific mappings. Perf's reported values may be scaled when
events are multiplexed; running percentages are retained per event and the
minimum observed percentage appears in the summary. Ratios formed from
separately scaled events can be noisy. Inspect raw results before interpreting
small differences. Large miss ratios are prompts for experiments, not causal
proof of a bottleneck.

Counter trials follow the timing trials and never contribute to runtime
speedups or throughput. Counter differences compare medians of available
values; partial availability is explicit in each summary. Unsupported,
uncounted, malformed, and missing events remain nullable. Requesting perf
with no usable counters fails the Python benchmark instead of silently
switching to timing. Native output preserves perf stderr for diagnosis.

On restricted hosts, `perf_event_paranoid`, permissions, container policies,
or unavailable virtualized PMUs may block events. Request access using your
system's administrative process. CoreLens does not modify those settings,
retry with elevated privileges, or invent counter values.

## Assembly and optimization advice

Assembly instruction sites are counted per decoded function. Heuristics flag
potentially expensive division, conditional branches, calls, stack operands,
and scalar floating point arithmetic. They do not measure execution frequency,
latency, spills, or branch outcomes. Stack operations can be intentional;
scalar instructions can be required by dependencies. Inlining can remove a
function from disassembly, and whole-binary counts include runtime code.

LLVM optimization records explain actual compiler decisions such as
vectorization or inlining. Correlate records, filtered assembly, counter
changes, and runtime on the same source and input. Do not accept unsafe
arithmetic transformations or relaxed floating point semantics based solely
on a faster stdout-compatible trial.

## Output validation

Every measured and warmup invocation must exit successfully and produce the
same exact stdout bytes across variants. Output capture is bounded; truncated
stdout/stderr causes rejection. This is suited to deterministic checksums.
Programs that print timings, addresses, random data, or progress with varying
order need a deterministic benchmark wrapper. Output agreement does not
validate file writes, network effects, floating point tolerances, or unseen
inputs. Those require workload-specific correctness checks.
