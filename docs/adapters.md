# Bring a model

Inference is separate from scoring. Choose a frozen task manifest the model supports. Produce a portable submission directly or implement:

```python
def predict(case, inputs):
    # case: id, task, output_shape, timestamps_s, request
    # inputs: permitted RGB, calibrated cameras, optional actions/edit mask
    return {"rgb": predicted_uint8_frames}  # or {"depth": depth_z_meters}
```

```bash
womi predict --dataset campaign/public/manifest.json \
  --adapter your_package.adapter:predict --name YourModel \
  --revision EXACT_CHECKPOINT_AND_ADAPTER_REVISION --kind model \
  --output runs/your-model
```

Load the checkpoint once. Declare cold-start separately: the runner times each function call plus serialization/hashing, excludes public-input loading, and does not attest GPU synchronization, peak memory or hardware. Declare warmup, sampling and synchronization in the campaign card. Adapters are trusted code, not sandboxed. Keep protected targets and secrets on a separate host; never tune preprocessing, scale or sample selection against targets.

## Depth export bridges

`examples/exported_depth.py` converts saved outputs. Store `<case-id>.npz` files with one `values` array in an isolated directory. Set `WOMI_EXPORT_ROOT`, `WOMI_DEPTH_CONVENTION` and the predeclared `WOMI_METERS_PER_UNIT`; use `--adapter examples.exported_depth:predict` from the repository root on a geometry-only manifest.

| Convention | Source shape | Conversion |
| --- | --- | --- |
| `mapanything-depth-z` | Stacked `depth_z`, `[N,H,W,1]` | Remove final singleton |
| `pi3-local-points` | `local_points`, `[1,N,H,W,3]` | Select camera-local Z |
| `da3-depth` | `prediction.depth`, `[N,H,W]` | Preserve axes |

Meters-per-unit must be known independently of targets. Scale-ambiguous models need a separately specified scale-normalized study. Resolution and calibration must match the manifest; bridges do not reverse cropping/resampling.

These are **tested format conversions, not qualified model inference integrations**. No scores are claimed. Pin source/checkpoints and consult primary documentation:

- [MapAnything](https://github.com/facebookresearch/map-anything): `depth_z` differs from depth along the ray.
- [Pi3/Pi3X](https://github.com/yyfz/Pi3): local points differ from world points; code and checkpoint licenses differ.
- [Depth Anything 3](https://github.com/ByteDance-Seed/Depth-Anything-3): processed resolution and extrinsic convention require explicit handling.

Record the exact model variant's licenses. WoMI-Bench's MIT license does not cover external weights or code.
