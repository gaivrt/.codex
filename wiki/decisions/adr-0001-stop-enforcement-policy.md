---
title: ADR-0001 Stop Enforcement Policy
type: decision
updated: 2026-07-01 20:46
sources:
  - hooks/codex_guard.py
  - harness_policy.yaml
  - SCHEMA.md
---

# ADR-0001 Stop Enforcement Policy

## Status

Accepted

## Context

The original harness had two gates: wiki ingest reminders and GAN-style reviewer reminders. The implementation contained hard-block capable functions, but `hook_stop()` called them in reminder-only mode. This created a mismatch between the intended discipline for large real code edits and the repository hook behavior.

The harness now needs to support long-running Codex work where objective missing requirements can stop the agent before it exits, while subjective quality judgments remain the reviewer's responsibility.

## Decision

Stop enforcement uses three modes:

- `observe`: record trace only.
- `remind`: emit additional context but return success.
- `block`: return `2` on the first missing objective requirement so the agent must continue work.

Small or low-risk changes remain observe/remind by default. Large or risky changes hard-block when objective artifacts are missing:

- no valid contract under `wiki/contracts/`;
- no structured review under `wiki/reviews/`;
- review verdict is `FAIL` or `NEEDS_HUMAN`;
- no validation evidence was observed.

Wiki ingest remains reminder-only by default, but the policy file can raise it to block for stricter projects.

## Rationale

Hard blocks should only enforce facts the harness can verify: artifacts, verdict values, validation commands, diff telemetry, and wiki log/index/page updates. The hook should not hard-block subjective quality judgments such as elegance, naming taste, or whether an alternative architecture might be nicer.

Large/risky edits are different from small edits because the expected damage from missing process is higher. Risk can come from size, path, or self-modification of the harness itself.

## Consequences

- Agents must create a contract before substantial implementation work.
- Reviewers must write structured review artifacts for large/risky changes.
- `wiki/log.md` remains durable project history; noisy per-session trace goes to `~/.codex/tmp/hooks/<session_id>/trace.jsonl`.
- `harness_policy.yaml` controls thresholds, risky paths, generated paths, validation markers, and enforcement mode.

## See Also

- [Codex Guard](../hooks/codex-guard.md)
- [Codex Loop Harness Contract](../contracts/2026-07-01-codex-loop-harness.md)
- [Wiki Log](../log.md)
