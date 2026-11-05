# Phase 0 Checklist

Status: In progress
Goal: lock one user, capability, model, dataset, evaluation, GPU target, and points policy.

## 1. Scope

- [ ] Choose one target user.
- [ ] Write the user story in `docs/specs/mvp.md`.
- [ ] Choose one capability.
- [ ] Write explicit non-goals.
- [ ] Define MVP success metrics.
- [ ] Review scope with at least one other person.

## 2. Model

- [ ] Shortlist three permissively licensed 1B–3B base models.
- [ ] Check license and redistribution terms.
- [ ] Check tokenizer, context length, and chat template.
- [ ] Check VRAM for QLoRA and inference.
- [ ] Check tool-calling quality.
- [ ] Run a load and inference smoke test.
- [ ] Run a QLoRA smoke test.
- [ ] Choose one base model.
- [ ] Write ADR-0002.

## 3. Data

- [ ] Choose one public/permissive dataset or curated subset.
- [ ] Verify license and provenance.
- [ ] Check PII and sensitive content.
- [ ] Check duplication.
- [ ] Check benchmark contamination.
- [ ] Define train/validation/test splits.
- [ ] Compute checksums.
- [ ] Write dataset card.
- [ ] Write data policy.

## 4. Evaluation

- [ ] Define baseline model and prompt.
- [ ] Choose public tool-use benchmark.
- [ ] Build custom held-out tool schemas.
- [ ] Define safety checks.
- [ ] Define primary metric.
- [ ] Define regression threshold.
- [ ] Define latency and cost targets.
- [ ] Write `docs/evaluation.md`.

## 5. Points

- [ ] Draft earning rules.
- [ ] Draft spending rules.
- [ ] Define expiry and admin discretion.
- [ ] Confirm no cash value and no transfers.
- [ ] Confirm points are beta-only.
- [ ] Write `docs/points-policy.md`.

## 6. Legal

- [ ] Base model license reviewed.
- [ ] Dataset license reviewed.
- [ ] Open-weight release terms reviewed.
- [ ] Contributor terms drafted.
- [ ] Privacy policy drafted.
- [ ] Terms of service drafted.
- [ ] Points policy reviewed.
- [ ] Data contribution agreement drafted.
- [ ] Write `docs/legal/checklist.md`.

## 7. Architecture

- [ ] Confirm stack.
- [ ] Confirm deployment target.
- [ ] Confirm auth.
- [ ] Confirm GPU target.
- [ ] Confirm one trusted inference host.
- [ ] Write ADR-0001.

## 8. Validation

- [ ] Draft contributor interview guide.
- [ ] Draft user interview guide.
- [ ] Interview 10 potential contributors.
- [ ] Interview 10 potential users.
- [ ] Record notes.
- [ ] Summarize findings.
- [ ] Get at least 3 contributor commitments.
- [ ] Get at least 3 user commitments.

## 9. Technical spikes

- [ ] QLoRA smoke test on target GPU.
- [ ] vLLM serving test.
- [ ] `lm-evaluation-harness` run.
- [ ] Worker sandbox test.
- [ ] Artifact upload/download test.
- [ ] Record time, cost, VRAM, tokens/sec, failure modes.
- [ ] Write `docs/specs/spikes.md`.

## 10. Exit

- [ ] All decisions locked or explicitly accepted as risks.
- [ ] `docs/specs/mvp.md` complete.
- [ ] `docs/specs/decisions.md` updated.
- [ ] Legal checklist signed off.
- [ ] 3 beta commitments.
- [ ] Spikes passed.
- [ ] Ready to start Phase 1.
