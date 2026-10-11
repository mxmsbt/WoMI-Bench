"""Recompute supplied calibration outputs; never execute a candidate adapter."""
import argparse
import platform
from pathlib import Path

from womi.adapters import CONTROLS
from womi.evaluate import compare, replay
from womi.io import read_json, write_json

parser = argparse.ArgumentParser()
parser.add_argument("bundle", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
checks = {}
for name in CONTROLS:
    checks[name] = replay(args.bundle/"dataset/public/manifest.json", args.bundle/"dataset/targets/targets.json",
                          args.bundle/name/"prediction/submission.json", args.bundle/name/"report/report.json")
comparison = compare(args.bundle/"linear-pixels/report/report.json", args.bundle/"last-frame/report/report.json")
if comparison != read_json(args.bundle/"paired-comparison.json"):
    raise ValueError("Recorded paired comparison did not replay")
write_json(args.output, {"schema": "womi.calibration_replay.v1", "checks": checks,
                         "paired_comparison_recomputed": True, "platform": platform.platform(),
                         "claim": "metric recomputation only; no scientific review or model qualification"})
print("Recomputed all three control reports and the paired comparison from retained arrays.")
