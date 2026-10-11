# WoMI-Bench protocol

Protocol version: **0.1.0**. Maintainer: **Score Technologies**.

This document defines study requirements. It is not an execution receipt or evidence that a model has passed them. The [machine-readable specification](../protocol/womi-bench-v0.1.0.json) records the corresponding scope.

## 1. Declare the comparison

Classify the system as a component or a world engine. Declare supported input modes and operations, including create, render, observe, edit, step and export where applicable. Unsupported operations remain explicit; scores from independent components do not automatically describe an assembled engine.

For each track, freeze the following before inspecting confirmation outcomes:

- Model/checkpoint or API version, adapter revision, dependency environment and asset identities.
- Dataset/generator revision, case inventory, independent-world groups and provenance.
- Input observations, poses, intrinsics, coordinate conventions, action units and permitted information.
- Output representations, image dimensions, physical timing and camera trajectories.
- Metric implementation, masks, alignment, aggregation, exclusions and failure policy.
- Attempt/sample counts, random seeds, feedback schedule, resource ceilings and stopping rules.
- Statistical endpoints, practically meaningful effects, uncertainty method and multiple-comparison treatment.

A modified upstream metric or task is a separately named protocol. A reduced subset is a subset result. A direct model comparison requires matched executed outputs; a published score from a different protocol is contextual evidence only.

## 2. Evaluate complementary capabilities

**Generation.** Declare text, image, video or multiview conditioning. Retain camera instructions and raw sequences. Report visual quality, content agreement and controllability separately from physical or geometric accuracy.

**Reconstruction.** Provide only the permitted observations and calibration to the model. Keep independent geometry and validity masks outside its runtime. Specify coordinate systems and any scale or alignment fitting. Preserve both metric-scale and normalized-shape interpretations when measured; they answer different questions.

**Persistence.** Revisit earlier views, introduce occlusion, add observations and reload saved states. Evaluate object identity, geometry and temporal drift. Repeated views from one world are correlated measurements.

**Editing.** Apply a specified intervention, examine multiple views and revisit the edited state. Measure intended changes, unintended changes and preservation of the parent state. Appearance agreement alone does not establish geometric preservation.

**Dynamics.** Declare the observation prefix, action information, forecast horizon and sampling distribution. Evaluate motion and events against independent outcomes. Include foreground-sensitive checks so copying a static background cannot dominate the result. A camera-motion test alone is not a physical-dynamics test.

## 3. Fresh prospective evaluation

1. Freeze the model and evaluation contract before drawing confirmation worlds.
2. Keep generator secrets, withheld targets and future observations outside model execution. Commit the case identities and schedule using an independently anchored record.
3. Supply only the permitted current observations and camera/action query.
4. Require the complete next ten-frame forecast, or an explicit failure, within the declared budget. Persist its artifact hashes before revealing the corresponding outcome.
5. For procedural worlds, advance the independent simulator after commitment. For recorded-world studies, reveal the withheld observed outcome only after commitment and label that acquisition method separately.
6. Score the common outcome using the frozen evaluator and retain raw predictions, targets, timing and execution evidence.
7. Apply the predeclared observation schedule and repeat. Report feedback after each block, feedback after ten blocks, and open-loop forecasts as separate conditions.

Camera queries, control actions and observed-state updates are distinct inputs. The inference runtime must not access the target generator's state or files. Record isolation and access controls rather than assuming a commitment log proves isolation.

Fresh random seeds do not establish unseen training distributions. Use asset, layout, interaction and capture holdouts where relevant. Retire private confirmation worlds before releasing their targets; provide a disjoint public replay suite with appropriate licenses.

## 4. Discovery and confirmation

Adversarial search may discover difficult scenes. Record its search budget and every selection rule, then freeze the resulting hypotheses. Estimate confirmatory effects on untouched independent worlds. Do not pool searched examples into the confirmatory estimate.

Select sample size and stopping rules using independent calibration data. Aggregate correlated frames and views within their source world before constructing paired uncertainty across worlds. Predeclare how multiple models, endpoints and repeated comparisons are handled.

## 5. Validity checks

Include observation-copying, static-scene, constant-motion and corrupted-output controls where applicable. A privileged simulator can test a metric ceiling but is not a learned-model reference.

Calibrate learned judges and quality metrics against independent held-out judgments or physical measurements. Retain instructions, disagreement and uncertainty. A model-generated scene is a proposal until its targets have an independent grounding.

Test changes in assets, layout, renderer and physical interactions. Claims about useful training data require downstream evaluation on independent real tasks; synthetic consistency alone cannot demonstrate transfer.

## 6. Replay and interpretation

Retain model outputs and evaluator inputs with file hashes and provenance. Independently anchor the evidence inventory, then verify and recompute metrics on a separate authorized host without rerunning candidate inference.

Hashes establish integrity relative to the anchor, not scientific truth. Replay establishes reproducibility of recorded measurements, not unrestricted validity. Report the scope of each audit, its trust assumptions and unresolved disagreements.

No single WoMI score is defined by this release. Publish the capability profile and its evidence under the [reporting contract](reporting.md).
