---
title: Harness Policy
type: codex-config
updated: 2026-07-01 20:56
sources:
  - harness_policy.yaml
  - hooks/codex_guard.py
---

# Harness Policy

`harness_policy.yaml` controls the Codex Loop Harness without editing Python for routine policy changes.

## Thresholds

- `review_net_new_lines`: net new lines that require review.
- `incremental_reminder_lines`: additional lines since last review that trigger another reminder.
- `new_file_min_lines`: minimum new-file size counted as review-relevant.
- `incremental_new_files`: new-file count since last review that triggers another reminder.
- `large_change_lines`: net new lines that classify a change as large.
- `large_change_new_files`: new-file count that classifies a change as large.

## Enforcement Modes

Supported modes:

- `observe`
- `remind`
- `block`

Current policy keeps default and medium changes in reminder mode, while large, risky, and harness self-modifying changes can block when objective requirements are missing.

Known missing requirements that can block:

- contract missing for large/risky change;
- review artifact missing for large/risky change;
- validation evidence missing for large/risky change;
- review verdict is `FAIL` or `NEEDS_HUMAN`.

Wiki ingest remains reminder-only by default.

## Risky Paths

Risk patterns include:

- `hooks/**`, `hooks.json`, `harness_policy.yaml`
- `AGENTS.md`, `SCHEMA.md`
- auth, migration, deploy, CI, config, sandbox, and permission-related paths

Harness self-modification is tracked separately so even tiny changes to hook/policy/bootstrap/schema files can require the stricter gate.

## Generated Paths

Generated/cache paths such as `.git/**`, cache/tmp directories, build/dist outputs, virtualenvs, bytecode caches, and node modules are ignored by diff telemetry.

## Validation Markers

Validation evidence is detected from shell commands containing markers such as `py_compile`, `unittest`, `pytest`, `ruff`, `mypy`, `tsc`, `npm test`, `bun test`, `cargo test`, or `go test`.

## See Also

- [Codex Loop Harness](../hooks/codex-guard.md)
- [Stop Enforcement ADR](../decisions/adr-0001-stop-enforcement-policy.md)
- [Git Boundaries](git-boundaries.md)
