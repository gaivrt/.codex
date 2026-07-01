---
title: Contract: Codex Loop Harness
type: decision
updated: 2026-07-01 20:46
sources:
  - hooks/codex_guard.py
  - hooks.json
  - SCHEMA.md
  - wiki/hooks/codex-guard.md
---

# Contract: Codex Loop Harness

## Original Request

Upgrade the current Wiki Gate + GAN Review Gate harness into a contract-driven, traceable Codex Loop Harness:

`Bootstrap -> Contract -> Work -> Verify -> Review -> Ingest -> Trace -> Restart`

## Scope

Allowed changes:

- `hooks/codex_guard.py`
- `harness_policy.yaml`
- `AGENTS.md`
- `SCHEMA.md`
- `wiki/**`
- `tests/**`

## Non-Goals

- Do not read or ingest credentials, sqlite databases, session transcripts, cache, tmp, or standalone binaries.
- Do not change remote Git state.
- Do not rewrite unrelated skills or installed package assets.
- Do not make subjective code-quality judgments hard-blocking in hooks.

## Acceptance Criteria

- [ ] Policy thresholds and enforcement modes are loaded from `harness_policy.yaml` with safe defaults.
- [ ] Risk-based review triggers include harness self-modification, hook/config/schema/auth/migration/deploy/CI style paths.
- [ ] Large or risky code changes hard-block at Stop when contract artifact is missing.
- [ ] Large or risky code changes hard-block at Stop when review artifact is missing.
- [ ] Review artifacts require a `Verdict` of `PASS`; `FAIL` and `NEEDS_HUMAN` block.
- [ ] Validation evidence is tracked; large/risky changes can block when no evidence is seen.
- [ ] Per-session `trace.jsonl` records classification, telemetry, gate decisions, validation, and Stop decisions outside `wiki/log.md`.
- [ ] Wiki ingest reminders still work and remain distinct from trace logging.
- [ ] Hook errors remain fail-open for unexpected exceptions.

## Required Validation

- [ ] `python3 -m py_compile hooks/codex_guard.py`
- [ ] `python3 -m unittest discover -s tests`
- [ ] Manual review of `wiki/index.md` links after ingest updates.

## Risk Class

risky

Reason: the task modifies the harness itself: `hooks/codex_guard.py`, `AGENTS.md`, `SCHEMA.md`, and wiki policy pages.

## Reviewer Checklist

- [ ] Does the implementation satisfy the contract?
- [ ] Are hard blocks limited to objective missing artifacts/evidence?
- [ ] Are small changes still reminder-only or observe/remind?
- [ ] Are risky paths recognized even for small diffs?
- [ ] Does trace logging avoid polluting `wiki/log.md`?
- [ ] Are secrets/runtime paths still excluded from ingest and tracking?
- [ ] Are tests meaningful and runnable with stdlib tooling?
- [ ] Was wiki ingest completed after durable changes?

## See Also

- [Codex Guard](../hooks/codex-guard.md)
- [Wiki Log](../log.md)
