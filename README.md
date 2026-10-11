# WoMI-Bench

**World Model Index Benchmark — measuring whether predictions describe a coherent world.**

An independent research project created and maintained by **[Maxime Sebti](https://github.com/mxmsbt)**. Open to contributions from researchers building spatial, generative and predictive models.

[Results & examples](https://mxmsbt.github.io/WoMI-Bench/) · [Quickstart](docs/quickstart.md) · [Metrics](docs/metrics.md) · [Submit a model](docs/submission.md) · [Research protocol](docs/protocol.md) · [Governance](GOVERNANCE.md)

## Why worlds need different tests

A compelling image describes an appearance. A useful world model must also predict another viewpoint, recover spatial structure, return to a consistent scene, preserve what an edit should leave alone, and anticipate what changes over time.

WoMI-Bench makes these questions explicit and their measurements replayable. The research goal is to distinguish visual plausibility from **spatial accuracy, persistence, controlled change and prediction**. Those capabilities matter for simulation, interactive creation, robotics and the generation of training data for vision systems. Claims about better training data require transfer tests on independent real tasks.

## Run it

Python 3.10+; the calibration run uses a CPU and downloads no model weights.

```bash
git clone https://github.com/mxmsbt/WoMI-Bench.git
cd WoMI-Bench
python -m venv .venv
source .venv/bin/activate
python -m pip install .
womi demo --output runs/calibration --worlds 8
```

Open `runs/calibration/last-frame/report/report.html`. Each report includes task metrics, per-world uncertainty, coverage, raw JSON/CSV and fixed-case visual comparisons. The demo produces **40 cases across eight analytic worlds**, scores three simple controls and replays every report.

**These are synthetic calibration results, not learned-model scores.** They test the evaluator, expose shortcuts and show how evidence is reported. No trained model is ranked in this release. [Dataset card](docs/data-card.md) · [Release scope](docs/release-0.2.0.md)

## Participate in the capability you support

You do not need a particular world engine or a six-operation interface. A submission can target one capability; unsupported capabilities stay unmeasured. Compatible models use the same frozen task manifest.

| Task in the executable v0.2 protocol | Required output | Current measurements |
| --- | --- | --- |
| Spatial views | RGB at declared query cameras | Pixel MAE and capped PSNR |
| Geometry | Camera-Z depth in meters at observed cameras | Bounded relative depth error; no target-fitted scale |
| Return-view persistence | RGB along a path returning to its start | Target agreement and return-view drift |
| Appearance editing | RGB after a masked appearance edit | Intended-region error and preservation error, separately |
| Dynamics | Future RGB after an observation prefix | Image, foreground and temporal-change errors |

These are transparent **diagnostics**. Pixel similarity alone is not perceptual quality or physical understanding; return-view agreement alone is not proof of retained state. Each has documented failure modes and controls. See the [metric definitions](docs/metrics.md).

Models connect through a small Python adapter or a portable prediction bundle. Output bridges cover the documented depth formats of MapAnything, Pi3/Pi3X and Depth Anything 3; they do not claim those models have been run. [Adapter guide](docs/adapters.md)

## Evidence before ranking

- Separate public observations from evaluator targets; score saved arrays without executing candidate code.
- Freeze case inventories, model revisions, permitted inputs and resource policies before a measured campaign.
- Retain every assigned case. Failed, missing and invalid predictions receive explicit worst-case diagnostic penalties.
- Average within each world, then equally across worlds. Compare systems with paired world-level uncertainty.
- Bind inputs, outputs, targets and evaluator source to content hashes. Replay measurements from the raw evidence.
- Report scope and verification status. A local hash check is not independent attestation or proof against leakage.

There is **no universal WoMI score**. Results remain a capability profile. A geometry component and an interactive world engine are different scopes; neither inherits results from the other.

The public site separates calibration controls from model submissions. Admission requires review of a campaign's evidence, licenses, attempts, compute, limitations and independent replay. Cost is unknown unless recorded; the runner's timing is not a hardware-normalized leaderboard. [Reporting contract](docs/reporting.md) · [Submission process](docs/submission.md)

## Research direction

The broader protocol defines prospective prediction before reveal: freeze a model, commit its next forecast, reveal an independently grounded outcome, then score it. It also calls for controlled interventions, longer revisits, distribution shifts and downstream transfer studies.

The executable v0.2 release implements the offline contracts above. Live forecast commitments, stateful engine qualification, large real-world datasets and validated perceptual/physics measures are separate research milestones, not inferred from calibration success. [Roadmap and adoption criteria](docs/roadmap.md)

Studies using [WorldScore](https://haoyi-duan.github.io/WorldScore/) or [Physics-IQ](https://github.com/google-deepmind/physics-IQ-benchmark) must retain their original names, versions, licenses and scoring definitions. WoMI-Bench does not rebrand their results or imply their authors' endorsement.

## Contribute and cite

The most useful contributions are a reproducible model submission, a licensed grounded dataset, a metric-validation study, or a demonstrated shortcut. Protocol changes happen through public issues and versioned releases. [Contributing](CONTRIBUTING.md) · [Governance and conflicts](GOVERNANCE.md)

```bibtex
@software{sebti2026womibench,
  author = {Sebti, Maxime},
  title = {{WoMI-Bench}: World Model Index Benchmark},
  year = {2026},
  version = {0.2.0},
  url = {https://github.com/mxmsbt/WoMI-Bench}
}
```

[CITATION.cff](CITATION.cff) · [MIT License](LICENSE) · [Upstream attribution](NOTICE)
