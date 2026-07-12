---
title: Review: Stop JSON Output
type: review
updated: 2026-07-01 23:45
sources:
  - hooks/codex_guard.py
  - tests/test_codex_guard.py
  - wiki/contracts/2026-07-01-stop-json-output.md
---

# Review: Stop JSON Output

## Verdict

PASS

## Contract coverage

- `Stop` emits valid JSON on stdout whenever it emits output.
- Reminder-only Stop output uses `systemMessage`, not `hookSpecificOutput.additionalContext`.
- Hard-block Stop output uses `decision: block` and `reason`, then exits `0` so Codex continues instead of reporting hook failure.
- Wiki and GAN gate messages are aggregated into one JSON object.
- Direct `enforce_wiki` and `enforce_gan` behavior remains compatible for existing tests.

## Diff risk

- touched files: `hooks/codex_guard.py`, `tests/test_codex_guard.py`, `wiki/contracts/2026-07-01-stop-json-output.md`, `wiki/hooks/codex-guard.md`, `wiki/index.md`, `wiki/log.md`
- risky paths: `hooks/codex_guard.py`, hook wiki and contract/review artifacts
- unrelated changes: `config.toml` has pre-existing local user changes and is excluded from this scoped patch.

## Validation evidence

- tests run:
  - `python3 -m py_compile hooks/codex_guard.py tests/test_codex_guard.py`
  - `python3 -m unittest discover -s tests`
  - manual Stop reminder/block JSON parse simulation
  - `git diff --check` on scoped files
  - wiki index link check
- outputs:
  - `py_compile`: exit 0
  - `unittest`: `Ran 18 tests`, `OK`
  - manual reminder parse: `{"systemMessage": "..."}`
  - manual block parse: `{"decision": "block", "reason": "..."}`
  - wiki index link check: `missing links: none`

## Issues

Initial review returned `REVISE` because it included an unrelated `config.toml` working-tree diff. Re-review scoped to the Stop JSON patch returned `PASS`.

## Required fixes before merge

None.

## Wiki ingest check

- [x] wiki/index.md updated
- [x] wiki/log.md updated
- [x] durable hook page updated
- [x] contract page added

## See Also

- [Stop JSON Output Contract](../contracts/2026-07-01-stop-json-output.md)
- [Codex Loop Harness](../hooks/codex-guard.md)
