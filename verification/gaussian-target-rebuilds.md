# Tate thesis Gaussian rebuilds

PR [leanprover-community/riemann-hypothesis#964](https://github.com/leanprover-community/riemann-hypothesis/pull/964) compares `d27f7134` to `12d4b9d7`. Lean `v4.37.0-rc1` and Mathlib `31ce06ea` are pinned by the project.

Each row measures a single target forced to rebuild with `lake --no-cache build +GroundTheory.GlobalFields.TateThesis.<module>`, one Lean thread and dependencies built. Each Lake run reported one rebuilt target. Trial 1 used the patch first, trial 2 used the baseline first. The following table gives the medians. The host was shared and wall times varied between trials.

| Module | Lake wall (s) | CPU (s) | Direct imports | Imported modules | .olean (B) | .olean.private (B) |
|---|---:|---:|---:|---:|---:|---:|
| `Gaussian` | 125.2 → 79.4 | 55.1 → 41.2 | 50 → 7 | 3,751 → 2,935 | 51,520 → 44,672 | 431,112 → 395,576 |
| `GaussianComplex` | 144.2 → 128.1 | 69.0 → 64.7 | 52 → 2 | 3,755 → 2,945 | 112,656 → 104,248 | 676,272 → 632,272 |
| `GaussianComplexFourier` | 111.9 → 128.7 | 57.5 → 60.9 | 48 → 1 | 3,759 → 2,946 | 40,128 → 32,016 | 691,112 → 673,360 |
| `GaussianSchwartz` | 110.5 → 102.3 | 47.3 → 42.3 | 48 → 5 | 3,716 → 2,773 | 47,872 → 41,024 | 301,248 → 252,256 |

## Individual measurements

| Trial | Revision | Module | Wall (s) | User + system CPU (s) |
|---:|---|---|---:|---:|
| 1 | patch | `Gaussian` | 121.00 | 59.33 |
| 1 | patch | `GaussianComplex` | 204.48 | 102.49 |
| 1 | patch | `GaussianComplexFourier` | 203.74 | 94.88 |
| 1 | patch | `GaussianSchwartz` | 129.97 | 53.08 |
| 1 | base | `Gaussian` | 138.32 | 61.40 |
| 1 | base | `GaussianComplex` | 230.24 | 105.31 |
| 1 | base | `GaussianComplexFourier` | 160.53 | 77.79 |
| 1 | base | `GaussianSchwartz` | 160.56 | 65.90 |
| 2 | base | `Gaussian` | 112.05 | 48.79 |
| 2 | base | `GaussianComplex` | 58.23 | 32.71 |
| 2 | base | `GaussianComplexFourier` | 63.26 | 37.16 |
| 2 | base | `GaussianSchwartz` | 60.49 | 28.63 |
| 2 | patch | `Gaussian` | 37.74 | 23.13 |
| 2 | patch | `GaussianComplex` | 51.63 | 26.95 |
| 2 | patch | `GaussianComplexFourier` | 53.57 | 26.89 |
| 2 | patch | `GaussianSchwartz` | 74.64 | 31.55 |

## Additional checks

Gaussian: 16 matching declarations.  
GaussianComplex: 20 matching declarations.  
GaussianComplexFourier: 10 matching declarations.  
GaussianSchwartz: 7 matching declarations.

Ten selected proof bodies were elaborated separately with the same imports and options using `#count_heartbeats`. This excludes import and Lake overhead.

| Proof | Before | After |
|---|---:|---:|
| `fourier_realGaussian` | 354 | 276 |
| `integral_realGaussianOdd_mul_sign_mul_abs_cpow` | 2,015 | 989 |
| `complexFourier_complexGaussian_zero` | 2,913 | 1,186 |
| `integrable_norm_pow_mul_exp_neg_two_pi_mul_sq` | 987 | 619 |
| `complexGaussian_mul_zpow` | 1,381 | 1,027 |
| `cexp_neg_two_pi_norm_sq` | 254 | 86 |
| `complexFourier_pow_mul_gaussian` | 2,592 | 2,228 |
| `complexFourier_conj` | 320,951 | 320,321 |
| `one_add_pow_mul_exp_neg_pi_mul_sq_le` | 2,056 | 658 |
| `norm_iteratedFDeriv_gaussian_le` | 2,595 | 1,965 |

All 11 declarations checked with `#print axioms` used only `propext`, `Classical.choice` and `Quot.sound`.

Both downstream targets built successfully.

```text
✔ [7883/7889] Built Development.AutomorphicSpectrum.Proofs.BlockDecomposition.ExistsSchwartzPolyMulGauss (20s)
✔ [7922/7923] Built Development.AbelianVarietyTheory.Proofs.DivisorProofs.MemClosureWideGaussianMulSchwartz (64s)
Build completed successfully (7923 jobs).
```

The isolated `lake build Challenge` run exceeded six minutes on this host. The repository-wide `Main` build and comparator are deferred to upstream batch verification.
