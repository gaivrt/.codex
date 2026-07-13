---
title: Harness Policy
type: codex-config
updated: 2026-07-13 13:29
sources:
  - harness_policy.yaml
  - hooks/codex_guard.py
---

# Harness Policy

`harness_policy.yaml` defines the small policy surface of Harness V3. It no longer contains line-count thresholds, new-file counters, validation command markers, incremental review reminders, or separate harness-self gates.

## Policy Version

`policy_version: 3` is included in the per-session bootstrap fingerprint. If `AGENTS.md`, the policy file, or its version changes during a session, the bootstrap hook asks the agent to start a new session so stale process instructions do not remain active.

## Enforcement

The default is `observe`. The only configured hard gate is:

- `missing_governed_artifacts: block`

A block is considered only after the turn has concrete governed file evidence. Ordinary work stays silent regardless of size.

## Governed Paths

Governed path patterns cover changes where missing review evidence has an objective risk:

- `hooks/**`, `hooks.json`, `harness_policy.yaml`, `.codex/**`
- auth, migration, deploy, CI workflow, sandbox, and permission-related paths

Authentication file names are also classified by exact path tokens (`auth`, `authentication`, `authorization`, `oauth`, `oidc`, `sso`). Token matching covers paths such as `src/auth.py` without treating unrelated names such as `author.py` as authentication code.

`AGENTS.md`, `SCHEMA.md`, documentation, and general configuration are not governed by path alone.

## Prompt Risk Terms

Security, auth/OAuth, permission, sandbox, migration, deploy, CI, performance-sensitive, and harness-enforcement terms can classify a turn as governed only when both conditions hold:

1. the prompt contains a positive implementation action rather than discussion or an explicitly negated action;
2. a structured file tool later declares a review-relevant code or configuration path.

Prompt text alone, Bash commands, and external operations therefore do not activate the code-review gate.

## Generated Paths

Generated/runtime paths such as Git metadata, caches, tmp, build/dist, virtualenvs, bytecode, node modules, data, probes, logs, and app-server control files are excluded from path evidence.

## See Also

- [Codex Loop Harness](../hooks/codex-guard.md)
- [Stop Enforcement ADR](../decisions/adr-0001-stop-enforcement-policy.md)
- [Git Boundaries](git-boundaries.md)
