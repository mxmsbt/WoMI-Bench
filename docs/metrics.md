# Metrics and interpretation

v0.2.0 provides diagnostics on fixed, aligned outputs. RGB is converted from uint8 to `[0,1]`. All errors are lower-is-better; PSNR is higher-is-better. Reference masks define valid pixels. No learned judge or target-dependent alignment is used.

| Measurement | Definition | Shortcut / limitation |
| --- | --- | --- |
| `rgb_mae` | Mean absolute channel error on valid pixels | Background can dominate; plausible alternative futures can be penalized |
| `rgb_psnr_capped_db` | `-10 log10(max(MSE, 1e-6))`, range 0–60 dB | Alignment sensitive; capped for finite aggregation; not perceptual quality |
| `depth_relative_error_bounded` | Mean `min(abs(pred-target)/target, 1)`; nonpositive predictions get 1 | Camera-Z meters, no scale fitting; caps large errors, does not measure complete surfaces |
| `revisit_mae` | First/last predicted return-view MAE on common valid mask | Frozen images can score perfectly; always inspect target agreement |
| `edit_region_mae` | MAE inside requested edit region | Specified appearance target, not general semantic edit quality |
| `preserved_region_mae` | MAE outside edit region, averaged separately | Fixed-camera appearance preservation, not 3D edit persistence |
| `foreground_mae` | MAE on independently annotated valid foreground | Depends on annotation; not force/contact correctness |
| `temporal_delta_mae` | Mean `abs((P[t]-P[t-1])-(Y[t]-Y[t-1]))/2` on common valid pixels | Time steps must match; not physical understanding |

## Failure and aggregation

Each assigned case remains in the denominator. Missing, failed or invalid predictions receive error 1 and PSNR 0. These are explicit penalties, not an estimate of an unseen output. Target/integrity failures abort the campaign; investigate them separately.

Average pixels/frames within each case, cases within each world and task, then equally across worlds. More camera views do not buy more weight. Tasks remain separate; there is no cross-track aggregate.

Intervals use a percentile bootstrap over world means: 2,000 resamples, seed 1729, 2.5th and 97.5th percentiles. With fewer than two worlds the interval is null. They are **descriptive and uncorrected**, not confirmatory significance tests. Eight analytic worlds are software calibration, not population evidence.

`womi compare` requires matching dataset, target index, evaluator source, scope and world coverage. It bootstraps paired per-world differences (`first - second`). Negative favors the first system on errors; positive favors it on PSNR. Compare replayed reports; checksums alone do not authenticate results.

## Stronger research campaigns

Predeclare effect sizes, sample size, budgets, attempts, endpoints and multiple-comparison corrections. Add disjoint assets/captures, longer horizons, strong controls, independent targets and held-out human or physical checks of metric validity. For multimodal futures, define a sampling/distributional evaluation rather than assuming one RGB reference is the only possible outcome.

To claim useful synthetic training data, train downstream systems under matched data/compute budgets and test transfer on held-out real tasks. Reconstruction error and attractive renders do not establish transfer.
