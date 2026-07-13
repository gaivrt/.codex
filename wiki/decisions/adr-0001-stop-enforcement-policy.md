---
title: ADR-0001 Stop Enforcement Policy
type: decision
updated: 2026-07-13 13:29
sources:
  - hooks/codex_guard.py
  - harness_policy.yaml
  - AGENTS.md
  - SCHEMA.md
---

# ADR-0001 Stop Enforcement Policy

## Status

Accepted — superseded by the Harness V3 decision below.

## Context

Earlier harness versions used repository snapshots, attributed line counts, 150/300 thresholds, validation-command detection, incremental reminders, automatic compilation, and wiki/reviewer state tracking. Even when size-only Stop stayed advisory, agents still spent time creating artifacts and repeatedly running tests for ordinary work. Recent session records also showed that most PostToolUse events had no file delta, so full snapshots imposed cost without useful evidence.

Artifact presence was not enough either: an unrelated old contract or PASS review could appear valid, and shell command matching did not prove that the recorded validation covered the reviewed change.

## Decision

Harness V3 uses a risk-only governed workflow.

- Line count, ordinary new files, architecture discussion, and task size never trigger a contract or reviewer.
- A turn becomes governed only through an objective governed path, or through explicit sensitive implementation intent paired with a structured code/config write.
- Governed work needs one short current contract and one coherent current PASS review after implementation and targeted validation.
- Stop blocks only when either artifact is objectively missing or invalid. All unexpected hook failures remain fail-open.
- External-operation authorization, scope/budget, and execution receipts are handled separately; an operation alone does not create code-review artifacts.

The hook does not scan the repository after every tool call. It accepts file ownership only from structured ApplyPatch/Write/Edit-style inputs. Bash command text is never parsed as path evidence.

For a governed Stop to pass:

1. the contract content was created or changed after the turn baseline and has all required headings;
2. the review content was created or changed after that baseline;
3. the review links that exact current contract, has all required headings and `Verdict: PASS`;
4. the review records an explicit validation `Command:` and a successful `Result:` without a conflicting failure/non-zero exit;
5. the review content hash differs from the snapshot taken after the last governed code/config edit.

## Rationale

Process should expand only where omission has a clear downside: enforcement, auth/security, permissions/sandboxing, migrations/deployment, CI, or explicitly performance-sensitive implementation. Size is a poor proxy for these risks and caused ceremony on otherwise ordinary work.

Content freshness and binding are stronger evidence than command surveillance or mtime. They allow the reviewer to choose risk-proportionate validation while preventing stale, touched-only, or unrelated artifacts from satisfying the gate.

## Consequences

- Ordinary work is silent regardless of size and can use targeted tests without mandatory full-suite repetition.
- Governed work receives at most one short PostToolUse nudge and one final review cycle; only blocking fixes receive focused re-checks.
- Per-turn state stores declared paths, governed flags, artifact baselines, worktree identity, and last review-relevant edit time—not repository snapshots or line totals.
- Trace is sparse: governed activation and governed Stop outcomes only.
- Policy changes prompt a new session because already-loaded `AGENTS.md` instructions cannot be retroactively replaced.

## See Also

- [Codex Guard](../hooks/codex-guard.md)
- [Harness V3 Contract](../contracts/2026-07-13-risk-only-harness-v3.md)
- [Wiki Log](../log.md)
