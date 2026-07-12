---
title: Harness Policy
type: codex-config
updated: 2026-07-12 22:59
sources:
  - harness_policy.yaml
  - hooks/codex_guard.py
---

# Harness Policy

`harness_policy.yaml` controls the Codex Loop Harness without editing Python for routine policy changes.

## Thresholds

- `contract_net_new_lines: 150`: ordinary code changes at or above this size need a short contract.
- `review_net_new_lines: 300`: ordinary code changes at or above this size need a reviewer.
- `incremental_reminder_lines: 300`: after review, another 300 attributed lines can request a checkpoint re-review.
- `new_file_min_lines: 80`: only controls which new files enter incremental telemetry; a new file does not trigger review by itself.
- `incremental_new_files: 5`: five qualifying files since review can request a checkpoint re-review.
- `large_change_lines: 300`: classifies the size tier used by telemetry.
- `large_change_new_files: 999`: effectively disables ordinary new-file-count classification as a standalone gate.

## Enforcement Modes

Supported policy modes are:

- `observe`
- `remind`
- `block`

The default and medium tiers are `observe`. Contract/review size thresholds create one short `PostToolUse` nudge; ordinary large changes remain advisory and Stop is silent. Risky or harness-self changes use `block`, and only objective missing contract, PASS review, or validation evidence becomes a Stop blocker. A changed review with `FAIL` or `NEEDS_HUMAN` also blocks strict changes.

Missing wiki ingest is `observe`, so it records state without user-facing Stop output.

## Risky Paths

Hard-risk patterns include:

- `hooks/**`, `hooks.json`, `harness_policy.yaml`, `.codex/**`
- auth, migration, deploy, CI workflow, sandbox, and permission-related paths

Harness self-modification is the narrower `hooks/**`, `hooks.json`, and `harness_policy.yaml` set. `AGENTS.md`, `SCHEMA.md`, ordinary documentation, and general configuration are not hard-risk by path alone.

Risk, architecture, and security/performance prompt signals only matter after concrete code telemetry exists. Planning or discussion alone cannot activate a gate.

## Generated Paths

Generated/cache paths such as `.git/**`, cache/tmp directories, build/dist outputs, virtualenvs, bytecode caches, node modules, data, probes, and scratch are ignored by diff telemetry.

## Validation Markers

Validation evidence is detected from shell commands containing markers such as `py_compile`, `unittest`, `pytest`, `ruff`, `mypy`, `tsc`, `npm test`, `bun test`, `cargo test`, or `go test`.

## See Also

- [Codex Loop Harness](../hooks/codex-guard.md)
- [Stop Enforcement ADR](../decisions/adr-0001-stop-enforcement-policy.md)
- [Git Boundaries](git-boundaries.md)
