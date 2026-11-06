# Evaluation Design

Status: Proposed — Phase 0

## Goal

Evaluate whether the community fine-tune is better than the base model at **tool use / function calling** without unacceptable regressions in general instruction following or safety.

## Baselines

- Base model with a fixed system prompt.
- Base model with the same tool schemas.
- Optional: a similar-size open instruct model as context.

## Test sets

1. **Public tool-use benchmark**
   - BFCL-style function-calling tasks if available and licensed.
   - Or a comparable public tool-calling benchmark.

2. **Custom held-out tool schemas**
   - 50–100 tool schemas not present in training.
   - Single-tool and multi-tool calls.
   - Required and optional arguments.
   - Nested JSON.
   - Ambiguous requests that should trigger clarification.
   - Requests that should not call a tool.

3. **General instruction following**
   - Small public held-out set.
   - Checks for regression.

4. **Safety**
   - Refusal of clearly harmful requests.
   - No credential harvesting.
   - No dangerous tool invocation without confirmation.
   - Prompt-injection resistance in tool descriptions.

## Primary metric

**Valid tool-call rate** on the custom held-out set.

A tool call is valid if:

- the correct tool is selected;
- arguments match the schema;
- required arguments are present;
- values are semantically correct;
- no tool is called when none is appropriate.

## Secondary metrics

- Exact tool selection accuracy.
- Argument accuracy.
- JSON validity.
- Clarification rate on ambiguous requests.
- General instruction-following score.
- Safety pass rate.
- p50/p95 latency.
- Tokens/sec.
- Cost per 1M tokens.

## Thresholds

- Primary metric must beat the base model by at least 5 percentage points **on a non-saturated, domain-specific test set**.
- General regression must be no more than 2 percentage points on the generic hard set.
- Safety must pass the release checklist.
- Latency must fit the target agent workflow.
- Cost must fit the proposed points/price model.

### Saturation rule

If the base model scores 95% or higher on the generic benchmark, that benchmark is a regression guard, not an improvement metric.

In that case:

- Create a harder, narrower test set where the base model has headroom.
- Report both generic regression and domain-specific improvement.
- Do not claim fine-tune value from a saturated benchmark.

## Human review

- Sample 30–50 outputs.
- Blind comparison where possible.
- Two reviewers if available.
- Record disagreements.
- Do not use test prompts in training.

## Reporting

- `results.json`
- `summary.json`
- `safety.json`
- Model card table
- Known weaknesses
- Failure examples
- Sample sizes
- Confidence intervals where possible

## Eval set versioning and ownership

- Eval sets are versioned and immutable once used for a release.
- Eval sets have separate owners from tuning recipes.
- A pull request may not change a recipe and its eval set together.
- Any eval change gets a new version and published before/after results.
- The recipe manifest records the eval set id, version, and SHA256.
- A released model links the eval version it was measured against.

## Rules

- Fix the evaluation config before training.
- Never train on the test set.
- Publish raw results or link them.
- Do not cherry-pick examples.
- Do not claim general capability from a tool-use benchmark.
