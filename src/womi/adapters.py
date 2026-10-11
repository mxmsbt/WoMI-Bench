"""Prediction producers receive public inputs only; execution itself is trusted."""
import importlib
from pathlib import Path
import time

import numpy as np

from .contracts import dataset, require
from .io import load_arrays, record, verified_file, write_json

CONTROLS = ("last-frame", "linear-pixels", "black")


def control(name, case, inputs):
    shape = tuple(case["output_shape"])
    if case["task"] == "geometry":
        # No true depth is supplied to the producer. Deliberately simple diagnostic.
        return {"depth": np.full(shape, 0. if name == "black" else 4., dtype=np.float32)}
    source = inputs["rgb"]
    out = np.repeat(source[-1:], shape[0], axis=0)
    if name == "black":
        out = np.zeros_like(out)
    if name == "linear-pixels" and case["task"] == "dynamics":
        t = inputs["timestamps_s"]
        slope = (source[-1].astype(float)-source[-2].astype(float))/(t[-1]-t[-2])
        out = np.stack([np.clip(source[-1] + slope*(q-t[-1]), 0, 255).astype(np.uint8)
                        for q in case["timestamps_s"]])
    return {"rgb": out}


def predict(manifest_path, output, *, adapter, name, revision, kind="model"):
    manifest, identity = dataset(manifest_path)
    require(kind in ("model", "control") and bool(name) and bool(revision), "Model identity required")
    if adapter in CONTROLS:
        require(kind == "control", "Diagnostic controls cannot be labelled learned models")
        function = lambda case, arrays: control(adapter, case, arrays)
    else:
        module, sep, member = adapter.partition(":")
        require(bool(sep and module and member), "Adapter must be module:function")
        function = getattr(importlib.import_module(module), member)
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    (output/"outputs").mkdir()
    entries = {}
    for case in manifest["cases"]:
        inputs = load_arrays(verified_file(Path(manifest_path).parent, case["input"]))
        # Do not expose artifact paths or hashes through the adapter interface.
        request = {key: case[key] for key in ("id", "task", "output_shape", "timestamps_s", "request")}
        begin = time.perf_counter()
        try:
            result = function(request, inputs)
            require(isinstance(result, dict) and set(result) == {"depth" if case["task"] == "geometry" else "rgb"},
                    "Adapter returned unexpected arrays")
            require(all(isinstance(v, np.ndarray) and v.dtype.kind in "buif" and v.size <= 32_000_000
                        for v in result.values()), "Adapter returned unsafe arrays")
            path = output/"outputs"/(case["id"]+".npz")
            np.savez_compressed(path, **result)
            entry = {"status": "ok", "output": record(path, output)}
        except Exception as exc:
            # Keep every assigned case, but avoid including credential-bearing exception text.
            entry = {"status": "failed", "error_type": type(exc).__name__}
        entry["runtime_seconds"] = time.perf_counter()-begin
        entry["cost_usd"] = None
        entries[case["id"]] = entry
        # A crash preserves this partial receipt; resume never silently retries a sample.
        write_json(output/(case["id"]+".receipt.json"), entry)
    submission = {"schema": "womi.submission.v1", "dataset_sha256": identity,
                  "system": {"name": name, "revision": revision, "kind": kind}, "cases": entries}
    write_json(output/"submission.json", submission)
    return output/"submission.json"


def depth_export(source, convention, *, scale_meters):
    """Normalize already-produced public model outputs; never fit scale to targets."""
    require(np.isfinite(scale_meters) and scale_meters > 0, "A positive declared scale in meters is required")
    values = np.asarray(source)
    if convention == "mapanything-depth-z":
        require(values.ndim == 4 and values.shape[-1] == 1, "Expected stacked depth_z [N,H,W,1]")
        values = values[..., 0]
    elif convention == "pi3-local-points":
        require(values.ndim == 5 and values.shape[0] == 1 and values.shape[-1] == 3,
                "Expected local_points [1,N,H,W,3]")
        values = values[0, ..., 2]
    elif convention == "da3-depth":
        require(values.ndim == 3, "Expected depth [N,H,W]")
    else:
        raise ValueError("Unknown depth output convention")
    require(values.dtype.kind == "f" and np.isfinite(values).all(), "Expected finite floating point predictions")
    return {"depth": np.asarray(values * scale_meters, dtype=np.float32)}

