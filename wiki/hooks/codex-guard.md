---
title: Codex Loop Harness
type: lifecycle-hook
updated: 2026-07-13 13:29
sources:
  - hooks.json
  - hooks/codex_guard.py
  - harness_policy.yaml
  - tests/test_codex_guard.py
  - AGENTS.md
  - SCHEMA.md
  - https://developers.openai.com/codex/hooks
---

# Codex Loop Harness

`hooks/codex_guard.py` implements Harness V3: an ordinary silent path and a small risk-only governed path. It does not use task size, line count, or ordinary new files as process signals.

The workflow is:

`Bootstrap -> Ordinary Work`

or, only when governed evidence appears:

`Bootstrap -> Contract -> Work -> Targeted Validation -> Review -> Stop`

## Lifecycle Events

- `UserPromptSubmit` starts isolated turn state and fingerprints the artifact directories. It also records sensitive implementation intent without treating prompt text as proof of a change.
- `SessionStart` performs the same hash-based bootstrap check without starting change state.
- `PostToolUse` is matched only for ApplyPatch/Write/Edit/MultiEdit/parallel tools, then looks for structured file paths. Calls without paths return before opening the governed state lock. Ordinary declared paths are recorded silently; governed evidence emits one short nudge.
- `Stop` returns silently for ordinary turns. A governed turn passes or emits one valid `{"decision":"block","reason":"..."}` object.

Unexpected hook errors append non-sensitive diagnostics to `/tmp/codex-hook-errors.log` and fail open.

## Bootstrap

Session meta stores the worktree scope plus hashes of `SCHEMA.md`, `wiki/index.md`, `AGENTS.md`, and `harness_policy.yaml`, including `policy_version`. The first event asks the agent to read the schema and index. Schema/index changes name only the file that must be reread. Guidance or policy changes ask for a new Codex session because an existing session may retain old instructions. Legacy V2 `wiki_bootstrap` state is recognized as a migration signal and receives the same restart guidance.

## Path Evidence

The hook accepts only paths declared by structured file tools:

- ApplyPatch parses `Add File`, `Update File`, and `Delete File` declarations from structured tool input.
- Write/Edit/MultiEdit use an explicit `file_path` or `path`.
- Nested calls in a parallel tool are inspected individually.

Bash/exec command strings are not parsed, even if they contain patch-looking text. This intentionally favors missed telemetry over attributing another process's writes to the current turn. There is no `git ls-files`, filesystem walk, repository snapshot, line accounting, or automatic compile/typecheck pass.

Generated/runtime paths configured by policy are discarded before state is opened.

## Governed Classification

A turn becomes governed through either:

- a declared path matching hook enforcement/policy, auth, migration, deploy, CI, sandbox, or permission patterns/tokens; or
- a positive sensitive implementation prompt paired with a later review-relevant code/config write.

Discussion and explicitly negated actions such as “不修改代码” do not count. Prompt intent without a structured write, and external operations without file evidence, stay outside the code-review gate. Ordinary `AGENTS.md`, `SCHEMA.md`, docs, and general config paths are not governed by path alone.

The first governed event writes a `GovernedChange` trace and emits one PostToolUse nudge. Later edits are silent but update the last review-relevant edit timestamp.

## Current Artifact Gate

A governed contract must be created or changed after the turn baseline and contain:

- Original request
- Scope
- Non-goals
- Acceptance criteria
- Required validation
- Risk class
- Reviewer checklist

A governed review must also be created or changed after baseline and contain Contract, Verdict, Validation evidence, Blocking issues, Residual risk, Required fixes before merge, and Wiki check.

The review passes only when it links the exact current contract, uses `Verdict: PASS`, and records an explicit `Command:` plus a successful `Result:` with no failure/non-zero exit marker. After every governed code/config edit, the hook snapshots review content hashes; the passing review content must differ from that snapshot. Artifact baselines and freshness compare content hashes rather than mtime, so `touch` and same-content rewrites cannot make pre-existing or stale evidence current.

The hook does not infer validation from shell history. The review owns the choice and exact record of risk-proportionate validation.

## Stop Behavior

Ordinary Stop is completely silent. Governed Stop evaluates only the current contract and review evidence:

- satisfied evidence returns silently and records a PASS trace;
- missing evidence blocks with one JSON object while the hook process exits successfully;
- `missing_governed_artifacts: observe` makes the same condition fail open;
- worktree mismatch fails open and records both scopes;
- `stop_hook_active=true` is a continuation loop guard and skips enforcement.

There is no Stop wiki-ingest gate, size reminder, validation-command gate, or incremental-review gate.

## State And Isolation

State lives under `~/.codex/tmp/hooks/` and is keyed by session plus turn. Identity prefers explicit session/thread ids, configured environment ids, transcript UUIDs, and parent ids. A verified Codex parent process may extend fallback scope; broad terminal variables are deliberately not session identity.

Worktree identity combines resolved root and Git dir. Sibling worktrees therefore have different scope keys even when they share a common Git dir. Stop fails open if its stored scope differs from the event cwd.

Trace remains under `~/.codex/tmp/hooks/<session_id>/trace.jsonl` and contains only governed activation/Stop outcomes. `wiki/log.md` remains concise durable history.

## Known Boundary

Bash-only writes cannot activate the gate because current PostToolUse payloads do not provide a reliable structured effective path for arbitrary commands. If a governed change is made exclusively through Bash, human/agent workflow guidance remains the control; the hook does not guess from command text.

## Tests

`tests/test_codex_guard.py` covers ordinary large-change silence, no-path early return, structured and parallel path attribution, Bash fail-open behavior, prompt negation, governed paths, generated/guidance exclusions, bootstrap/session/worktree isolation, current artifact binding and freshness, explicit validation evidence, Stop JSON, worktree fail-open, and loop protection.

## See Also

- [Harness Policy](../config/harness-policy.md)
- [Stop Enforcement ADR](../decisions/adr-0001-stop-enforcement-policy.md)
- [Harness V3 Contract](../contracts/2026-07-13-risk-only-harness-v3.md)
- [Worktree Scope Isolation Contract](../contracts/2026-07-12-worktree-scope-isolation.md)
- [Runtime State](../ops/runtime-state.md)
