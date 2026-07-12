---
title: Contract: Worktree Scope Isolation
type: contract
updated: 2026-07-12 17:29
sources:
  - hooks/codex_guard.py
  - tests/test_codex_guard.py
---

# Contract: Worktree Scope Isolation

## Original request

修复 Codex Loop Harness 在 session cwd 与工具实际 worktree 不一致时，把其他 terminal 在原 worktree 的改动误归属给当前 session，并由 Stop hook 持续误阻塞的问题。

## Scope

- 为 hook state 记录稳定的 Git worktree identity 和可诊断的 branch/HEAD 信息。
- 严格遵循官方 hook wire format：common `cwd` 是 session cwd，Bash/apply_patch 的 `tool_input` 只保证 `command`。
- canonical `apply_patch`/Write/Edit 只累计结构化输入明确声明的路径；Bash 不从自由文本 command 猜测写入路径。
- 没有可靠路径证据的 PostToolUse 只刷新 baseline，不把共享 filesystem 的变化归给当前 session。
- 使用 Codex 官方 `stop_hook_active` 字段避免同一 continuation chain 重复回灌；首次 Stop 仍执行正常 objective enforcement。
- diff telemetry 只累计当前工具输入可证明触及的路径；没有路径证据的工具调用只刷新 baseline，不把共享 filesystem 的变化归给当前 session。
- Stop 消息显示 worktree path 和 branch/HEAD，便于识别 scope 错误。
- 增加跨 worktree、外部改动误归属、Stop 去重与正常 hard gate 的回归测试。

## Non-goals

- 不尝试从任意 shell command 文本精确推断所有文件写入。
- 不允许多个 Codex session 安全地并发写同一个 worktree；独立 worktree 仍是推荐隔离方式。
- 不删除或读取现有 session transcript、sqlite、credentials、cache 或旧 runtime hook state。
- 不改变 contract、review、validation 的正常 hard-gate 条件。
- 不覆盖当前 worktree 中与本任务无关的未提交修改。

## Acceptance criteria

- [ ] session 启动时记录 worktree root、Git common-dir/git-dir、branch 或 detached HEAD。
- [ ] 官方 Bash payload 只有 `command` 时，无可证明路径的调用不会把原 worktree 的并发修改归入 telemetry。
- [ ] Bash command 即使含有 patch 文本，也不会把 session root 中同名的外部修改误归属给当前 turn。
- [ ] hook event 的 session worktree identity 与 turn state 不一致时，Stop fail-open 并写入明确 trace。
- [ ] `stop_hook_active=true` 时不再重复 block；首次 `stop_hook_active=false` 的 Stop 仍会阻止未解决的 objective blocker。
- [ ] Stop block 信息包含所检查的绝对 worktree path 和 branch/HEAD。
- [ ] 原有 session isolation、threshold、risky path、Stop JSON 和 PASS review 行为不回归。

## Required validation

- [ ] `python3 -m py_compile hooks/codex_guard.py tests/test_codex_guard.py`
- [ ] 新增定向 worktree/scope/Stop tests 通过。
- [ ] `python3 -m unittest discover -s tests` 通过。
- [ ] 手工创建两个临时 Git worktree，验证 sibling worktree 工具调用不会污染 session root telemetry。
- [ ] reviewer 写入结构化 review artifact，`Verdict` 为 `PASS`。

## Risk class

risky

原因：修改 `hooks/codex_guard.py` 的 worktree 归属和 Stop enforcement 路径；错误实现可能造成 false positive、false negative 或 Stop loop。

## Reviewer checklist

- [ ] identity 是否能区分同一仓库的 sibling worktree，而不只比较 branch 名？
- [ ] 无路径证据的调用是否 fail-open 且仍刷新 baseline，避免外部修改延迟到下一次 tool call 被归属？
- [ ] 测试是否使用官方真实 wire format，而非 synthetic tool-level `workdir`？
- [ ] 外部并发修改是否仍可能被无条件全仓库 snapshot 误归属？若无法完全消除，边界是否明确并安全？
- [ ] Stop 循环保护是否正确使用官方 `stop_hook_active`，且首次 Stop enforcement 保持不变？
- [ ] diagnostics 是否包含 root 和 branch/HEAD 且不泄露敏感内容？
- [ ] 原有 tests、validation、wiki ingest 和 review gate 是否保持兼容？

## See Also

- [Codex Loop Harness](../hooks/codex-guard.md)
- [Session Isolation Hardening](2026-07-01-session-isolation-hardening.md)
- [Stop Enforcement Policy](../decisions/adr-0001-stop-enforcement-policy.md)
