# Workload guide

| Source | Input | Purpose | Output |
| --- | --- | --- | --- |
| `arithmetic.cpp` | iteration count, default 10,000,000 | Integer division and strength reduction | Unsigned arithmetic checksum |
| `vector.cpp` | element count, default 2,000,000 | Integer vectorization and dead-store removal | Sum of final output vector |
| `cache.cpp` | matrix side, optional `rows` | Column versus row access locality | Same sum for either traversal |
| `branches.cpp` | element count, optional `sorted` | Data ordering and branch lowering | Same threshold sum for either order |
| `c_sum.c` | iteration count, default 10,000,000 | C11 compilation and integer loop optimization | Unsigned arithmetic checksum |

Workload allocation, initialization, sorting, and checksums are included in
process runtime. Sorting may cost more than it saves: measure the whole task.
Clang may vectorize or remove branches, or eliminate overwritten passes; inspect
assembly/records before attributing a result to a particular CPU behavior.
Integer overflow uses unsigned types and defined wrapping semantics.

Compare a compiler change with:

```sh
corelens experiment workloads/vector.cpp --candidate-flag=-O3 --arg 2000000 --units 64000000
```

`--units` is a logical work count; optimization can eliminate source operations,
so it is not an executed instruction count. For source experiments, preserve
the same logical output and supplied arguments. To investigate locality,
change the cache workload's default traversal in a candidate copy, then use
`--candidate-source` with the same matrix size. The `rows`/`sorted` arguments
allow standalone trials via `bench`; use the resulting JSON to compare their
whole-task cost. Keep binary and source manifests with results.
