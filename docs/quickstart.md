# Quickstart

The evaluator is a small CPU package. Candidate model inference can happen elsewhere. No model weights, API credentials or GPU are required for the development example.

```bash
git clone https://github.com/mxmsbt/WoMI-Bench.git
cd WoMI-Bench
python -m venv .venv
source .venv/bin/activate
python -m pip install .
womi demo --output runs/calibration --worlds 8
```

The output directory must be new. The command makes public inputs and separate targets, runs three deterministic diagnostic controls, measures them, replays the measurements and writes a paired comparison. Open `runs/calibration/last-frame/report/report.html` directly in a browser.

## Individual steps

```bash
womi validate --dataset runs/calibration/dataset/public/manifest.json
womi predict --dataset runs/calibration/dataset/public/manifest.json \
  --adapter last-frame --name Copy --revision 0.2.0 --kind control \
  --output runs/copy
womi evaluate --dataset runs/calibration/dataset/public/manifest.json \
  --targets runs/calibration/dataset/targets/targets.json \
  --submission runs/copy/submission.json --output runs/copy-report
womi replay --dataset runs/calibration/dataset/public/manifest.json \
  --targets runs/calibration/dataset/targets/targets.json \
  --submission runs/copy/submission.json --report runs/copy-report/report.json
womi compare runs/calibration/linear-pixels/report/report.json \
  runs/calibration/last-frame/report/report.json --output runs/comparison.json
```

Replay loads retained arrays and recomputes metrics; it does not rerun a model. It checks the evaluator source identity and exact evidence hashes. A different evaluator release needs its own report. The command itself does not attest that another person or host ran it.

## Frozen CPU environment

`requirements-eval.txt` pins replay dependencies for Python 3.12. The Docker recipe uses a versioned base tag; record the resolved image digest for a measured campaign because a tag is not an immutable digest.

```bash
docker build -t womi-eval:0.2.0 .
docker image inspect womi-eval:0.2.0 --format '{{.Id}}'
mkdir -p runs/container
docker run --rm --network none --read-only --tmpfs /tmp \
  --user "$(id -u):$(id -g)" -v "$PWD/runs/container:/work" \
  womi-eval:0.2.0 demo --output /work/calibration
```

This image is an **evaluator**, not a secure model runner. Do not mount active private targets into a container that executes a submitted adapter.

## Development

```bash
python -m pip install '.[test]'
python -m pytest -q
python -m pip install build
python -m build
```

CI tests the package, creates calibration evidence, then replays that evidence in a separate job from the installed wheel. The static site is built from those reports only after replay passes. [Workflow](../.github/workflows/ci.yml)
