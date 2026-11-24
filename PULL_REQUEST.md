## Draft pull request

[Open the prefilled upstream PR form](https://github.com/leanprover-community/riemann-hypothesis/compare/main...CubeJerry:riemann-hypothesis:perf/ereal-infimum?expand=1&title=perf%3A%20prune%20imports%20for%20graded%20valuations%20on%20monoid%20algebras&body=Keep%20the%20two%20public%20imports%20of%20%60ErealAddIInf%60%20and%20replace%20its%2043%20private%20imports%20with%20%60Mathlib.Data.EReal.Operations%60.%20Adding%20a%20finite%20real%20is%20right%20adjoint%20to%20subtracting%20it%20on%20%60EReal%60%2C%20so%20%60GaloisConnection.u_iInf%60%20replaces%20the%20two%20case%20splits%20at%20infinity%20in%20%60ereal_add_iInf%60.%0A%0A%7C%20Lean%20%2F%20Mathlib%20%7C%20Direct%20imports%20%7C%20Transitive%20imports%20%7C%20Public%20%60.olean%60%20%28bytes%29%20%7C%20Median%20target%20rebuild%20%7C%0A%7C---%7C---%3A%7C---%3A%7C---%3A%7C---%3A%7C%0A%7C%204.37.0-rc1%20%2F%20%6031ce06e%60%20%7C%2045%20%E2%86%92%203%20%7C%203%2C696%20%E2%86%92%201%2C310%20%7C%20126%2C136%20%E2%86%92%20119%2C216%20%7C%2053.1%20s%20%E2%86%92%2043.4%20s%20%7C%0A%7C%204.36.0%20%2F%20%60fc4f59e%60%20%7C%2045%20%E2%86%92%203%20%7C%203%2C693%20%E2%86%92%201%2C309%20%7C%20124%2C696%20%E2%86%92%20117%2C776%20%7C%20623.0%20s%20%E2%86%92%2072.2%20s%20%7C%0A%0AEach%20pair%20forced%20the%20target%20to%20rebuild%20with%20prebuilt%20dependencies%2C%20one%20CPU%20and%20one%20Lean%20thread.%20Revision%20order%20alternated.%20The%20change%20was%20faster%20in%20two%20of%20four%20pairs%20on%204.37%20and%20both%20pairs%20on%204.36.%20Transitive%20counts%20come%20from%20Lake%E2%80%99s%20%60importArts%60.%20On%204.37%20the%20proof%20itself%20took%20970%20%E2%86%92%20200%20elaboration%20heartbeats%20under%20identical%20imports.). Select **Create draft pull request** while the repository-wide build is pending.

## Benchmarks and verification

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

The branch includes upstream `64970dc6`. The repository-wide `lake build`, full `lake build Main Challenge` and project-wide `lake comparator` remain pending. The host has a 20 GiB workspace. The upstream contributor guide calls for 250 GiB of free SSD space.
