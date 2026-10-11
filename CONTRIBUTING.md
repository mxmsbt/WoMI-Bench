# Contributing to WoMI-Bench

Maintained by Maxime Sebti as an independent research project. Read the [governance and conflicts](GOVERNANCE.md) and [adoption roadmap](docs/roadmap.md). All models use the same evidence rules.

Use GitHub issues to propose protocol changes, reference adapters, replay tooling or validation studies. Submit focused pull requests with the problem, proposed behavior and evidence supporting the change.

For a new metric, specify the task, units, direction, failure behavior, independent statistical unit and known shortcuts. Include a plan for validating the metric against held-out human judgments or physical evidence. For an adapter, document inputs, outputs, model/dependency revisions, licenses, resource limits and replay instructions.

Protocol changes must receive a new version when they change the meaning of a measurement. Preserve prior manifests and measured reports. Never silently replace difficult cases, choose successful samples after inspecting targets or reclassify a partial run as complete.

Contributions must be yours to publish. Keep credentials, proprietary model artifacts, restricted datasets, private evaluation targets and identifying operational logs out of commits. Attribute upstream work and preserve its license.

By contributing, you agree that your original contribution is offered under this repository's MIT License. Separately licensed upstream material must remain clearly identified.

For code changes, install `.[test]`, run `python -m pytest -q`, and test meaningful behavior. Schema/score changes require versioning and preserve prior evidence. New model results require a submission and review record.
