---
title: Codex Loop Harness
type: lifecycle-hook
updated: 2026-07-01 20:56
sources:
  - hooks.json
  - hooks/codex_guard.py
  - harness_policy.yaml
  - tests/test_codex_guard.py
---

# Codex Loop Harness

`hooks/codex_guard.py` is the lifecycle hook dispatcher for the Codex Loop Harness. It coordinates wiki memory, contract-first execution, diff telemetry, risk-based review gates, validation evidence, trace logging, and Stop enforcement.

The loop target is:

`Bootstrap -> Contract -> Work -> Verify -> Review -> Ingest -> Trace -> Restart`

## Lifecycle Events

- `UserPromptSubmit`: starts turn state, classifies implementation prompts, records code/wiki baselines, records contract/review artifact baselines, injects wiki and loop-harness reminders.
- `SessionStart`: reminds agents to query wiki and keep contract/review/validation requirements active after startup, resume, clear, or compact.
- `PostToolUse`: tracks concrete file side effects through snapshots, records diff telemetry, risk flags, reviewer activity, validation commands, wiki edits, and trace records.
- `Stop`: evaluates objective missing requirements. Small/medium changes can remind; large or risky changes can hard-block when contract, PASS review artifact, or validation evidence is missing.

Unexpected hook errors remain fail-open and are appended to `/tmp/codex-hook-errors.log`.

## Policy-Driven Gates

`harness_policy.yaml` externalizes thresholds, enforcement modes, risky paths, generated paths, and validation command markers. The Python hook keeps safe defaults, but project policy is read from the project root when available.

The policy supports three enforcement modes:

- `observe`: write trace only.
- `remind`: emit hook additional context and return success.
- `block`: return `2` on the first known missing objective requirement.

Hard blocks are limited to verifiable missing artifacts/evidence, not subjective quality.

## Contract Gate

Non-trivial work should create `wiki/contracts/<YYYY-MM-DD>-<task-slug>.md`. A valid contract includes:

- Original request
- Scope
- Non-goals
- Acceptance criteria
- Required validation
- Risk class
- Reviewer checklist

For large or risky changes, Stop blocks if no valid contract artifact exists. Existing valid contracts can be reused across turns and resumes, while review artifacts remain tied to the current risky change.

## Review Artifact Gate

Large or risky changes require `wiki/reviews/<YYYY-MM-DD>-<task-slug>-review.md`. A valid review includes:

- Verdict
- Contract coverage
- Diff risk
- Validation evidence
- Issues
- Required fixes before merge
- Wiki ingest check

`Verdict` must be `PASS` for the gate to pass. `FAIL`, `NEEDS_HUMAN`, missing verdict, or missing review sections block large/risky changes.

## Diff Telemetry And Risk

The harness observes actual filesystem state, not agent self-report. It builds snapshots from `git ls-files --cached --others --exclude-standard`, falling back to a filesystem walk.

Risk is triggered by size or path:

- review threshold: configured net new code lines or new files;
- large threshold: configured larger line/file count;
- risky path: policy patterns such as hooks, `AGENTS.md`, `SCHEMA.md`, config, auth, migrations, deploy, CI, sandbox, or permission files;
- harness self-modification: changes to hook/policy/bootstrap/schema files.

Generated/cache paths are excluded by policy.

## Validation Evidence

The hook records validation evidence when shell commands include configured markers such as `py_compile`, `unittest`, `pytest`, `ruff`, `mypy`, `tsc`, `npm test`, `bun test`, `cargo test`, or `go test`.

For large or risky changes, Stop can block if no validation evidence was observed.

The hook also automatically compiles changed Python files and attempts TypeScript checking when TypeScript files changed.

## Trace And Restart

Per-session trace lives under:

`~/.codex/tmp/hooks/<session_id>/trace.jsonl`

Per-session restart state lives under:

`~/.codex/tmp/hooks/<session_id>/state.json`

Trace records include prompt classification, session reminders, changed files, line deltas, risk flags, validation messages, gate decisions, missing requirements, and Stop outcomes.

`wiki/log.md` remains durable project history and does not receive noisy per-session trace.

## Tests

`tests/test_codex_guard.py` covers line-count review triggers, risky path triggers including CI workflow paths, generated/cache exclusions, repeated Stop blocking while objective requirements remain missing, large-change missing contract/review blocks, existing contract reuse, PASS review success, small-change reminder behavior, and wiki ingest reminder behavior.

## See Also

- [Harness Policy](../config/harness-policy.md)
- [Stop Enforcement ADR](../decisions/adr-0001-stop-enforcement-policy.md)
- [Codex Loop Harness Contract](../contracts/2026-07-01-codex-loop-harness.md)
- [Runtime State](../ops/runtime-state.md)
