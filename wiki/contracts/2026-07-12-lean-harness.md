---
title: Contract: Lean Harness
type: contract
updated: 2026-07-12 22:49
sources:
  - AGENTS.md
  - README.md
  - SCHEMA.md
  - harness_policy.yaml
  - hooks.json
  - hooks/codex_guard.py
  - tests/test_codex_guard.py
  - templates/wiki-schema.md
---

# Contract: Lean Harness

## Original request

降低 Codex Loop Harness 的 token 与流程成本：日常工作默认沉默，只在真实的大型或高风险改动时展开 contract、validation、review 和 wiki 闭环。

## Scope

- Wiki bootstrap 改为每个 session/worktree 一次，按 hash 变化重读。
- `<150` 行普通改动静默；`>=150` 行或架构/risky 修改需要精简 contract；`>=300` 行或 risky/安全/性能修改需要 reviewer。
- 普通新文件不单独触发 review；Stop 只为 objective risky blocker 输出。
- 小改动允许主 agent 直接 ingest；artifact 各自只保存其唯一职责。
- 精简 `AGENTS.md`、`README.md`、`SCHEMA.md`、wiki template、policy、hook、tests 和 wiki。

## Non-goals

- 不回退 session/worktree isolation、Stop JSON、loop guard 或 runtime/sensitive-file exclusions。
- 不读取 credentials、sessions、sqlite、cache、tmp 或 standalone binaries。
- 不修改远端 Git 状态或覆盖无关的未提交改动。

## Acceptance criteria

- 同一 session/worktree 不重复注入 Wiki bootstrap；schema/index hash 或 worktree 改变时才重新提示。
- planning/discussion 不触发长 GAN 提示；gate 由真实 file-tool telemetry 驱动。
- 普通 `<150` 行改动和普通新文件不会触发 reviewer 或 Stop 消息。
- `>=150` 行普通改动缺 contract 时提醒而不阻断；`>=300` 行普通改动需要 reviewer 提醒。
- risky/harness self、安全、性能类修改缺 contract、validation 或 PASS review 时仍 block。
- Wiki 缺失默认静默；小 ingest 不要求 subagent。
- Contract、review、wiki 页面不重复 scope、validation 与风险叙述。

## Required validation

- `python3 -m py_compile hooks/codex_guard.py tests/test_codex_guard.py`
- `python3 -m unittest discover -s tests -v`
- 定向测试覆盖 bootstrap 去重、150/300 分层、普通新文件、silent Stop、risky hard block。
- `git diff --check`（只评估本任务触及文件）。

## Risk class

risky：修改 harness 自身的 prompt、telemetry 和 Stop enforcement。

## Reviewer checklist

- 默认路径是否真正静默且不丢失 risky hard gate？
- 阈值和 contract/reviewer 职责是否与用户确认的一致？
- session/worktree/hash bootstrap 是否避免重复提示？
- 既有 worktree isolation、Stop JSON 与 loop guard 是否无回归？
- tests、wiki ingest 和最终行为是否一致？

## See Also

- [Codex Loop Harness](../hooks/codex-guard.md)
- [Harness Policy](../config/harness-policy.md)
