# LamCopy benchmark evidence

## Status

Scoped source verification passed on both requested Lean 4.36.0 and merged-main Lean 4.37.0-rc1. Full `lake build Main Challenge` and `lake comparator` gates have not been run. This record is not an end-to-end proof verdict.

## Source and evidence identities

| Lane | Base source | Candidate source | Successful run | GitHub artifact | ZIP SHA-256 |
|---|---|---|---|---:|---|
| 4.36.0 | `c592e91eb8f41bfd149227c09460fae0c17bf3c5` | `acb08b84d95e0f40647acb5bfdfab6696365cbf0` | [45131872717](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45131872717) | 14800656335 | `4a84d61128a92eac395160ae134f37a1f88032152f53891b73c654ae21a2e08f` |
| 4.37.0-rc1 | `9c9f665ed79ce0fa8da61bd803b7a4bf1ad62ed0` | `4902a2ece0f1b8058752b5a4d3b853e675de52f0` | [45134044951](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45134044951) | 14800965016 | `bbf3d99451570c7c0d140309bb6c5f5f4c9eaa79c4d55f0861c3cbbda77b04f1` |

The downloaded ZIP digests were checked against GitHub's artifact metadata before reading results. Original result records are preserved as [lean-4.36-result.json](lean-4.36-result.json) and [lean-4.37-result.json](lean-4.37-result.json). [benchmark-summary.json](benchmark-summary.json) adds rounded module-job durations extracted from the target logs.

## Review description

## Why

`LamCopy.lam_copy` imports the ring-spectrum proof module to obtain two transport structures. Extracting those structures narrows the environment needed to rebuild LamCopy. This also simplifies the dependent elimination proof by removing duplicate facts.

## Changes

- Move `CopyAll` and `SameFrame`, with their declaration text, namespace, fields and attributes preserved, into `IwasawaDecomposition/CopyAll.lean`. The existing ring-spectrum module publicly reexports them.
- Give LamCopy three explicit public project imports. Remove `PlaceModelImp`, 19 unused Mathlib tactic-extension imports, the already publicly reachable `Chebyshev` import, and two unused namespace openings.
- Name every required field in the existing `h.cp.set` destructuring, remove ten repeated projections, and clear `h` and `ι` before the dependent eliminations. The subsequent substitutions and final construction are preserved.

The `lam_copy` statement is unchanged. This PR changes only three Lean files. It introduces no `sorry`, `admit`, axiom or unsafe feature, and changes no heartbeat/recursion limits, toolchain configuration, or dependency pins. `src/Challenge.lean`, `src/Statements.lean`, `comparator.json` and the other protected challenge/export inputs are byte-identical to the base.

## Verification

**Draft: all touched-module builds passed; `lake build Main Challenge` and `lake comparator` remain NOT RUN.** The full-project gates must pass before this is ready to merge. Hosted comparator rehearsals are not counted as a full comparator result.

Both runs freshly rebuilt `CopyAll`, `RingSpecNormalisedCharacterEq`, `LamCopy` and the immediate consumer `ExportTieMove` using explicit stock `lake --rehash build +<Module>` targets. All 11 measured invocations per lane exited 0; each log names exactly one freshly `Built` target and contains no `Restored` target. Target outputs were deleted before every measurement, with `LAKE_ARTIFACT_CACHE=false`, `LAKE_RESTORE_ARTIFACTS=false`, and `LEAN_ABORT_ON_PANIC=1` inside the offline build sandbox.

Each before/after pair used one Ubuntu 22.04 GitHub-hosted runner (4 CPUs, approximately 15.6 GiB RAM), one Lean thread and verified cached dependencies. Times below include the complete Lake invocation. LamCopy uses the median of three repetitions; other targets have one observation. Baseline ran before candidate, without randomized alternation. Project ancestors exclude the target and external packages.

### Current main after #185: Lean 4.37.0-rc1

Base `9c9f665ed79ce0fa8da61bd803b7a4bf1ad62ed0`; candidate `4902a2ece0f1b8058752b5a4d3b853e675de52f0`; Mathlib `31ce06eaadf4a200c0e1407c5f10953cf606b8f8`.

| Module | Build seconds | Direct imports | Project ancestors | `.olean` bytes |
|---|---:|---:|---:|---:|
| `LamCopy` | 87.78 → 72.57 | 37 → 16 | 2,144 → 1,782 | 26,688 → 23,752 |
| `RingSpecNormalisedCharacterEq` | 41.37 → 45.77 | 35 → 35 | 1,913 → 1,914 | 470,136 → 412,168 |
| `CopyAll` | new → 30.03 | new → 1 | new → 1,779 | new → 96,768 |
| `ExportTieMove` | 39.87 → 39.27 | 43 → 43 | 3,593 → 3,594 | 360,712 → 360,712 |

LamCopy's median wall time improves **17.3%**. Individual times: **85.48, 88.07, 87.78 → 72.57, 71.68, 72.77 s**. Lake's rounded module-job median is **59 → 46 s**; this includes import loading and does not isolate the theorem's tactic execution.

[Successful 4.37 run and logs](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45134044951).

### Requested Lean 4.36.0 pin

The corresponding pinned-version change is preserved separately at `acb08b84d95e0f40647acb5bfdfab6696365cbf0`, based on `c592e91eb8f41bfd149227c09460fae0c17bf3c5`, with Mathlib `fc4f59e577feb1a4956671bc04ac18aaaf8cd842`. It contains the same structure extraction and proof cleanup; the 4.37-specific private-import pruning is confined to this PR.

| Module | Build seconds | Direct imports | Project ancestors | `.olean` bytes |
|---|---:|---:|---:|---:|
| `LamCopy` | 156.83 → 98.27 | 3 → 3 | 13,144 → 3,259 | 20,488 → 20,536 |
| `RingSpecNormalisedCharacterEq` | 127.83 → 108.78 | 5 → 5 | 13,143 → 13,144 | 461,512 → 404,496 |
| `CopyAll` | new → 56.17 | new → 1 | new → 3,256 | new → 95,600 |
| `ExportTieMove` | 109.28 → 107.28 | 11 → 11 | 13,570 → 13,571 | 355,088 → 355,088 |

LamCopy's median wall time improves **37.3%**. Individual times: **159.03, 156.33, 156.83 → 102.27, 96.98, 98.27 s**. Lake's rounded module-job median is **64 → 48 s**.

[Successful 4.36 run and logs](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45131872717).

## Tradeoffs and remaining gates

The new interface module increases the three touched modules' combined `.olean` size by **35,864 B on 4.37** and **38,632 B on 4.36**. The full consumer still needs the ring-spectrum environment, so its project dependency closure increases by one module. The measured benefit is to LamCopy's own imports and rebuild cost; no full-project build-time or aggregate size improvement is claimed.

RingSpec's single 4.37 wall-time observation increased from 41.37 to 45.77 s; the table retains that result. Other single-sample changes are not treated as established speedups.

- [x] Fresh builds of all three touched modules and `ExportTieMove` on both toolchain pins.
- [x] Exact source hashes, protected-file equality, official Lean commits, and locked package sources verified.
- [ ] `lake build Main Challenge` for the complete proposed merge.
- [ ] `lake comparator` for the complete proposed merge.

Benchmark infrastructure and evidence are on separate fork verification branches, outside this source PR. The upstream full-build workflow is currently being skipped, and the connected account cannot dispatch the maintainer-only full build.

Related: #178; based on merged #185.

