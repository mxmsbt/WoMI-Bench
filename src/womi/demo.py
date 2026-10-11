"""Original analytic-room calibration fixtures, not a learned-model benchmark."""
from pathlib import Path
import random

import numpy as np

from .io import file_hash, record, write_json


def _render(boxes, camera_x, height=32, width=48):
    """Exact ray/AABB intersections in OpenCV camera coordinates; depth is camera Z."""
    y, x = np.mgrid[:height, :width]
    k = np.array([[42, 0, width/2], [0, 42, height/2], [0, 0, 1]], dtype=np.float64)
    rays = np.stack(((x+.5-k[0, 2])/k[0, 0], (y+.5-k[1, 2])/k[1, 1], np.ones_like(x)), axis=-1)
    origin = np.array([camera_x, 0., 0.])
    depth = np.full((height, width), 8., dtype=np.float64)
    hit = origin + depth[..., None] * rays
    checker = ((np.floor(hit[..., 0]*3) + np.floor(hit[..., 1]*3)) % 2).astype(np.uint8)
    rgb = np.stack([150 + 18*checker, 155 + 18*checker, 163 + 18*checker], axis=-1)
    ids = np.zeros((height, width), np.int16)
    # The positive-y plane is a floor; the back wall closes every ray.
    floor_t = np.divide(1.2, rays[..., 1], out=np.full_like(depth, np.inf), where=rays[..., 1] > 0)
    mask = (floor_t > 0) & (floor_t < depth)
    depth[mask] = floor_t[mask]
    rgb[mask] = [92, 104, 118]
    for index, (low, high, color) in enumerate(boxes, 1):
        lo, hi = np.array(low), np.array(high)
        with np.errstate(divide="ignore", invalid="ignore"):
            a, b = (lo-origin)/rays, (hi-origin)/rays
        near = np.minimum(a, b).max(axis=-1)
        far = np.maximum(a, b).min(axis=-1)
        visible = (far >= near) & (near > 0) & (near < depth)
        depth[visible] = near[visible]
        ids[visible] = index
        rgb[visible] = color
    pose = np.eye(4); pose[0, 3] = camera_x
    return rgb.astype(np.uint8), depth.astype(np.float32), ids, k, pose


def generate(output, worlds=8):
    if not 2 <= worlds <= 64:
        raise ValueError("Calibration suite supports 2–64 worlds")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    public = output/"public"; private = output/"targets"
    (public/"inputs").mkdir(parents=True); private.mkdir()
    cases, targets = [], {}
    for world in range(worlds):
        rng = random.Random(4400 + world)
        center = rng.uniform(-.25, .25)
        boxes = [([center-.38, -.45, 3.2], [center+.38, .65, 4.0], [44, 139, 204]),
                 ([-1.4, -.1, 4.5], [-.65, 1.0, 5.3], [190, 151, 72]),
                 ([.65, -.6, 5.2], [1.5, 1.1, 6.0], [102, 163, 116])]
        for task in ("spatial", "geometry", "persistence", "editing", "dynamics"):
            ident = f"room-{world:03d}-{task}"
            context_x = [-.35, .35] if task in ("spatial", "geometry") else [0.]
            query_x = {"spatial": [-.12, .60], "geometry": context_x,
                       "persistence": [0., .55, 0.], "editing": [0.], "dynamics": [0., 0., 0.]}[task]
            times = [0.]*len(query_x)
            contexts = [_render(boxes, x) for x in context_x]
            future_boxes = [boxes]*len(query_x)
            if task == "editing":
                future_boxes = [[(boxes[0][0], boxes[0][1], [208, 60, 66]), *boxes[1:]]]
            if task == "dynamics":
                velocity = rng.uniform(.7, 1.1)
                def advance(t):
                    offset = np.array([velocity*t, 0., 0.])
                    return [(np.array(boxes[0][0])+offset, np.array(boxes[0][1])+offset, boxes[0][2]), *boxes[1:]]
                contexts = [_render(advance(t), 0.) for t in (0., .1, .2)]
                times = [.3, .4, .5]
                future_boxes = [advance(t) for t in times]
            queries = [_render(b, x) for b, x in zip(future_boxes, query_x)]
            inp = {"rgb": np.stack([r[0] for r in contexts]),
                   "intrinsics": np.stack([r[3] for r in contexts]),
                   "camera_to_world": np.stack([r[4] for r in contexts]),
                   "query_intrinsics": np.stack([r[3] for r in queries]),
                   "query_camera_to_world": np.stack([r[4] for r in queries])}
            if task == "dynamics": inp["timestamps_s"] = np.array([0., .1, .2])
            shape = list(np.stack([r[1] for r in queries]).shape)
            target = {"valid": np.ones(shape, dtype=bool)}
            target["depth" if task == "geometry" else "rgb"] = np.stack([r[1 if task == "geometry" else 0] for r in queries])
            if task == "editing":
                target["region"] = np.stack([r[2] == 1 for r in queries])
                inp["edit_mask"] = target["region"].copy()
            if task == "dynamics": target["foreground"] = np.stack([r[2] == 1 for r in queries])
            ipath, tpath = public/"inputs"/f"{ident}.npz", private/f"{ident}.npz"
            np.savez_compressed(ipath, **inp); np.savez_compressed(tpath, **target)
            cases.append({"id": ident, "world_id": f"room-{world:03d}", "task": task,
                          "input": record(ipath, public), "output_shape": shape, "timestamps_s": times,
                          "request": {"text": "Repaint the masked box red"} if task == "editing" else {}})
            targets[ident] = record(tpath, private)
    manifest = {"schema": "womi.dataset.v1", "protocol_version": "0.2.0", "id": "analytic-rooms-v1",
                "scope": "synthetic_diagnostic", "license": "MIT", "cases": cases}
    write_json(public/"manifest.json", manifest)
    write_json(private/"targets.json", {"schema": "womi.targets.v1", "dataset_sha256": file_hash(public/"manifest.json"),
                                        "cases": targets})
    return public/"manifest.json", private/"targets.json"

