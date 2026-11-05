# Model Cards

Model cards are added when a model version reaches the evaluation gate. Each card must include:

- Model and adapter identifiers, revision, and checksum.
- Base model, license, and training data provenance.
- Intended use and out-of-scope use.
- Evaluation harness, baseline, aggregate and category results.
- Latency, hardware, and serving configuration.
- Known failure modes and safety notes.
- Release status and approval.

Do not publish a model card that claims capability not supported by the recorded evaluation.

The first MVP model is `ibm-granite/granite-4.1-3b` base. The current adapters are research
artifacts and do not get a release card.
