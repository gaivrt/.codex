---
title: Wiki Index
type: project-overview
updated: 2026-07-01 23:18
sources:
  - SCHEMA.md
  - README.md
---

# Wiki Index

<!-- LLM 维护的内容索引。每个页面一行：链接 + 单行摘要。 -->

## Overview

- [Overview](overview.md) — GAIVR 个人 Codex home 的项目全景、目录角色和 ingest 边界。

## Config

- [Codex Configuration](config/codex-config.md) — Codex 模型/provider/MCP/trusted projects/hooks trust/rules 的配置摘要。
- [Git Boundaries](config/git-boundaries.md) — Git 与 wiki 的长期维护边界、`.gitignore` 排除类别和协作规则。
- [Harness Policy](config/harness-policy.md) — Codex Loop Harness 的阈值、enforcement modes、risky/generated paths 和 validation markers。

## Hooks

- [Codex Loop Harness](hooks/codex-guard.md) — contract-first、diff telemetry、risk-based review、validation、trace/restart 和 Stop enforcement。

## Contracts

- [Codex Loop Harness Contract](contracts/2026-07-01-codex-loop-harness.md) — 本次 harness 升级的 scope、non-goals、acceptance criteria、validation 和 reviewer checklist。
- [Session Isolation Hardening Contract](contracts/2026-07-01-session-isolation-hardening.md) — 防止缺失可靠 session identity 时跨 Codex session 共享 hook state 的修复 contract。

## Reviews

- [Session Isolation Hardening Review](reviews/2026-07-01-session-isolation-hardening-review.md) — reviewer 对 session isolation 修复的结构化 PASS 审查，记录初次 REVISE 与最终验证。

## Skills

- [System Skills](skills/system-skills.md) — `skills/.system/` 中 imagegen、openai-docs、plugin-creator、skill-creator、skill-installer 的合并索引。

## Templates

- [Wiki Schema Template](templates/wiki-schema-template.md) — `templates/wiki-schema.md` 的用途、结构和 `$init-wiki` 复用边界。

## Ops

- [Runtime State](ops/runtime-state.md) — credentials、sqlite、sessions、cache、standalone binaries 等默认排除类别和维护规则。

## Decisions

- [ADR-0001 Stop Enforcement Policy](decisions/adr-0001-stop-enforcement-policy.md) — Stop enforcement 的 observe/remind/block 三档策略和 hard-block 边界。

## See Also

- [Project Overview](overview.md)
- [Wiki Log](log.md)
