"""Portable HTML report and small, explicitly selected evidence previews."""
from html import escape
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

from .io import load_arrays, read_json, verified_file


def render_report(report, manifest_path, targets_path, submission_path, output):
    manifest, targets, sub = map(read_json, (manifest_path, targets_path, submission_path))
    output = Path(output); (output/"previews").mkdir()
    rows = []
    for task, group in report["measurements"]["tasks"].items():
        for key, value in group["metrics"].items():
            ci = "unavailable" if value["ci95"] is None else " – ".join(f"{v:.4f}" for v in value["ci95"])
            rows.append(f"<tr><td>{escape(task)}</td><td>{escape(key)}</td><td>{value['mean']:.4f}</td>"
                        f"<td>{ci}</td><td>{group['successful']}/{group['assigned']}</td></tr>")
    cards = []; shown = set()
    statuses = {r["id"]: r["status"] for r in report["measurements"]["cases"]}
    for case in sorted(manifest["cases"], key=lambda c: c["id"]):
        if case["task"] in shown or statuses[case["id"]] != "ok": continue
        shown.add(case["task"])
        p = load_arrays(verified_file(Path(submission_path).parent, sub["cases"][case["id"]]["output"]))
        t = load_arrays(verified_file(Path(targets_path).parent, targets["cases"][case["id"]]))
        inp = load_arrays(verified_file(Path(manifest_path).parent, case["input"]))
        if case["task"] == "geometry":
            bound = max(float(t["depth"][t["valid"]].max()), 1.)
            def colors(depth):
                v = np.clip(np.nan_to_num(depth / bound), 0, 1)
                return np.stack([v*255, (1-v)*180, (1-v)*240], -1).astype(np.uint8)
            pred, truth = colors(p["depth"][0]), colors(t["depth"][0])
        else: pred, truth = p["rgb"][0], t["rgb"][0]
        error = np.abs(pred.astype(float)-truth.astype(float)).mean(-1)
        heat = np.stack([error*3, np.zeros_like(error), np.zeros_like(error)], -1).clip(0,255).astype(np.uint8)
        canvas = Image.new("RGB", (4*240, 190), "#101722")
        draw = ImageDraw.Draw(canvas)
        for index, (label, pixels) in enumerate(zip(("Last observation", "Reference", "Prediction", "Display error"),
                                                   (inp["rgb"][-1], truth, pred, heat))):
            canvas.paste(Image.fromarray(pixels).resize((240,160), Image.Resampling.NEAREST), (index*240, 30))
            draw.text((index*240+8, 9), label, fill="white")
        filename = f"previews/{case['task']}.png"; canvas.save(output/filename)
        cards.append(f"<figure><img src='{filename}' alt='{escape(case['task'])} diagnostic'>"
                     f"<figcaption>{escape(case['id'])}: first successful case, first query. "
                     "Depth colors use the reference range; display error is not the numerical depth metric.</figcaption></figure>")
    name = escape(report["system"]["name"])
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{name} · WoMI-Bench</title><style>
body{{font:16px system-ui;background:#101722;color:#e8eef5;max-width:1100px;margin:4rem auto;padding:0 24px;line-height:1.6}}
a{{color:#69ddbd}}table{{width:100%;border-collapse:collapse}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #344052}}
img{{max-width:100%;height:auto}}figure{{margin:32px 0}}figcaption,small{{color:#abbacb}}code{{overflow-wrap:anywhere}}
</style><h1>{name}</h1><p>WoMI-Bench {report['evaluator_version']} · {escape(report['scope'])} · {escape(report['system']['kind'])}</p>
<p>Local metric recomputation. Admission has not been independently reviewed. Calibration controls are not learned-model results.</p>
<p><a href="report.json">Full JSON</a> · <a href="per-case.csv">Case CSV</a></p>
<table><thead><tr><th>Task</th><th>Metric</th><th>Mean</th><th>95% world bootstrap</th><th>Successful / assigned</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table><p>Errors are lower-is-better; capped PSNR is higher-is-better. Worlds receive equal weight.
Intervals are descriptive, uncorrected for multiple comparisons. No cross-task aggregate.</p>
<h2>Evidence previews</h2>{''.join(cards)}<small>Dataset SHA256: <code>{report['dataset_sha256']}</code><br>
Evaluator SHA256: <code>{report['evaluator_sha256']}</code><br>Independent research by Maxime Sebti.</small></html>"""
    (output/"report.html").write_text(html)

