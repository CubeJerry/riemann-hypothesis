# Verified improvements to condensed main

26 November 2026. Ten independent pull requests against `leanprover-community/riemann-hypothesis:main`, using Lean 4.35.0 and the repository's pinned Mathlib revision.

## Results

Every submitted change passed its explicit `lake build` target list. The successful checks cover **51 named targets** across the ten changes. SHA-256 hashes for all **22 changed source files** match the files recorded by those successful builds. No sorry warning was reported in the successful case results, and no compiler warning was reported for a changed file.

The verification script resets to the pinned upstream base before each case, restores only that case's changed source files, checks the exact changed-file set, and invokes `lake build` with the listed module targets. It does not invoke a repository-wide build. Verification workflows and scripts are confined to fork verification branches and are absent from the source PRs.

Each row below refers to the successful final version. Exploratory runs also contain candidates subsequently repaired or excluded, so an exploratory run's aggregate status can be red even when the linked case passed. The JSON record identifies the exact successful source commit, source hashes, targets and job for every submitted PR.

| PR | Change | Target checks | Upstream CI at status check |
|---|---|---:|---|
| [#5694](https://github.com/leanprover-community/riemann-hypothesis/pull/5694) | Replace the blanket Lib.Base dependency with two focused Mathlib imports in grid-path combinatorics. | 3 | Passed |
| [#5720](https://github.com/leanprover-community/riemann-hypothesis/pull/5720) | Remove the discrete-series dependency from residue-sum identities. | 2 | Passed |
| [#5766](https://github.com/leanprover-community/riemann-hypothesis/pull/5766) | Use MvPolynomial.pderiv_comm and remove the duplicated project theorem. | 6 | Running |
| [#5767](https://github.com/leanprover-community/riemann-hypothesis/pull/5767) | Use PowerSeries.constantCoeff_subst_of_constantCoeff_zero, making former implicit simp uses explicit. | 5 | Running |
| [#5783](https://github.com/leanprover-community/riemann-hypothesis/pull/5783) | Remove unused complex-theta data from near-identity matrix estimates. | 4 | Running |
| [#5785](https://github.com/leanprover-community/riemann-hypothesis/pull/5785) | Remove three unused self-conjugate-prime lemmas and their obsolete documentation reference. | 3 | Running |
| [#5788](https://github.com/leanprover-community/riemann-hypothesis/pull/5788) | Replace the blanket Lib.Base dependency with eleven focused Mathlib imports for the Pieri cone formulas. | 2 | Passed |
| [#5789](https://github.com/leanprover-community/riemann-hypothesis/pull/5789) | Move generic matrix definitions to IntegralLattices so HermiteForm no longer imports the adelic Witt theorem. | 19 | Running |
| [#5790](https://github.com/leanprover-community/riemann-hypothesis/pull/5790) | Replace the finite-sum induction with map_sum and inline a single-use primitive-character helper. | 1 | Running |
| [#5810](https://github.com/leanprover-community/riemann-hypothesis/pull/5810) | Place taylorAtZero with general Taylor theory and make the true integral and Fourier dependencies explicit. | 6 | Running |

## Dependency reductions

Counts below include transitive project modules, excluding the module itself and external packages. These are import-graph counts, not elapsed-time benchmarks.

| Module | Before | After | Removed dependencies |
|---|---:|---:|---:|
| `Lib.General.Algebra.ResidueSums` | 9 | 2 | 7 |
| `Lib.General.LinearAlgebra.MatricesNearIdentity` | 16 | 9 | 7 |
| `Lib.General.LinearAlgebra.HermiteForm` | 27 | 6 | 21 |
| `Lib.General.Analysis.MeanValueAndTaylor` | 18 | 3 | 15 |

`GridPaths` and `PieriCone` also remove their blanket `Lib.Base` imports and import two and eleven focused Mathlib modules respectively. Their declarations remain public, their definitions remain transparent, and their proof bodies are unchanged.

## Exact successful checks

### #5694: perf: narrow the imports of grid path combinatorics

- Source commit: `258ca82a4502566724e4a26973388e8c66f48187`
- Upstream base: `2fc633272442a664eb260b76151c6e4e474c6b0b`
- [Successful case evidence](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45734140787/job/139623158263)

```sh
lake build New.Determinant.AuxiliaryForms.GridPaths New.Determinant.Chain.Moduli New.Determinant.AuxiliaryForms.PathData
```

### #5720: refactor: decouple residue sums from discrete series

- Source commit: `576c958dd023037545a2a03a4cc53005ada5226c`
- Upstream base: `2fc633272442a664eb260b76151c6e4e474c6b0b`
- [Successful case evidence](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45734140787/job/139623158263)

```sh
lake build Lib.General.Algebra.ResidueSums New.Appendix.DiscreteSeries.StationaryPosition
```

### #5766: refactor: use Mathlib for commuting partial derivatives

- Source commit: `57e024e620ef60b6597ffcc9e8847197d1b149d3`
- Upstream base: `2fc633272442a664eb260b76151c6e4e474c6b0b`
- [Successful case evidence](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45734140787/job/139623158263)

```sh
lake build Lib.General.Algebra.MultivariatePolynomials Lib.SiegelWeil.Reproduction Lib.DiscreteSeries.Theta.LocalCorrespondence Lib.DiscreteSeries.Theta.FockDualPair Lib.DiscreteSeries.Theta.FockJointHarmonics Lib.Weil.Fock.OscillatorPair
```

### #5767: refactor: reuse Mathlib's substitution constant coefficient lemma

- Source commit: `b64fb25bfb81d08e2fda2c2756551320ec23d5b3`
- Upstream base: `2fc633272442a664eb260b76151c6e4e474c6b0b`
- [Successful case evidence](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45734140787/job/139623158263)

```sh
lake build Lib.General.Algebra.IntegralPowerSeries Lib.CM.FormalGroup.IntegralParameter New.Derivatives.Vacuum.JetIntegrality New.Derivatives.Sharpness.Couplings New.Derivatives.Sharpness.LeastValuation
```

### #5783: refactor: remove the theta dependency from matrix estimates

- Source commit: `93f6db722e93ccb5635b6cddbc3f4ba62dbed764`
- Upstream base: `2fc633272442a664eb260b76151c6e4e474c6b0b`
- [Successful case evidence](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45734140787/job/139623158263)

```sh
lake build Lib.General.LinearAlgebra.MatricesNearIdentity New.Appendix.DiscreteSeries.SteepParameters New.Appendix.DiscreteSeries.MinorSecondOrder Lib.Weil.Fock.PolynomialVectors
```

### #5785: refactor: remove unused self-conjugate prime lemmas

- Source commit: `d0848dc4e9076ee90fa5483a8c262ef38c2d96ba`
- Upstream base: `2fc633272442a664eb260b76151c6e4e474c6b0b`
- [Successful case evidence](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45734140787/job/139623158263)

```sh
lake build New.Reduction.Data.FieldsAndPlaces New.Derivatives.Field.PrimeDecomposition New.Derivatives.Field.WeilData
```

### #5788: perf: narrow imports of Pieri cone volume formulas

- Source commit: `f47fb9760e8841a79b05a1a7f70006f6ef35797a`
- Upstream base: `e063a923620ee7787b4a1270421478645bf66bdb`
- [Successful case evidence](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45736098093/job/139629622434)

```sh
lake build New.UpperBound.ElementaryDivisors.PieriCone New.UpperBound.ElementaryDivisors.DefectCount
```

### #5789: refactor: separate primitive matrices from the adelic Witt theorem

- Source commit: `7dcf74b9bc3556e31f411b764efc31804146683c`
- Upstream base: `e063a923620ee7787b4a1270421478645bf66bdb`
- [Successful case evidence](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45736098093/job/139629621893)

```sh
lake build Lib.General.LinearAlgebra.IntegralLattices Lib.Adelic.Witt.WittTheorem Lib.General.LinearAlgebra.HermiteForm Lib.LocalGL.Iwahori.ParahoricStructure Lib.PadicHodge.Crystalline.HodgeTateJumps New.UpperBound.ElementaryDivisors.ElementaryDivisorTheorem Lib.PadicHodge.RadiusLemma Lib.PadicHodge.BlochKato Lib.Cohomology.WoodsHole Lib.PadicComparison.Crystalline.ComparisonMap Lib.PadicComparison.HodgeTate.GaloisWeight Lib.PadicComparison.Primitive.ComparisonTheorem Lib.PadicComparison.Primitive.Periods Lib.PadicHodge.Kisin.KummerChartDeRham Lib.PadicHodge.Kisin.PeriodMatrixFrame Lib.General.Algebra.BlockFittingBound Lib.General.Algebra.SharpMinors Lib.Shimura.CongruenceRelation.EichlerShimura Lib.General.LinearAlgebra.PartnerAlgebra
```

### #5790: refactor: simplify finite additive character proofs

- Source commit: `0300cdf5d83671a7f13ac9a7c38a639bb59bf5a9`
- Upstream base: `e063a923620ee7787b4a1270421478645bf66bdb`
- [Successful case evidence](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45737454025/job/139634010598)

```sh
lake build Lib.General.Analysis.FiniteFourier
```

### #5810: refactor: move Taylor series to general analysis

- Source commit: `de84e853470e8aea8d6ed2d63ddf3a1ff4253610`
- Upstream base: `e063a923620ee7787b4a1270421478645bf66bdb`
- [Successful case evidence](https://github.com/CubeJerry/riemann-hypothesis/actions/runs/45738794898/job/139638411993)

```sh
lake build Lib.General.Analysis.MeanValueAndTaylor Lib.CM.Sigma.Basic Lib.Adelic.Witt.SmoothWitt Lib.Weil.MixedModel.FockSections Lib.DiscreteSeries.Holomorphic.HighestVectorExtension Lib.CM.Sigma.ThetaSections
```

## Selection and scope

Three deletion candidates were excluded because existing PRs #5668, #5671 and #5697 already covered them. A holomorphic-integration import reduction was excluded after compilation exposed required implicit dependencies. The additive-character and Taylor changes were repaired and recompiled before submission.

The submitted patches do not change challenge, statement or comparator files and do not add sorry, admit, axioms or unsafe declarations. They preserve the statements of retained theorems. The PR descriptions explain the code changes without self-reported build or benchmark results.

See [the machine-readable verification record](optimizations-2026-11-26.json) for file hashes and complete result metadata.
