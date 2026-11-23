# Polynomial-evaluation changed-unit verification

| Metric | Before | After |
|---|---:|---:|
| Median command seconds | 20.545 | 16.442 |
| direct_imports | 8 | 5 |
| source_mathlib_closure | 8713 | 8713 |
| Unit olean bytes | 500312 | 459424 |
| Unit private bytes | 1133968 | 980752 |
| Unit server bytes | 23408 | 7848 |

One warm-up per revision, then three pairs in AB, BA, AB order. Stock Lean, one thread. Both consumers replayed with stock leanchecker.

**Bounded changed-unit diagnostic only. Full `lake build Main Challenge` and `lake comparator`: NOT RUN.**
