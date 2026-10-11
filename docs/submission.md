# Submit a model or study

Open a [model submission issue](https://github.com/mxmsbt/WoMI-Bench/issues/new?template=model_submission.yml). Participate in one capability without implementing a whole engine. Public examples currently contain calibration controls, not ranked learned models.

## Required evidence

1. **Campaign card:** investigators/affiliations/conflicts, question/task, supported inputs, model/API/checkpoint/adapter revisions, licenses, frozen dataset/generator and permissions.
2. **Analysis plan:** case inventory, world groups, permitted observations, camera/time conventions, target provenance, metrics, attempts/samples, budgets, exclusions, stopping rule and endpoints. State whether fixed before seeing outcomes.
3. **Raw evidence:** manifests, outputs, permitted targets, hashes, logs and exact evaluator source. Include failed/interrupted attempts. Do not post active private targets; describe controlled replay access.
4. **Compute:** hardware, environment, sampling settings, cold/warm policy, latency, memory and actual cost. Unknowns stay unknown; resource comparisons need a common policy.
5. **Replay:** commands and a separate-host record with environment and recomputed measurements. Provenance and isolation need review separately; hashes cannot certify a study.

Admission follows the [reporting contract](reporting.md). Incomplete studies can be useful development reports, with missing evidence visible; editing a JSON label cannot make them independently reviewed.

## Publication

A maintainer adds a reviewed campaign through a pull request linking the submission, evidence and exact measurements. The current site accepts generated calibration reports only; adding model results requires a reviewed site change, not automatic ingestion of submitted HTML or code.

Distinguish self-reporting, separate-host recomputation and unaffiliated review. Maintainer-affiliated models require unaffiliated review for the final status. Corrections retain the old record and explain the change.

Useful contributions include a model adapter with a permitted replay sample, a grounded dataset/data card, a metric-validity study or a demonstrated shortcut. Controls winning for the wrong reason are scientific findings to investigate.
