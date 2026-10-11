"""Transparent low-level diagnostics; no perceptual/physical intelligence aggregate."""
import numpy as np

from .io import InvalidEvidence

METRICS = {
    "spatial": ("rgb_mae", "rgb_psnr_capped_db"),
    "geometry": ("depth_relative_error_bounded",),
    "persistence": ("rgb_mae", "revisit_mae"),
    "editing": ("edit_region_mae", "preserved_region_mae"),
    "dynamics": ("rgb_mae", "foreground_mae", "temporal_delta_mae"),
}


def failures(task):
    return {key: 0.0 if key == "rgb_psnr_capped_db" else 1.0 for key in METRICS[task]}


def score(case, prediction, target):
    task = case["task"]
    key = "depth" if task == "geometry" else "rgb"
    if set(prediction) != {key}:
        raise InvalidEvidence("Prediction must contain exactly the task's output array")
    p, t, mask = prediction[key], target[key], target["valid"]
    if p.shape != t.shape or not np.isfinite(p).all():
        raise InvalidEvidence("Invalid prediction shape or nonfinite values")
    if task == "geometry":
        if p.dtype.kind != "f":
            raise InvalidEvidence("Depth must be floating point camera-Z meters")
        p, t = p[mask].astype(np.float64), t[mask].astype(np.float64)
        error = np.where(p > 0, np.minimum(np.abs(p - t) / t, 1.0), 1.0)
        return {"depth_relative_error_bounded": float(error.mean())}
    if p.dtype != np.uint8:
        raise InvalidEvidence("RGB must be uint8; implicit clipping/rescaling is forbidden")
    p, t = p.astype(np.float64) / 255, t.astype(np.float64) / 255
    error = np.abs(p - t).mean(axis=-1)
    mae = float(error[mask].mean())
    if task == "spatial":
        mse = float(((p - t)**2)[mask].mean())
        return {"rgb_mae": mae, "rgb_psnr_capped_db": float(-10 * np.log10(max(mse, 1e-6)))}
    if task == "persistence":
        common = mask[0] & mask[-1]
        return {"rgb_mae": mae, "revisit_mae": float(np.abs(p[0] - p[-1])[common].mean())}
    if task == "editing":
        region = target["region"]
        return {"edit_region_mae": float(error[mask & region].mean()),
                "preserved_region_mae": float(error[mask & ~region].mean())}
    valid_delta = mask[1:] & mask[:-1]
    delta_error = np.abs(np.diff(p, axis=0) - np.diff(t, axis=0)).mean(axis=-1) / 2
    return {"rgb_mae": mae, "foreground_mae": float(error[mask & target["foreground"]].mean()),
            "temporal_delta_mae": float(delta_error[valid_delta].mean())}


def interval(values, *, seed=1729, repeats=2000):
    """Percentile bootstrap over independent world-level values, never frames."""
    values = np.asarray(values, dtype=np.float64)
    if not len(values):
        raise InvalidEvidence("Cannot summarize an empty group")
    mean = float(values.mean())
    if len(values) < 2:
        return {"mean": mean, "ci95": None, "world_count": len(values)}
    rng = np.random.default_rng(seed)
    # Chunking bounds memory for large campaigns.
    samples = []
    for start in range(0, repeats, 100):
        indices = rng.integers(len(values), size=(min(100, repeats-start), len(values)))
        samples.extend(values[indices].mean(axis=1).tolist())
    return {"mean": mean, "ci95": np.quantile(samples, [0.025, 0.975]).tolist(), "world_count": len(values)}

