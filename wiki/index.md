---
title: Wiki Index
type: project-overview
updated: 2026-07-12 23:06
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
- [Harness Policy](config/harness-policy.md) — Lean Harness 的 150/300 阈值、silent/advisory/strict enforcement、risky/generated paths 和 validation markers。

## Hooks

- [Codex Loop Harness](hooks/codex-guard.md) — 一次性 wiki bootstrap、tool-evidenced telemetry、lean process tiers、worktree isolation 和 strict-risk Stop enforcement。

## Contracts

- [Codex Loop Harness Contract](contracts/2026-07-01-codex-loop-harness.md) — 本次 harness 升级的 scope、non-goals、acceptance criteria、validation 和 reviewer checklist。
- [Session Isolation Hardening Contract](contracts/2026-07-01-session-isolation-hardening.md) — 防止缺失可靠 session identity 时跨 Codex session 共享 hook state 的修复 contract。
- [Stop JSON Output Contract](contracts/2026-07-01-stop-json-output.md) — 修复 Stop hook invalid JSON output 的 contract，规定 reminder/block 的 JSON 输出形状。
- [Worktree Scope Isolation Contract](contracts/2026-07-12-worktree-scope-isolation.md) — 修复跨 worktree 文件误归属与 Stop continuation 循环的 scope、wire-format 边界和验收标准。
- [Lean Harness Contract](contracts/2026-07-12-lean-harness.md) — 将日常路径改为静默、contract/reviewer 改为 150/300 分层并收紧 strict Stop blocker 的验收边界。

## Reviews

- [Codex Loop Harness Review](reviews/2026-07-01-codex-loop-harness-review.md) — 初版 strict harness 的历史 PASS review；当前 enforcement 以 Lean Harness 页面与 ADR 为准。
- [Session Isolation Hardening Review](reviews/2026-07-01-session-isolation-hardening-review.md) — reviewer 对 session isolation 修复的结构化 PASS 审查，记录初次 REVISE 与最终验证。
- [Stop JSON Output Review](reviews/2026-07-01-stop-json-output-review.md) — reviewer 对 Stop JSON 输出修复的结构化 PASS 审查，记录 invalid JSON failure mode 的验证。
- [Worktree Scope Isolation Review](reviews/2026-07-12-worktree-scope-isolation-review.md) — reviewer 对 worktree identity、tool-evidenced attribution、Bash fail-open 和 Stop loop guard 的结构化 PASS 审查。
- [Lean Harness Review](reviews/2026-07-12-lean-harness-review.md) — 150/300 分层、一次性 bootstrap、ordinary silent Stop 与 strict-risk blocker 的精简 PASS 审查。

## Skills

- [System Skills](skills/system-skills.md) — `skills/.system/` 中 imagegen、openai-docs、plugin-creator、skill-creator、skill-installer 的合并索引。

## Templates

- [Wiki Schema Template](templates/wiki-schema-template.md) — `templates/wiki-schema.md` 的用途、结构和 `$init-wiki` 复用边界。

## Ops

- [Runtime State](ops/runtime-state.md) — credentials、sqlite、sessions、cache、standalone binaries 等默认排除类别和维护规则。

## Decisions

- [ADR-0001 Stop Enforcement Policy](decisions/adr-0001-stop-enforcement-policy.md) — 默认静默、size-only advisory、仅 strict-risk objective omissions hard-block 的 Stop 策略。

## See Also

- [Project Overview](overview.md)
- [Wiki Log](log.md)
