# Analytic Rooms v1 — calibration data card

**Author:** Maxime Sebti. **License:** MIT. **Purpose:** metric calibration, software tests and report examples. **Not a learned-model leaderboard dataset.**

`womi demo` creates eight worlds by default (40 cases). Counts 2–64 are supported. Each has five tasks, 32×48 RGB/depth images, explicit cameras and ray/axis-aligned-box intersections. Three colored boxes, a floor and back wall define targets; no learned generator supplies truth. Seeds are `4400 + world index`.

Spatial queries change camera position; geometry uses two observed views; persistence revisits a fixed scene; editing repaints a masked box; dynamics translates a box at constant velocity after three observations. This is analytic kinematics, not validated rigid-body simulation. There are simple materials, no personal data and no external asset/checkpoint downloads.

Targets are in a separate directory to demonstrate the interface. Source and targets are public and reconstructible, so a model can memorize or solve the suite analytically. It cannot establish private generalization or which learned model is best.

## Controls

- **last-frame:** copy the last observed RGB for every query; constant 4 m depth.
- **linear-pixels:** same, except dynamics extrapolates clipped per-pixel changes from the last two observations. Not optical flow or object-motion reasoning.
- **black:** zero RGB/depth; zero depth receives the worst penalty.

Unit tests use privileged target copying for metric ceilings; it is never a published model result. Previews use the fixed first successful case in manifest order, not visual-quality selection; reports identify the case.

External datasets need provenance, redistribution permission, calibration, target-generation methods, validity masks, independent-world grouping, split/contamination policy and limitations. MIT for these fixtures grants no rights to other datasets.
