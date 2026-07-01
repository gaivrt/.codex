---
title: Contract: Session Isolation Hardening
type: contract
updated: 2026-07-01 23:18
sources:
  - hooks/codex_guard.py
  - tests/test_codex_guard.py
  - wiki/hooks/codex-guard.md
---

# Contract: Session Isolation Hardening

## Original request

Investigate and fix the risk that hook state can interfere across different Codex sessions.

## Scope

- `hooks/codex_guard.py`
- `tests/test_codex_guard.py`
- `wiki/hooks/codex-guard.md`
- `wiki/index.md`
- `wiki/log.md`
- `wiki/reviews/*-review.md`

## Non-goals

- Do not change user runtime config such as `config.toml`.
- Do not delete existing hook runtime state under `tmp/hooks`.
- Do not read credentials, sqlite databases, session transcripts, or cache content.
- Do not weaken explicit `session_id` or `turn_id` handling.

## Acceptance criteria

- [ ] Explicit session IDs still produce separate hook meta/state paths.
- [ ] Codex process scope is used only when it identifies a Codex process.
- [ ] Terminal-only environment variables such as `TMUX` or `WT_SESSION` are not used as cross-session identity.
- [ ] When no reliable session/thread/process identity exists, the hook fails open per hook process instead of sharing state across sessions.
- [ ] Existing contract/review/wiki/validation gates continue to pass.

## Required validation

- [ ] `python3 -m py_compile hooks/codex_guard.py tests/test_codex_guard.py`
- [ ] `python3 -m unittest discover -s tests`
- [ ] Manual inspection of generated session IDs for explicit and fallback cases.

## Risk class

risky

Reason: the change modifies `hooks/codex_guard.py`, which is part of the harness enforcement path.

## Reviewer checklist

- [ ] Does the fix prevent terminal-only scope from mixing different sessions?
- [ ] Does the fallback fail open rather than block work with stale shared state?
- [ ] Does the change preserve explicit session and Codex process isolation?
- [ ] Are tests focused on session isolation and not dependent on real user state?
- [ ] Was wiki ingest completed for durable design changes?

## See Also

- [Codex Loop Harness](../hooks/codex-guard.md)
- [Wiki Log](../log.md)
