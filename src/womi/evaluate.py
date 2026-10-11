"""Offline scoring and replay, with no candidate-code execution."""
import csv
from datetime import datetime, timezone
from pathlib import Path
import sys
import zipfile

import numpy as np

from . import __version__
from .contracts import dataset, finite_number, require, target_arrays, target_index
from .io import InvalidEvidence, digest, file_hash, load_arrays, read_json, verified_file, write_json
from .metrics import failures, interval, score


def evaluator_identity():
    return digest({p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))})


def measure(manifest_path, target_path, submission_path):
    manifest_path, target_path, submission_path = map(Path, (manifest_path, target_path, submission_path))
    manifest, identity = dataset(manifest_path)
    targets = target_index(target_path, manifest, identity)
    sub = read_json(submission_path)
    require(sub.get("schema") == "womi.submission.v1" and sub.get("dataset_sha256") == identity,
            "Submission is bound to another dataset")
    system = sub.get("system", {})
    require(isinstance(system.get("name"), str) and 1 <= len(system["name"]) <= 160 and
            isinstance(system.get("revision"), str) and system["revision"] and
            system.get("kind") in ("control", "model"), "System name, revision and kind required")
    entries = sub.get("cases")
    require(isinstance(entries, dict) and set(entries) <= {c["id"] for c in manifest["cases"]},
            "Submission contains unassigned cases")
    rows = []
    for case in manifest["cases"]:
        target = target_arrays(verified_file(target_path.parent, targets["cases"][case["id"]]), case)
        if case["task"] == "editing":
            inputs = load_arrays(verified_file(manifest_path.parent, case["input"]))
            require(np.array_equal(target["region"], inputs["edit_mask"]), "Edit regions disagree")
            before = np.broadcast_to(inputs["rgb"][-1], target["rgb"].shape)
            outside = target["valid"] & ~target["region"]
            require(np.array_equal(before[outside], target["rgb"][outside]),
                    "Editing targets must preserve the specified unchanged region")
        entry = entries.get(case["id"], {"status": "missing"})
        require(isinstance(entry, dict) and entry.get("status") in ("ok", "failed", "missing"), "Invalid case status")
        for key in ("runtime_seconds", "cost_usd"):
            require(entry.get(key) is None or finite_number(entry[key]) and entry[key] >= 0, "Invalid resource value")
        status, reason, values = "failed", entry["status"], failures(case["task"])
        if entry["status"] == "ok":
            # Changed/missing files and paths are integrity failures: abort, do not silently score.
            path = verified_file(submission_path.parent, entry.get("output"))
            try:
                values = score(case, load_arrays(path), target)
                status, reason = "ok", None
            except (InvalidEvidence, ValueError, OSError, EOFError, zipfile.BadZipFile) as exc:
                reason = "invalid_prediction: " + str(exc)[:240]
        rows.append({"id": case["id"], "world_id": case["world_id"], "task": case["task"],
                     "status": status, "reason": reason, "metrics": values,
                     "runtime_seconds": entry.get("runtime_seconds"), "cost_usd": entry.get("cost_usd")})
    groups = {}
    for task in sorted({r["task"] for r in rows}):
        selected = [r for r in rows if r["task"] == task]
        by_world = {}
        for row in selected:
            by_world.setdefault(row["world_id"], []).append(row)
        world_values = {world: {key: float(np.mean([r["metrics"][key] for r in cases]))
                               for key in cases[0]["metrics"]} for world, cases in by_world.items()}
        groups[task] = {"assigned": len(selected), "successful": sum(r["status"] == "ok" for r in selected),
                        "failed": sum(r["status"] != "ok" for r in selected), "world_values": world_values,
                        "metrics": {key: interval([v[key] for v in world_values.values()])
                                    for key in selected[0]["metrics"]}}
    seconds = [r["runtime_seconds"] for r in rows]
    costs = [r["cost_usd"] for r in rows]
    measured = {"cases": rows, "tasks": groups, "assigned": len(rows),
                "successful": sum(r["status"] == "ok" for r in rows),
                "resource_evidence": "submitter_reported_not_independently_attested",
                "total_inference_seconds": sum(seconds) if all(x is not None for x in seconds) else None,
                "total_cost_usd": sum(costs) if all(x is not None for x in costs) else None}
    return {"schema": "womi.report.v1", "evaluator_version": __version__, "evaluator_sha256": evaluator_identity(),
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_id": manifest["id"], "dataset_sha256": identity, "targets_sha256": file_hash(target_path),
            "submission_sha256": file_hash(submission_path), "scope": manifest["scope"], "system": system,
            "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
            "verification": "local_recompute_only", "leaderboard_admission": "not_reviewed",
            "cross_track_aggregate": None, "measurements": measured, "measurements_sha256": digest(measured)}


def evaluate(manifest, targets, submission, output):
    report = measure(manifest, targets, submission)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/"report.json", report)
    with (output/"per-case.csv").open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["case", "world", "task", "status", "metric", "value"])
        for row in report["measurements"]["cases"]:
            for metric, value in row["metrics"].items():
                writer.writerow([row["id"], row["world_id"], row["task"], row["status"], metric, value])
    from .report import render_report
    render_report(report, manifest, targets, submission, output)
    return report


def replay(manifest, targets, submission, report_path):
    recorded = read_json(report_path)
    current = measure(manifest, targets, submission)
    for key in ("schema", "evaluator_version", "evaluator_sha256", "dataset_sha256", "targets_sha256",
                "submission_sha256", "scope", "system", "measurements", "measurements_sha256"):
        require(recorded.get(key) == current[key], "Replay differs: " + key)
    return {"recomputed": True, "measurements_sha256": current["measurements_sha256"],
            "host_independence": "not_attested_by_this_command"}


def compare(first_path, second_path):
    first, second = read_json(first_path), read_json(second_path)
    for report in (first, second):
        require(report.get("schema") == "womi.report.v1" and
                digest(report["measurements"]) == report["measurements_sha256"], "Invalid report integrity")
    for key in ("dataset_sha256", "targets_sha256", "evaluator_sha256", "scope"):
        require(first[key] == second[key], "Unmatched reports: " + key)
    require(set(first["measurements"]["tasks"]) == set(second["measurements"]["tasks"]), "Task coverage differs")
    result = {}
    for task, a in first["measurements"]["tasks"].items():
        b = second["measurements"]["tasks"][task]
        require(set(a["world_values"]) == set(b["world_values"]), "World coverage differs")
        result[task] = {key: interval([a["world_values"][w][key] - b["world_values"][w][key]
                                     for w in sorted(a["world_values"])]) for key in a["metrics"]}
    return {"schema": "womi.comparison.v1", "difference": "first_minus_second",
            "first": first["system"], "second": second["system"], "scope": first["scope"],
            "dataset_sha256": first["dataset_sha256"], "paired_world_intervals": result,
            "note": "Descriptive paired intervals, not multiple-comparison corrected; resources are not attested."}
