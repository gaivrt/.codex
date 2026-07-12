---
title: Contract: Stop JSON Output
type: contract
updated: 2026-07-01 23:45
sources:
  - hooks/codex_guard.py
  - tests/test_codex_guard.py
  - https://developers.openai.com/codex/hooks
---

# Contract: Stop JSON Output

## Original request

Fix the `Stop hook (failed): hook returned invalid stop hook JSON output` error.

## Scope

- `hooks/codex_guard.py`
- `tests/test_codex_guard.py`
- `wiki/hooks/codex-guard.md`
- `wiki/index.md`
- `wiki/log.md`
- `wiki/reviews/*-review.md`

## Non-goals

- Do not change unrelated runtime config such as `config.toml`.
- Do not change hook discovery or `hooks.json`.
- Do not weaken contract, review, validation, or wiki gates.
- Do not delete existing runtime state under `tmp/hooks`.

## Acceptance criteria

- [ ] `Stop` hook exits with valid JSON on stdout whenever it emits output.
- [ ] `Stop` reminder output uses common fields such as `systemMessage`, not `hookSpecificOutput.additionalContext`.
- [ ] `Stop` hard-block output uses `decision: block` and `reason` so Codex continues with the reason as the next prompt.
- [ ] Wiki and GAN Stop messages are aggregated into one JSON object.
- [ ] Direct `enforce_wiki` and `enforce_gan` behavior used by tests remains compatible.

## Required validation

- [ ] `python3 -m py_compile hooks/codex_guard.py tests/test_codex_guard.py`
- [ ] `python3 -m unittest discover -s tests`
- [ ] Manual JSON parse check for Stop reminder and Stop block output.

## Risk class

risky

Reason: the change modifies `hooks/codex_guard.py`, which is part of the lifecycle enforcement path.

## Reviewer checklist

- [ ] Does the implementation match the official Codex Stop hook output contract?
- [ ] Does `hook_stop` emit at most one JSON object?
- [ ] Does block behavior continue the agent instead of failing the hook?
- [ ] Are reminder-only gates still non-blocking?
- [ ] Are tests focused on the reported invalid JSON failure mode?
- [ ] Was wiki ingest completed for durable design changes?

## See Also

- [Codex Loop Harness](../hooks/codex-guard.md)
- [Wiki Log](../log.md)
