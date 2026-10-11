"""Build a static, calibration-only evidence browser after replaying the raw arrays."""
import argparse
from pathlib import Path
import shutil

from womi.adapters import CONTROLS
from womi.evaluate import replay
from womi.io import read_json, write_json

parser = argparse.ArgumentParser()
parser.add_argument("bundle", type=Path)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--revision", default="local-development")
parser.add_argument("--ci-url", default="")
args = parser.parse_args()
rows = []
for name in CONTROLS:
    source = args.bundle/name/"report/report.json"
    report = read_json(source)
    if report["scope"] != "synthetic_diagnostic" or report["system"]["kind"] != "control":
        raise ValueError("This site builder only admits synthetic calibration controls")
    replay(args.bundle/"dataset/public/manifest.json", args.bundle/"dataset/targets/targets.json",
           args.bundle/name/"prediction/submission.json", source)
    rows.append({"name": name, "report": f"reports/{name}/report.html", "data": f"reports/{name}/report.json",
                 "cases_csv": f"reports/{name}/per-case.csv", "system": report["system"],
                 "measured_at_utc": report["measured_at_utc"], "tasks": report["measurements"]["tasks"],
                 "successful": report["measurements"]["successful"], "assigned": report["measurements"]["assigned"],
                 "dataset_sha256": report["dataset_sha256"], "evaluator_sha256": report["evaluator_sha256"],
                 "reported_seconds": report["measurements"]["total_inference_seconds"],
                 "reported_cost_usd": report["measurements"]["total_cost_usd"]})
if len({r["dataset_sha256"] for r in rows}) != 1:
    raise ValueError("Control reports are not a matched campaign")
shutil.copytree(Path(__file__).resolve().parents[1]/"site", args.output)
for name in CONTROLS:
    shutil.copytree(args.bundle/name/"report", args.output/"reports"/name)
shutil.copy2(args.bundle/"paired-comparison.json", args.output/"paired-comparison.json")
shutil.make_archive(str(args.output/"calibration-evidence"), "zip", args.bundle)
write_json(args.output/"catalog.json", {"version": "0.2.0", "revision": args.revision, "ci_url": args.ci_url,
                                       "scope": "synthetic_diagnostic", "model_results": [], "controls": rows})
print(args.output.resolve())
