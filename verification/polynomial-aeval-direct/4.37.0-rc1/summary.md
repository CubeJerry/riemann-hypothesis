# Polynomial-evaluation changed-unit verification

| Metric | Before | After |
|---|---:|---:|
| Median command seconds | 8.384 | 6.883 |
| direct_imports | 176 | 92 |
| source_mathlib_closure | 4031 | 4031 |
| Unit olean bytes | 531032 | 475808 |
| Unit private bytes | 1136152 | 982456 |
| Unit server bytes | 23544 | 7920 |

One warm-up per revision, then three pairs in AB, BA, AB order. Stock Lean, one thread. Both consumers replayed with stock leanchecker.

**Bounded changed-unit diagnostic only. Full `lake build Main Challenge` and `lake comparator`: NOT RUN.**
