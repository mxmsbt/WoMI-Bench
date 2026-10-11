"""Bridge saved outputs into WoMI's geometry contract; no model code is vendored.

Set WOMI_EXPORT_ROOT to an isolated directory of <case-id>.npz files with a
single 'values' array, WOMI_DEPTH_CONVENTION to one of the documented formats,
and WOMI_METERS_PER_UNIT to the predeclared positive scale. Never derive it
from evaluation targets. Run on a geometry-only manifest.
"""
import os
from pathlib import Path

from womi.adapters import depth_export
from womi.io import load_arrays, safe_file


def predict(case, inputs):
    if case["task"] != "geometry":
        raise ValueError("This adapter supports geometry only")
    path = safe_file(Path(os.environ["WOMI_EXPORT_ROOT"]), case["id"]+".npz")
    arrays = load_arrays(path)
    if set(arrays) != {"values"}:
        raise ValueError("Expected a single values array")
    return depth_export(arrays["values"], os.environ["WOMI_DEPTH_CONVENTION"],
                        scale_meters=float(os.environ["WOMI_METERS_PER_UNIT"]))
