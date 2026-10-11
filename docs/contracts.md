# Executable contracts — v0.2.0

All bundles are JSON indexes plus numeric, pickle-free NPZ arrays. `womi validate` checks the public input contract; `womi evaluate` checks targets and submissions as well. The generated demo is a complete example. `src/womi/contracts.py` is authoritative for this version.

## Public dataset

`manifest.json` contains schema `womi.dataset.v1`, protocol_version `0.2.0`, an ID, license, scope (`synthetic_diagnostic`, `development`, or `held_out`) and a frozen list of cases. A scope label is a declaration, not proof that data was unseen.

Each case has `id`, `world_id`, `task`, `input: {path, sha256}`, `output_shape: [T,H,W]`, `timestamps_s: [T]` and a `request` object. Group correlated captures/views under their source world. A task-specific campaign may contain just one task. Freeze it before inference; do not filter a completed run to its successful tasks.

| Input key | Contract |
| --- | --- |
| `rgb` | uint8 `[I,H,W,3]`, sRGB bytes |
| `intrinsics` | float `[I,3,3]`, positive focal lengths |
| `camera_to_world` | float `[I,4,4]`, rigid right-handed OpenCV axes: x right, y down, z forward |
| `query_intrinsics` | float `[T,3,3]` |
| `query_camera_to_world` | float `[T,4,4]`, translations in meters |
| `timestamps_s` | `[I]`, required for dynamics; strictly before future times |
| `edit_mask` | bool `[T,H,W]`, required for appearance editing |
| `actions` | Optional numeric array; declare units/meaning in the campaign |

Pixel centers are at `(column + 0.5, row + 0.5)` in the analytic fixture. Resize/crop transforms and corresponding intrinsics must be fixed in a real campaign. The evaluator never silently resizes, aligns or rescales an output.

Geometry queries equal observed cameras. Persistence returns to its first query camera and unchanged reference appearance. Appearance editing uses the last observed camera, with an unchanged region. Dynamics requires at least two future frames and independently annotated foreground. These offline tasks do not enforce an interactive state machine.

## Evaluator-only targets

`targets.json` contains schema `womi.targets.v1`, `dataset_sha256` and `cases: {id: {path, sha256}}`. Case coverage must be exact. Each target NPZ contains `valid: bool[T,H,W]` and either `rgb: uint8[T,H,W,3]` or `depth: float[T,H,W]` in camera-Z meters. Editing adds a `region` mask equal to the public edit mask. Dynamics adds a `foreground` mask, withheld from the model.

An independent capture, simulator or measurement must establish the target. For active tests, targets and generator secrets live outside the inference runtime. Public calibration targets are intentionally disclosed; their generator is not a hidden benchmark.

## Portable submission

`submission.json` contains schema `womi.submission.v1`, `dataset_sha256`, `system: {name, revision, kind}` and `cases`. Kind is `model` or `control`. A successful entry has `status: "ok"`, `output: {path, sha256}`, and nullable `runtime_seconds` / `cost_usd`. Failures have `status: "failed"` or `"missing"`. Absent assigned entries count as missing; extra entries abort scoring.

Outputs contain exactly `depth: float[T,H,W]` for geometry or `rgb: uint8[T,H,W,3]` otherwise. Nonfinite/wrong-shape predictions are failures. Changed hashes, absent promised files, incorrect targets or scope mismatches abort the report as integrity problems rather than producing a deceptively complete score.

Limits: 4,096 cases, eight million requested pixels per case, 128 MiB per NPZ and expanded payload, bounded NPY headers, no pickle/object arrays, symlinks or path traversal. These limits bound parsing; they are not a security certification. Use OS resource limits for untrusted evidence.

## Isolation and provenance

`womi predict` executes **trusted local Python** and is not a sandbox. Arguments omit target paths, but imported code can access the process filesystem and network. Protected evaluation needs inference on a separate machine/container without target mounts or credentials; retain output before exposing targets to the evaluator. Isolation, timing commitments, attempt limits and hardware receipts are the campaign operator's responsibility.

Hashes detect changes relative to an anchored record. A participant able to rewrite evidence and hashes can fabricate a self-reported bundle. Neither the package nor CI automatically authenticates scientific claims.
