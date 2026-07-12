---
title: Codex Loop Harness
type: lifecycle-hook
updated: 2026-07-12 22:59
sources:
  - hooks.json
  - hooks/codex_guard.py
  - harness_policy.yaml
  - tests/test_codex_guard.py
  - AGENTS.md
  - SCHEMA.md
  - https://learn.chatgpt.com/docs/hooks
---

# Codex Loop Harness

`hooks/codex_guard.py` is the lifecycle dispatcher for a lean Codex Loop Harness. Its ordinary path is silent; process expands only after structured file-tool telemetry proves a sufficiently large or risky code change.

The loop target is:

`Bootstrap -> Contract -> Work -> Verify -> Review -> Ingest -> Trace -> Restart`

## Lifecycle Events

- `UserPromptSubmit`: starts turn state, records worktree/code/artifact baselines, and stores architecture or sensitive-review prompt signals without treating discussion as evidence of work.
- `SessionStart`: checks the same session/worktree bootstrap state without repeating unchanged guidance.
- `PostToolUse`: attributes concrete structured file-tool effects, records diff/risk/reviewer/validation/wiki state, and emits at most one short nudge per contract or review threshold.
- `Stop`: stays silent for ordinary advisory and missing-wiki states. Only strict risky/security/performance changes can emit a hard-block JSON object for objective missing artifacts.

Unexpected hook errors remain fail-open and are appended to `/tmp/codex-hook-errors.log`.

## Policy-Driven Gates

`harness_policy.yaml` externalizes thresholds, enforcement modes, risky paths, generated paths, and validation command markers. The Python hook keeps safe defaults, but project policy is read from the project root when available.

The policy supports three enforcement modes:

- `observe`: write trace only.
- `remind`: emit a short tool-time nudge and return success.
- `block`: make the public Stop hook emit one `decision: block` JSON object while the command itself returns success.

Ordinary changes below 150 attributed net-new lines need neither contract nor reviewer. At 150 lines the harness requests a short contract; at 300 it requests review. These size-only tiers never hard-block at Stop. Risky path or security/performance changes require contract, validation, and a current PASS review; only their objective omissions hard-block.

## Wiki Bootstrap

The session meta state stores the worktree `scope_key` and SHA-1 hashes of `SCHEMA.md` and `wiki/index.md`. The first `UserPromptSubmit` or `SessionStart` in a session/worktree emits one short bootstrap message. Later events are silent unless the worktree changes or either file hash changes, in which case only the changed source is named for rereading.

Prompt classification initializes architecture/security/performance intent, but `triggered` is derived only after real attributed code paths exist. Planning and discussion therefore do not generate GAN guidance or Stop gates.

## Contract Gate

Architecture, risky, or at least 150-line attributed code changes create `wiki/contracts/<YYYY-MM-DD>-<task-slug>.md`. A valid short contract includes:

- Original request
- Scope
- Non-goals
- Acceptance criteria
- Required validation
- Risk class
- Reviewer checklist

An existing valid contract can be reused across turns and resumes. Size-only absence is advisory; strict risky absence blocks.

## Review Artifact Gate

Risky, security/performance-sensitive, or at least 300-line attributed changes require `wiki/reviews/<YYYY-MM-DD>-<task-slug>-review.md`. The lean shape contains Contract, Verdict, Validation evidence, Blocking issues, Residual risk, Required fixes before merge, and Wiki check; the previous structured shape remains accepted for compatibility.

Review evidence must be created or changed after the turn baseline, and `Verdict` must be `PASS`. Size-only absence remains advisory at Stop; strict changes block on a missing/non-PASS current artifact.

## Diff Telemetry And Risk

The harness builds repository snapshots from `git ls-files --cached --others --exclude-standard`, falling back to a filesystem walk, but a snapshot delta is charged to the turn only for paths evidenced by the current tool's structured input. Canonical `apply_patch` reads Add/Update/Delete paths from `tool_input.command`; Write/Edit-style tools use their explicit `file_path` or `path`. After every `PostToolUse`, the full baseline is refreshed even when there is no path evidence, so unrelated changes observed during a fail-open call do not leak into a later attributed call.

The official release wire format makes common `cwd` the session cwd. Bash and canonical `apply_patch` expose `tool_input.command`; Bash does not expose a separate effective tool `workdir`. The harness therefore never parses Bash command text as file-ownership evidence, even when it contains patch-looking text. A Bash call with no structured path evidence contributes an empty scoped delta while still refreshing the baseline. This intentionally prefers missed telemetry over charging another terminal's changes to the current session.

Process tiers are triggered by attributed code telemetry:

- contract threshold: 150 net-new lines or an architecture/risky/sensitive signal paired with a code change;
- review threshold: 300 net-new lines, a risky path, or a security/performance-sensitive signal paired with a code change;
- risky path: hook enforcement/policy plus auth, migration, deploy, CI, sandbox, and permission patterns;
- harness self-modification: `hooks/**`, `hooks.json`, or `harness_policy.yaml`.

Ordinary new files are counted toward their net-new lines but never trigger review merely because they are new. `AGENTS.md`, `SCHEMA.md`, docs, and general config are excluded from hard-risk classification by path alone.

Generated/cache paths are excluded by policy.

## Validation Evidence

The hook records validation evidence when shell commands include configured markers such as `py_compile`, `unittest`, `pytest`, `ruff`, `mypy`, `tsc`, `npm test`, `bun test`, `cargo test`, or `go test`.

Validation is a hard requirement only for strict risky/security/performance changes. Ordinary size-only changes can receive tool-time process nudges but Stop stays silent.

The hook also automatically compiles changed Python files and attempts TypeScript checking when TypeScript files changed.

## Trace And Restart

Per-session trace lives under:

`~/.codex/tmp/hooks/<session_id>/trace.jsonl`

Per-session restart state lives under:

`~/.codex/tmp/hooks/<session_id>/state.json`

Trace records include prompt classification, bootstrap decisions, changed files, line deltas, risk flags, validation messages, gate decisions, missing requirements, worktree identity, and Stop outcomes.

`wiki/log.md` remains durable project history and does not receive noisy per-session trace.

## Stop JSON Output

`Stop` is stricter than prompt/session/tool hooks: when it exits `0` and writes to stdout, stdout must be one valid JSON object. The harness therefore aggregates Wiki and GAN gate messages and emits a single Stop object.

If a policy explicitly enables a reminder, reminder-only Stop output uses:

`{"systemMessage": "..."}`

Strict hard-block Stop output uses:

`{"decision": "block", "reason": "..."}`

For `Stop`, `decision: "block"` tells Codex to continue with the reason as the next prompt. The hook process still exits `0`; direct internal gate functions may return `2` to their caller. The harness does not emit `hookSpecificOutput.additionalContext` for `Stop`, because that shape is invalid for this event.

## Session Isolation

Hook state keys are scoped by `session_id` plus the active turn id. The session identity resolver prefers explicit hook/session/thread ids, configured Codex session environment ids, transcript/session path UUIDs, and parent message ids.

When those are missing, the harness may append a Codex parent process scope (`pid<id>-<start_time>`) only if the process tree identifies an actual Codex process. It intentionally does not use broad terminal-only variables such as `TMUX`, `WT_SESSION`, `STY`, `SSH_TTY`, or `TERM_SESSION_ID` as a cross-session identity. If no reliable identity exists, fallback state uses the hook process id plus process start time, or a per-process nonce when `/proc` is unavailable, and fails open rather than sharing stale gate state between concurrent sessions in the same terminal or cwd.

## Worktree Scope Isolation

At turn initialization, GAN and Wiki state record the session worktree's resolved root, per-worktree Git dir, shared Git common dir, branch or detached-HEAD label, full HEAD, and a `scope_key` derived from the resolved root plus Git dir. Sibling worktrees share a common dir but have different Git dirs and scope keys; branch is diagnostic metadata, not the sole identity.

At Stop, each gate compares its stored worktree identity with the identity resolved from the current event `cwd`. A mismatch fails open and writes `worktree_scope_mismatch` plus stored/current identities to the per-session trace instead of enforcing stale state. Normal GAN reminder/block messages name the absolute checked root and branch/detached label.

Codex sets `stop_hook_active=true` for a Stop continuation caused by a prior Stop hook. `hook_stop` treats that as a loop guard: it traces the skip and returns before Wiki or GAN enforcement. The first Stop, where the field is false or absent, still evaluates all objective gates. Direct calls to the gate functions continue to block repeatedly while requirements are missing; the loop guard depends on the host-provided continuation field rather than weakening those gates.

### Known Boundaries

- Bash-only file writes are not counted as code telemetry, automatic changed-file compilation, or wiki-ingest evidence because the official payload cannot reliably bind them to an effective worktree/path. Bash validation commands can still be recognized by configured command markers.
- The harness does not dynamically move a turn's state to a sibling worktree inferred from shell text. Start the Codex session in the intended worktree; independent worktrees remain the supported concurrent workflow.
- If another process modifies the exact same path declared by the current structured file tool between snapshots, filesystem state cannot identify which writer contributed which lines. Concurrent writes to one worktree are therefore not made safe by this change.
- Loop prevention requires the host to send `stop_hook_active=true`. A fresh Stop with the field absent or false is intentionally enforced again if objective requirements remain missing.

## Tests

`tests/test_codex_guard.py` covers the 150/300 tiers, ordinary-new-file behavior, non-risky `AGENTS.md`/`SCHEMA.md`, risky hook/CI paths, bootstrap hash deduplication, discussion silence, generated/cache exclusions, session/worktree isolation, structured-path attribution, Bash fail-open boundaries, Stop JSON/loop guard, silent advisory Stop, strict blockers, and lean/legacy PASS review shapes.

## See Also

- [Harness Policy](../config/harness-policy.md)
- [Stop Enforcement ADR](../decisions/adr-0001-stop-enforcement-policy.md)
- [Codex Loop Harness Contract](../contracts/2026-07-01-codex-loop-harness.md)
- [Session Isolation Contract](../contracts/2026-07-01-session-isolation-hardening.md)
- [Stop JSON Output Contract](../contracts/2026-07-01-stop-json-output.md)
- [Worktree Scope Isolation Contract](../contracts/2026-07-12-worktree-scope-isolation.md)
- [Worktree Scope Isolation Review](../reviews/2026-07-12-worktree-scope-isolation-review.md)
- [Runtime State](../ops/runtime-state.md)
