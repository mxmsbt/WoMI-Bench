"""Versioned task contracts with evaluator-only targets."""
import math
import re
from pathlib import Path

import numpy as np

from .io import InvalidEvidence, file_hash, load_arrays, read_json, verified_file

TASKS = ("spatial", "geometry", "persistence", "editing", "dynamics")
SCOPES = ("synthetic_diagnostic", "development", "held_out")
IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$")
INPUT_KEYS = {"rgb", "intrinsics", "camera_to_world", "query_intrinsics",
              "query_camera_to_world", "timestamps_s", "actions", "edit_mask"}


def require(condition, message):
    if not condition:
        raise InvalidEvidence(message)


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def dataset(path):
    path = Path(path)
    doc = read_json(path)
    require(doc.get("schema") == "womi.dataset.v1", "Unknown dataset schema")
    require(doc.get("protocol_version") == "0.2.0", "Unsupported protocol version")
    require(doc.get("scope") in SCOPES, "Unknown evaluation scope")
    require(isinstance(doc.get("license"), str) and doc["license"], "Dataset license required")
    require(isinstance(doc.get("id"), str) and IDENTIFIER.fullmatch(doc["id"]), "Invalid dataset ID")
    require(isinstance(doc.get("cases"), list) and 1 <= len(doc["cases"]) <= 4096, "Invalid case count")
    ids = set()
    for case in doc["cases"]:
        require(set(case) == {"id", "world_id", "task", "input", "output_shape", "timestamps_s",
                              "request"}, "Unexpected case fields")
        for key in ("id", "world_id"):
            require(isinstance(case[key], str) and IDENTIFIER.fullmatch(case[key]), "Invalid case/world ID")
        require(case["id"] not in ids and case["task"] in TASKS, "Duplicate case or unsupported task")
        ids.add(case["id"])
        shape = case["output_shape"]
        require(isinstance(shape, list) and len(shape) == 3 and
                all(type(v) is int and 1 <= v <= 8192 for v in shape) and math.prod(shape) <= 8_000_000,
                "Output shape must be bounded [frames, height, width]")
        times = case["timestamps_s"]
        require(isinstance(times, list) and len(times) == shape[0] and
                all(finite_number(t) and t >= 0 for t in times) and
                all(a <= b for a, b in zip(times, times[1:])), "Invalid physical timestamps")
        require(isinstance(case["request"], dict), "Request must be an object")
        inputs = load_arrays(verified_file(path.parent, case["input"]))
        require(set(inputs) <= INPUT_KEYS and "rgb" in inputs, "Unsupported or target-like input fields")
        rgb = inputs["rgb"]
        require(rgb.dtype == np.uint8 and rgb.ndim == 4 and rgb.shape[-1] == 3 and
                list(rgb.shape[1:3]) == shape[1:], "Input RGB must be uint8 [observations,H,W,3]")
        for key, array in inputs.items():
            require(np.isfinite(array).all(), "Nonfinite public input")
        for key, count in (("intrinsics", rgb.shape[0]), ("query_intrinsics", shape[0])):
            matrix = inputs.get(key)
            require(matrix is not None and matrix.shape == (count, 3, 3) and
                    (matrix[:, 0, 0] > 0).all() and (matrix[:, 1, 1] > 0).all() and
                    np.allclose(matrix[:, 2, :], [0, 0, 1]), "Invalid declared intrinsics")
        for key, count in (("camera_to_world", rgb.shape[0]), ("query_camera_to_world", shape[0])):
            matrix = inputs.get(key)
            require(matrix is not None and matrix.shape == (count, 4, 4) and
                    np.allclose(matrix[:, 3, :], [0, 0, 0, 1]), "Invalid camera-to-world transform")
            rotation = matrix[:, :3, :3]
            require(np.allclose(rotation @ rotation.transpose(0, 2, 1), np.eye(3), atol=1e-5) and
                    np.allclose(np.linalg.det(rotation), 1, atol=1e-5), "Camera rotation must be right-handed rigid")
        if case["task"] == "geometry":
            require(rgb.shape[0] == shape[0], "Geometry predicts depth at the supplied observation views")
            require(np.array_equal(inputs["intrinsics"], inputs["query_intrinsics"]) and
                    np.array_equal(inputs["camera_to_world"], inputs["query_camera_to_world"]),
                    "Geometry queries must match the observed cameras")
        if case["task"] == "dynamics":
            require(shape[0] >= 2 and all(a < b for a, b in zip(times, times[1:])),
                    "Dynamics requires increasing physical time")
            observed = inputs.get("timestamps_s")
            require(observed is not None and observed.shape == (rgb.shape[0],) and
                    np.all(np.diff(observed) > 0) and observed[-1] < times[0],
                    "Dynamics observations must end before forecast starts")
        if case["task"] == "persistence":
            require(shape[0] >= 2, "Persistence requires a return view")
            require(np.array_equal(inputs["query_intrinsics"][0], inputs["query_intrinsics"][-1]) and
                    np.array_equal(inputs["query_camera_to_world"][0], inputs["query_camera_to_world"][-1]),
                    "Persistence must return to the first query camera")
        if case["task"] == "editing":
            mask = inputs.get("edit_mask")
            require(mask is not None and mask.dtype == np.bool_ and mask.shape == tuple(shape),
                    "Editing requires an input edit_mask")
            require(np.array_equal(inputs["query_intrinsics"], np.repeat(inputs["intrinsics"][-1:], shape[0], axis=0)) and
                    np.array_equal(inputs["query_camera_to_world"], np.repeat(inputs["camera_to_world"][-1:], shape[0], axis=0)),
                    "Appearance editing queries must use the last observation camera")
    return doc, file_hash(path)


def target_index(path, manifest, manifest_hash):
    doc = read_json(path)
    require(doc.get("schema") == "womi.targets.v1" and doc.get("dataset_sha256") == manifest_hash,
            "Target bundle does not bind to the dataset")
    require(set(doc.get("cases", {})) == {c["id"] for c in manifest["cases"]}, "Target coverage must be exact")
    return doc


def target_arrays(path, case):
    arrays = load_arrays(path)
    shape = tuple(case["output_shape"])
    mask = arrays.get("valid")
    require(mask is not None and mask.dtype == np.bool_ and mask.shape == shape and mask.any(),
            "Target needs a nonempty boolean valid mask")
    key = "depth" if case["task"] == "geometry" else "rgb"
    expected = shape if key == "depth" else (*shape, 3)
    require(key in arrays and arrays[key].shape == expected, "Target dimensions differ from manifest")
    if key == "rgb":
        require(arrays[key].dtype == np.uint8, "Target RGB must be uint8")
    else:
        require(arrays[key].dtype.kind == "f" and np.isfinite(arrays[key][mask]).all()
                and (arrays[key][mask] > 0).all(), "Target depth must be finite positive camera-Z meters")
    if case["task"] == "editing":
        region = arrays.get("region")
        require(region is not None and region.dtype == np.bool_ and region.shape == shape and
                (mask & region).any() and (mask & ~region).any(), "Editing needs target and preserved regions")
    if case["task"] == "dynamics":
        fg = arrays.get("foreground")
        require(fg is not None and fg.dtype == np.bool_ and fg.shape == shape and (mask & fg).any(),
                "Dynamics needs a nonempty independently annotated foreground")
        require((mask[1:] & mask[:-1]).any(), "Dynamics needs overlapping temporal validity")
    if case["task"] == "persistence":
        common = mask[0] & mask[-1]
        require(common.any() and np.array_equal(arrays["rgb"][0][common], arrays["rgb"][-1][common]),
                "Persistence fixture must return to unchanged appearance at the same view")
    allowed = {key, "valid"} | ({"region"} if case["task"] == "editing" else set()) | (
        {"foreground"} if case["task"] == "dynamics" else set())
    require(set(arrays) == allowed, "Unexpected target arrays")
    return arrays
