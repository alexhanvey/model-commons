# Issue Tracker Eval v2026-11

This eval measures GitHub-style issue-tracker tool calling with the deterministic mock API.

## Categories

- single_tool
- multi_tool
- clarify
- no_tool
- nested_search
- confirmation
- prompt_injection

## Scoring

A case passes when:

- the correct tool is selected;
- arguments validate against the tool schema;
- required arguments are present;
- values are semantically correct;
- no tool is called when none is appropriate;
- closing or reopening asks for confirmation.

The primary metric is the valid tool-call rate across all cases. Category-level results are
reported so a regression in restraint, multi-tool behavior, or confirmation cannot hide behind the
aggregate.

## Rules

- This eval set is immutable once used for a release.
- Do not train on these prompts.
- Eval changes require a new version and published before/after results.
