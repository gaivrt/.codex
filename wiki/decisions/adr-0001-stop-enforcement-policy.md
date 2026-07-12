---
title: ADR-0001 Stop Enforcement Policy
type: decision
updated: 2026-07-12 22:59
sources:
  - hooks/codex_guard.py
  - harness_policy.yaml
  - SCHEMA.md
---

# ADR-0001 Stop Enforcement Policy

## Status

Accepted

## Context

The first strict harness made large and risky changes share a full contract/review/validation closure. Repeated wiki bootstrap, prompt-driven guidance, low size/new-file thresholds, and user-facing Stop reminders imposed disproportionate token and workflow cost on ordinary personal-repository work.

## Decision

Policy still exposes three modes:

- `observe`: record trace only.
- `remind`: emit concise tool-time guidance.
- `block`: public Stop emits one `{"decision":"block","reason":"..."}` object and returns success so Codex continues.

The default path is silent. Ordinary changes below 150 net-new attributed lines need no artifact. At 150 lines contract becomes advisory; at 300 lines review becomes advisory. New-file status alone does not activate review, and ordinary size-only changes do not emit Stop output.

Only strict risky/security/performance changes hard-block on objective omissions:

- no valid contract under `wiki/contracts/`;
- no structured review under `wiki/reviews/`;
- current review verdict is absent, `FAIL`, or `NEEDS_HUMAN`;
- no validation evidence was observed.

Wiki ingest is `observe` by default. Planning/discussion cannot trigger a gate without attributed code telemetry. Bootstrap guidance is stored per session/worktree with schema/index content hashes and repeats only when scope or content changes.

## Rationale

Hard blocks should only enforce facts the harness can verify: artifacts, verdict values, validation commands, diff telemetry, and wiki log/index/page updates. The hook should not hard-block subjective quality judgments such as elegance, naming taste, or whether an alternative architecture might be nicer.

Hard blocks are reserved for changes where the expected damage is tied to enforcement, security, permissions, deployment, migration, CI, or explicit security/performance intent. Size remains useful for process guidance but is not sufficient reason to prevent completion.

## Consequences

- Agents receive at most one short nudge when an ordinary change crosses the 150/300 thresholds.
- Risky changes still require a short contract, validation, and a concise current PASS review.
- `AGENTS.md`, `SCHEMA.md`, ordinary docs, and general config are not hard-risk by path alone.
- Small focused wiki updates may be performed by the main agent; missing wiki ingest is silent by default.
- `wiki/log.md` remains durable project history; noisy per-session trace goes to `~/.codex/tmp/hooks/<session_id>/trace.jsonl`.
- `harness_policy.yaml` controls thresholds, risky paths, generated paths, validation markers, and enforcement mode.

## See Also

- [Codex Guard](../hooks/codex-guard.md)
- [Codex Loop Harness Contract](../contracts/2026-07-01-codex-loop-harness.md)
- [Wiki Log](../log.md)
