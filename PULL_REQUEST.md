Keep the two public imports of `ErealAddIInf` and replace its 43 private imports with `Mathlib.Data.EReal.Operations`. Subtracting a finite real is left adjoint to adding it on the extended reals. Applying `GaloisConnection.u_iInf` replaces the two case splits at infinity and the hand-written order argument.

| Lean / Mathlib | Direct imports | Transitive imports | Public `.olean` (bytes) | Median target rebuild |
|---|---:|---:|---:|---:|
| 4.37.0-rc1 / `31ce06e` | 45 → 3 | 3,696 → 1,310 | 126,136 → 119,216 | 53.1 s → 43.4 s |
| 4.36.0 / `fc4f59e` | 45 → 3 | 3,693 → 1,309 | 124,696 → 117,776 | 623.0 s → 72.2 s |

Each pair is a forced `lake --no-cache build +Formalism.LocalToGlobal.ProjectiveLattices.ErealAddIInf` with existing dependencies, one Lean thread and one pinned CPU. Only the target trace was removed. Run order alternated between pairs. Transitive counts are the entries in Lake’s `importArts` map. The source file was identical at both base commits, `d27f7134` and `4f5b851c`.

- 4.37.0-rc1 / `31ce06e` took 60.3 → 26.3 s, 32.2 → 45.3 s, 45.8 → 74.3 s, 281.0 → 41.4 s.
- 4.36.0 / `fc4f59e` took 673.5 → 40.3 s, 572.6 → 104.0 s.

Wall times varied on the shared host. Both runs improved on the requested 4.36 pin. On upstream’s 4.37 pin the revision was faster in two of four pairs. The single theorem used 970 → 200 elaboration heartbeats on 4.37, measured with `#count_heartbeats` in the same import environment for each proof.

The changed module passed `lake build` on both pins. A comparison of the two sets of `.olean` files matched names, universe parameters and types for all 17 public declarations on each pin, as well as the bodies of all public definitions. The direct importer `IntDerApply` built on upstream’s pin, and `leanchecker` replayed the changed module. `lake build Challenge` passed using its cached artifact after matching its source, build settings and all 9,133 import records.

For the changed theorem, stock Comparator reported success for statement comparison and the permitted-axiom check. Its kernel subprocesses could not start because this host denies Bubblewrap’s network-namespace setup. Lean’s default kernel, Lean paranoid and nanoda each accepted the same revised export when run directly.

The patch merges cleanly with upstream `0e40c084`. Full `lake build Main Challenge` and project-wide `lake comparator` remain pending.
