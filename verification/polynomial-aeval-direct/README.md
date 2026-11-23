# Polynomial evaluation cleanup: verification evidence

**Scoped verification passed on both pins. Full `lake build Main Challenge` and `lake comparator` were not run.**

This evidence is kept on a fork-only verification branch. It is not part of the four-file source pull request.

[Successful GitHub Actions run](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45172602746), harness commit `6385bbd519cf6309cba89e4413e5f19b795dcddd`.
The workflow and script are in `.github/workflows/polynomial-aeval-direct.yml` and `.github/scripts/polynomial-aeval-direct.py` at that commit.

## Results

Times are whole-command wall seconds for rebuilding the affected unit, including Lake traversal and `--rehash`, with unchanged dependencies warm. Each lane has one warm-up per variant followed by three measured pairs in AB, BA, AB order. The same two-root build command rebuilds four modules before and two after. Lean uses one thread on GitHub-hosted Ubuntu 24.04. This does not measure isolated tactic execution or establish a whole-project speedup.

| Metric | Lean 4.36.0 before | After | Lean 4.37.0-rc1 before | After |
|---|---:|---:|---:|---:|
| Median wall seconds | 20.545 | 16.442 | 8.384 | 6.883 |
| Affected compilation units | 4 | 2 | 4 | 2 |
| Direct import entries in affected unit | 8 | 5 | 176 | 92 |
| Distinct reachable Mathlib source modules | 8,713 | 8,713 | 4,031 | 4,031 |
| .olean bytes | 500,312 | 459,424 | 531,032 | 475,808 |
| .olean.private bytes | 1,133,968 | 980,752 | 1,136,152 | 982,456 |
| .olean.server bytes | 23,408 | 7,848 | 23,544 | 7,920 |

At current upstream, 83 of the 84 removed import entries belong to the deleted helper files. The surviving callers have 93 imports before and 92 after. The combined Mathlib closure is unchanged on both pins.

## Immutable inputs and samples

### Lean 4.36.0

- Base: `c592e91eb8f41bfd149227c09460fae0c17bf3c5`
- Candidate: `6e503772f36133839159fd849a0b1e2b4f6d552e`
- Mathlib: `fc4f59e577feb1a4956671bc04ac18aaaf8cd842`
- Lean: `Lean (version 4.36.0, x86_64-unknown-linux-gnu, commit 611c117bfaf7b7ae1cfcf246ce6fba31e8f509e9, Release)`
- Measured before seconds: `[20.757, 20.448, 20.545]`
- Measured after seconds: `[16.642, 16.434, 16.442]`
- Median reduction: `19.97%`
- Restored unchanged project dependencies: `311`

### Lean 4.37.0-rc1

- Base: `c900e67c2fcd1fdb041685820bbd2b867fbc5a4b`
- Candidate: `5de976dfd04ebedcac15ba640c700116c536e9ca`
- Mathlib: `31ce06eaadf4a200c0e1407c5f10953cf606b8f8`
- Lean: `Lean (version 4.37.0-rc1, x86_64-unknown-linux-gnu, commit 0b77e12952ad39077d80d8bd6b66d601f225c321, Release)`
- Measured before seconds: `[8.382, 8.389, 8.384]`
- Measured after seconds: `[6.988, 6.881, 6.883]`
- Median reduction: `17.90%`
- Restored unchanged project dependencies: `158`

## Checks and reproduction

```bash
lake --no-cache --rehash build \
  +ReciprocityTheory.ReductiveGroups.DiscreteSeries.TensorRepresentations.DecompA \
  +Formalism.SharpRestriction.LevelLetterCocycles.DvrLatticeRank.AevalMemOfStable

lake env leanchecker --verbose \
  ReciprocityTheory.ReductiveGroups.DiscreteSeries.TensorRepresentations.DecompA
lake env leanchecker --verbose \
  Formalism.SharpRestriction.LevelLetterCocycles.DvrLatticeRank.AevalMemOfStable
```

The harness removes all affected outputs and traces before each build. Every active affected module must appear as freshly built. Measured samples reject unexpected dependency builds and artifact restoration. Only unchanged ancestor artifacts are restored, with pinned manifests and archive SHA-256 checks plus source-blob equality across the cache producer, baseline, and candidate. Stock Lake validates their traces. Official Mathlib caches supply unchanged dependency artifacts.

Both lanes passed exact compiled public-interface comparison: 19 declarations in `DecompA`, 11 in `AevalMemOfStable`, with identical names, universe parameters and types. Both versions of the three rewritten theorems depend only on `propext`, `Classical.choice`, and `Quot.sound`. Both final consumers passed stock `leanchecker` replay. All package heads match their manifests. Protected files and build configuration are byte-identical between each baseline and candidate.

The original `Bl.PowerApplication.goal1` and `Bl.PowerMembership.goal1` declarations and their private induction helpers are intentionally removed. No tracked repository reference to either deleted helper module remains. This is not a claim that the deleted modules' public interfaces are preserved.

Per-lane directories preserve all textual files at the root of the uploaded artifact: build logs, raw samples, source diff, dependency receipts, identities, summaries, safe interface probes and their results. Source snapshots and baseline public `.olean` binaries remain in the original ZIP artifacts; the source snapshots are also recoverable from the immutable input commits. `provenance.json` records original ZIP digests and SHA-256 hashes of the preserved text files. The original uploaded artifacts expire after 14 days; this committed evidence does not rely on their retention.

**Remaining gates:** full candidate `lake build Main Challenge` and `lake comparator`. The source PR must remain draft until those pass. The scoped results do not attest to full-project verification or establish a new claim about the Riemann Hypothesis.
