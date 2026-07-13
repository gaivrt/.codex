---
title: Wiki Index
type: project-overview
updated: 2026-07-13 13:46
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
- [Harness Policy](config/harness-policy.md) — Harness V3 的 governed/generated paths、prompt risk terms 和单一 objective Stop gate。

## Hooks

- [Codex Loop Harness](hooks/codex-guard.md) — hash bootstrap、structured path evidence、risk-only current artifact gate、worktree isolation 和 sparse trace。

## Contracts

- [Codex Loop Harness Contract](contracts/2026-07-01-codex-loop-harness.md) — 本次 harness 升级的 scope、non-goals、acceptance criteria、validation 和 reviewer checklist。
- [Session Isolation Hardening Contract](contracts/2026-07-01-session-isolation-hardening.md) — 防止缺失可靠 session identity 时跨 Codex session 共享 hook state 的修复 contract。
- [Stop JSON Output Contract](contracts/2026-07-01-stop-json-output.md) — 修复 Stop hook invalid JSON output 的 contract，规定 reminder/block 的 JSON 输出形状。
- [Worktree Scope Isolation Contract](contracts/2026-07-12-worktree-scope-isolation.md) — 修复跨 worktree 文件误归属与 Stop continuation 循环的 scope、wire-format 边界和验收标准。
- [Lean Harness Contract](contracts/2026-07-12-lean-harness.md) — 将日常路径改为静默、contract/reviewer 改为 150/300 分层并收紧 strict Stop blocker 的验收边界。
- [Harness V3 Contract](contracts/2026-07-13-risk-only-harness-v3.md) — 删除 line-count ceremony、repo snapshots 与 command surveillance，改为 risk-only governed contract/review 的验收边界。

## Reviews

- [Codex Loop Harness Review](reviews/2026-07-01-codex-loop-harness-review.md) — 初版 strict harness 的历史 PASS review；当前 enforcement 以 Lean Harness 页面与 ADR 为准。
- [Session Isolation Hardening Review](reviews/2026-07-01-session-isolation-hardening-review.md) — reviewer 对 session isolation 修复的结构化 PASS 审查，记录初次 REVISE 与最终验证。
- [Stop JSON Output Review](reviews/2026-07-01-stop-json-output-review.md) — reviewer 对 Stop JSON 输出修复的结构化 PASS 审查，记录 invalid JSON failure mode 的验证。
- [Worktree Scope Isolation Review](reviews/2026-07-12-worktree-scope-isolation-review.md) — reviewer 对 worktree identity、tool-evidenced attribution、Bash fail-open 和 Stop loop guard 的结构化 PASS 审查。
- [Lean Harness Review](reviews/2026-07-12-lean-harness-review.md) — 150/300 分层、一次性 bootstrap、ordinary silent Stop 与 strict-risk blocker 的精简 PASS 审查。
- [Harness V3 Review](reviews/2026-07-13-risk-only-harness-v3-review.md) — reviewer 验证 risk classifier、content-hash artifact freshness、validation result、ordinary silent path 与 fail-open boundaries 后给出的 PASS 审查。

## Skills

- [System Skills](skills/system-skills.md) — `skills/.system/` 中 imagegen、openai-docs、plugin-creator、skill-creator、skill-installer 的合并索引。

## Templates

- [Wiki Schema Template](templates/wiki-schema-template.md) — `templates/wiki-schema.md` 的用途、结构和 `$init-wiki` 复用边界。

## Ops

- [Runtime State](ops/runtime-state.md) — credentials、sqlite、sessions、cache、standalone binaries 等默认排除类别和维护规则。

## Decisions

- [ADR-0001 Stop Enforcement Policy](decisions/adr-0001-stop-enforcement-policy.md) — 放弃 size-only process，采用 risk-only governed evidence、current artifact binding/freshness 和 external-op 分离的 Stop 策略。

## See Also

- [Project Overview](overview.md)
- [Wiki Log](log.md)
