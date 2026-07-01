---
title: Review: Session Isolation Hardening
type: review
updated: 2026-07-01 23:18
sources:
  - hooks/codex_guard.py
  - tests/test_codex_guard.py
  - wiki/contracts/2026-07-01-session-isolation-hardening.md
---

# Review: Session Isolation Hardening

## Verdict

PASS

## Contract coverage

- Explicit session IDs still produce separate hook meta/state paths.
- Codex process scope is used only when the process tree identifies an actual Codex process.
- Terminal-only environment variables such as `TMUX`, `WT_SESSION`, `STY`, `SSH_TTY`, and `TERM_SESSION_ID` are no longer used as cross-session identity.
- Unknown-session fallback now uses hook process pid plus process start time, with a per-process nonce fallback when `/proc` is unavailable.
- Existing gates continue to pass under the expanded test suite.

## Diff risk

- touched files: `hooks/codex_guard.py`, `tests/test_codex_guard.py`, `wiki/contracts/2026-07-01-session-isolation-hardening.md`, `wiki/hooks/codex-guard.md`, `wiki/index.md`, `wiki/log.md`
- risky paths: `hooks/codex_guard.py`, hook wiki and contract/review artifacts
- unrelated changes: `config.toml` already had local changes outside this patch scope and was not edited for this fix.

## Validation evidence

- tests run:
  - `python3 -m py_compile hooks/codex_guard.py tests/test_codex_guard.py`
  - `python3 -m unittest discover -s tests`
  - manual session identity check for explicit and forced fallback cases
  - wiki index link check
- outputs:
  - `py_compile`: exit 0
  - `unittest`: `Ran 15 tests`, `OK`
  - manual identity check: explicit sessions became separate `session-a.pid...` / `session-b.pid...`; forced terminal-only unknown fallback became `unknown-cwd-...hookpid<pid>-<start>`
  - wiki index link check: `missing links: none`

## Issues

Initial review returned `REVISE` because `.hookpid<pid>` alone could collide after PID reuse while stale hook state remained on disk. The fix added process start time and a nonce fallback.

## Required fixes before merge

None.

## Wiki ingest check

- [x] wiki/index.md updated
- [x] wiki/log.md updated
- [x] durable hook page updated
- [x] contract page added

## See Also

- [Session Isolation Contract](../contracts/2026-07-01-session-isolation-hardening.md)
- [Codex Loop Harness](../hooks/codex-guard.md)
