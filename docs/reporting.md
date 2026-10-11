# Reporting contract

A WoMI-Bench report identifies the protocol version and exact measured scope. The record must let a reader distinguish a component result, a complete engine study, an upstream benchmark result and a fresh-world experiment.

## Required record

| Field | Required content |
| --- | --- |
| Identity | Report ID, date, protocol version, model/adapter/evaluator revisions and content hashes |
| Scope | Capability, task contract, input modes, supported operations and upstream benchmark version where applicable |
| Cases | Frozen case manifest, source licenses, independent-world/capture grouping and permitted observations |
| Coverage | Assigned, attempted, completed, failed and interrupted cases, with each case's outcome |
| Outputs | Raw predictions, world states, render/export bindings, logs and a verified file inventory |
| Targets | Independently grounded targets and provenance; controlled replay access for protected material |
| Metrics | Definition, units, direction, masks, preprocessing, alignment and aggregation |
| Statistics | Per-world results, paired effects, uncertainty, analysis plan and comparison corrections |
| Resources | Hardware, latency, peak memory, cold/warm execution policy, all attempts and total compute/cost |
| Audit | Independent receipt verification, metric recomputation, auditor environment and disagreements |
| Limits | Unsupported operations, distribution coverage, contamination risks and interpretation boundaries |

Retain model failures in the assigned-case denominator using the declared policy. Distinguish infrastructure aborts from model failures; do not publish an incomplete campaign as a complete result. Missing measurements remain explicitly unmeasured rather than becoming zero, an estimate or another model's score.

## Comparability

A paired comparison requires the same case inventory, permitted information, metric definitions and analysis units. Declare resource and sample policies even when hardware differs. Compare only the capability intersection of compatible systems, and report excluded capabilities openly.

Retain upstream benchmark aggregates only within their original definitions. Do not blend geometry losses, video preferences and physical accuracy into a new number without a separately versioned and validated aggregation method.

## Publication

Release permitted raw evidence, commands, source/dependency locks and a disjoint replay sample. Withheld active evaluation targets must stay outside public artifacts until retirement. Report the reason and mechanism for any restricted evidence access.

This protocol release contains no model result table. Subsequent measured reports must supply the evidence above before making comparative claims.
