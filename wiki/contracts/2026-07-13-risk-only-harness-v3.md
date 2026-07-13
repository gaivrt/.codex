---
title: Contract: Risk-only Harness V3
type: contract
updated: 2026-07-13 13:18
sources:
  - AGENTS.md
  - harness_policy.yaml
  - hooks/codex_guard.py
  - tests/test_codex_guard.py
---

# Contract: Risk-only Harness V3

## Original request

Implement the approved Harness V3 plan: remove size-driven ceremony and retain strict enforcement only for objectively governed code changes.

## Scope

- Replace 150/300 line gates with risk-only governance.
- Remove full-repository PostToolUse snapshots, wiki gates, command-string validation, and automatic compile/typecheck.
- Bind a fresh PASS review to a valid contract and post-change validation evidence.
- Preserve bootstrap, session/worktree isolation, structured-path attribution, Stop JSON, and loop protection.

## Non-goals

- Do not change sandbox, approval, credential, or remote-operation behavior.
- Do not rewrite historical contracts/reviews or unrelated dirty-worktree changes.

## Acceptance criteria

- Ordinary changes of any size remain silent and need no artifacts.
- Governed changes block only on an objectively missing current contract/review.
- Read-only/no-path tools do no repository snapshot or noisy trace work.
- External operations remain authorization-based rather than review-artifact-based.

## Required validation

- Targeted unit tests during implementation.
- One final complete harness suite, Python compile, policy parse, and diff check.

## Risk class

Governed: harness self-modification.

## Reviewer checklist

- Correct risk classification and artifact freshness/binding.
- Fail-open session/worktree and Bash attribution boundaries.
- Ordinary silent path, Stop JSON validity, and removal of obsolete overhead.
