import argparse
import json
from pathlib import Path

from . import __version__
from .adapters import CONTROLS, predict
from .contracts import dataset
from .demo import generate
from .evaluate import compare, evaluate, replay
from .io import write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description="WoMI-Bench: independent world-model evaluation")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Generate and score original analytic calibration scenes; no model download")
    demo.add_argument("--output", type=Path, required=True); demo.add_argument("--worlds", type=int, default=8)
    validate = sub.add_parser("validate", help="Validate public input hashes and contracts")
    validate.add_argument("--dataset", type=Path, required=True)
    run = sub.add_parser("predict", help="Run a trusted local adapter against public inputs only")
    run.add_argument("--dataset", type=Path, required=True); run.add_argument("--output", type=Path, required=True)
    run.add_argument("--adapter", required=True); run.add_argument("--name", required=True)
    run.add_argument("--revision", required=True); run.add_argument("--kind", choices=("control", "model"), default="model")
    for command in ("evaluate", "replay"):
        p = sub.add_parser(command)
        for name in ("dataset", "targets", "submission"):
            p.add_argument("--"+name, type=Path, required=True)
        p.add_argument("--output" if command == "evaluate" else "--report", type=Path, required=True)
    pair = sub.add_parser("compare", help="Paired differences for reports with matching evidence contracts")
    pair.add_argument("first", type=Path); pair.add_argument("second", type=Path)
    pair.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            manifest, targets = generate(args.output/"dataset", args.worlds)
            for name in CONTROLS:
                submission = predict(manifest, args.output/name/"prediction", adapter=name, name=name,
                                     revision=__version__, kind="control")
                evaluate(manifest, targets, submission, args.output/name/"report")
                replay(manifest, targets, submission, args.output/name/"report"/"report.json")
            comparison = compare(args.output/"linear-pixels/report/report.json", args.output/"last-frame/report/report.json")
            write_json(args.output/"paired-comparison.json", comparison)
            print(f"Calibration reports: {args.output.resolve()}\nSynthetic diagnostics only; no learned-model score.")
        elif args.command == "validate":
            doc, sha = dataset(args.dataset); print(json.dumps({"cases": len(doc["cases"]), "sha256": sha}))
        elif args.command == "predict":
            print(predict(args.dataset, args.output, adapter=args.adapter, name=args.name, revision=args.revision, kind=args.kind))
        elif args.command == "evaluate":
            result = evaluate(args.dataset, args.targets, args.submission, args.output)
            print(json.dumps({"assigned": result["measurements"]["assigned"], "successful": result["measurements"]["successful"],
                              "report": str(args.output/"report.html")}))
        elif args.command == "replay":
            print(json.dumps(replay(args.dataset, args.targets, args.submission, args.report)))
        elif args.command == "compare":
            write_json(args.output, compare(args.first, args.second)); print(args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"WoMI-Bench: {exc}\n")


if __name__ == "__main__":
    main()
