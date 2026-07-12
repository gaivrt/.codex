---
title: Codex Home Overview
type: project-overview
updated: 2026-07-12 22:59
sources:
  - SCHEMA.md
  - AGENTS.md
  - README.md
  - .gitignore
  - config.toml
  - harness_policy.yaml
  - hooks.json
  - hooks/codex_guard.py
  - rules/default.rules
  - tests/test_codex_guard.py
  - templates/wiki-schema.md
---

# Codex Home Overview

此项目是 GAIVR 的个人 Codex home，用于集中管理可长期维护的 Codex 配置、hook discipline、rules、skills、templates、MCP 与协作约定。

这个仓库关注“可复用、可审查、可同步的配置和知识”。它不以同步本机运行状态为目标，因此 credentials、session history、sqlite databases、cache、tmp、standalone binaries 等内容默认不进入 Git，也默认不进入 wiki。

## Durable Sources

| 路径 | 角色 |
|---|---|
| `AGENTS.md` | 精简的全局行为约定：session bootstrap、lean gate、artifact ownership、wiki ingest、安全与工程规则 |
| `README.md` | 仓库说明、提交边界、常用 Git 检查命令 |
| `.gitignore` | 排除 secrets、runtime state、cache、standalone binaries、备份文件 |
| `config.toml` | Codex 主配置：模型、provider、trusted projects、MCP servers、hook trust state |
| `hooks.json` | Codex lifecycle hooks 入口配置 |
| `harness_policy.yaml` | Codex Loop Harness policy：阈值、enforcement modes、risky/generated paths、validation markers |
| `hooks/codex_guard.py` | Lean Harness 主实现：一次性 wiki bootstrap、tool-evidenced telemetry、150/300 process tiers、strict-risk Stop gate、trace/restart |
| `rules/default.rules` | 已批准的命令前缀规则 |
| `skills/.system/` | 安装的 system skills、引用文档、脚本和资产 |
| `tests/test_codex_guard.py` | harness 行为测试 |
| `templates/wiki-schema.md` | LLM Wiki schema 模板 |

## Runtime And Sensitive State

以下路径可以解释其角色，但默认不读取细节、不摘录内容、不提交：

| 路径 | 说明 |
|---|---|
| `auth.json`, `.credentials.json`, `installation_id` | 本机凭据和身份 |
| `*.sqlite`, `*.sqlite-wal`, `*.sqlite-shm`, `models_cache.json`, `version.json` | Codex 本机数据库、缓存和版本状态 |
| `history.jsonl`, `sessions/`, `shell_snapshots/` | 会话历史和 shell 快照 |
| `cache/`, `tmp/`, `.tmp/`, `log/`, `app-server-control/`, `memories/` | 缓存、临时文件、运行控制状态和本机记忆 |
| `packages/standalone/` | Codex standalone release binaries；当前 symlink 指向 `0.142.5-x86_64-unknown-linux-musl` |
| `backups/`, `*.bak-*` | 迁移或编辑备份 |

## Knowledge Pages

- [Codex Configuration](config/codex-config.md) records model/provider defaults, MCP servers, trusted projects, hook trust hashes, and approved command prefixes.
- [Git Boundaries](config/git-boundaries.md) records what belongs in Git/wiki and what must remain local runtime state.
- [Harness Policy](config/harness-policy.md) records thresholds, enforcement modes, risky/generated paths, and validation markers.
- [Codex Loop Harness](hooks/codex-guard.md) records lifecycle hook events, contract/review gates, diff telemetry, validation, trace/restart, and Stop enforcement.
- [Codex Loop Harness Contract](contracts/2026-07-01-codex-loop-harness.md) records the implementation contract for the current harness upgrade.
- [ADR-0001 Stop Enforcement Policy](decisions/adr-0001-stop-enforcement-policy.md) records the enforcement decision for observe/remind/block behavior.
- [System Skills](skills/system-skills.md) indexes the installed system skills and their key scripts/references.
- [Wiki Schema Template](templates/wiki-schema-template.md) explains the reusable wiki schema skeleton.
- [Runtime State](ops/runtime-state.md) records excluded runtime/sensitive categories and the standalone binary version.

## Wiki Scope

Wiki 负责维护这个目录的长期知识：

- 配置意图：为什么 `config.toml`、`hooks.json`、`rules/default.rules` 这样设置。
- Hook 行为：`codex_guard.py` 如何追踪 loop discipline、contract/review artifacts、validation evidence、trace 和 Stop enforcement。
- Skill 索引：每个 skill 的目的、触发条件、入口和重要脚本。
- 模板说明：`templates/` 中的可复用模板如何使用。
- 运行维护：哪些文件是运行态，哪些文件应该被 Git 和 wiki 排除。
- 决策记录：影响未来维护的 durable decisions。

## Lean Maintenance Model

- 每个 session/worktree 首次非 trivial 工作读取 `SCHEMA.md` 与 `wiki/index.md`；内容和 scope 未变化时不重复读取。
- 普通 `<150` 行代码改动无 contract/reviewer；`>=150` 行需要短 contract，`>=300` 行需要 review，但 size-only Stop 保持静默。
- Hook enforcement/policy、auth、sandbox、permission、migration、deploy 和 CI 等 strict-risk 改动缺 contract、validation 或 current PASS review 时才 hard-block。
- 小而集中的 durable knowledge 由主 agent 直接 ingest；大型或跨模块 ingest 才委托 subagent。
- Contract 定义目标，review 保存结论和证据，wiki 只维护当前行为，log 只追加一条简洁历史记录。

## Maintenance Rules

- 新增可维护配置时，更新对应 wiki 页面和 `wiki/index.md`。
- 修改 hook 或 config 的行为时，更新相关页面并在 `wiki/log.md` 追加记录。
- 对默认排除文件只记录类别和用途，不复制 secrets、tokens、session 内容或 database 内容。
- `wiki/` 应由 Git 追踪，不要加入 `.gitignore`。

## See Also

- [Wiki Index](index.md)
- [Wiki Log](log.md)
- [Codex Configuration](config/codex-config.md)
- [Harness Policy](config/harness-policy.md)
- [Codex Loop Harness](hooks/codex-guard.md)
- [System Skills](skills/system-skills.md)
