# SCHEMA — LLM Wiki

## Project

GAIVR 的个人 Codex home，用于集中管理可长期维护的 Codex 配置、hook discipline、rules、skills、templates、MCP 与协作约定。

## Project Structure

| 路径 | 角色 |
|------|------|
| `AGENTS.md` | 全局 Codex 行为约定，包括沟通、工程规则、wiki workflow、GAN review workflow |
| `README.md` | 仓库说明、提交边界、常用 Git 检查命令 |
| `.gitignore` | 排除 secrets、runtime state、cache、standalone binaries、备份文件 |
| `config.toml` | Codex 主配置：模型、provider、trusted projects、MCP servers、hook trust state |
| `harness_policy.yaml` | Codex Loop Harness policy：阈值、enforcement modes、risky/generated paths、validation command markers |
| `hooks.json` | Codex lifecycle hooks 的入口配置 |
| `hooks/codex_guard.py` | wiki/GAN discipline hook 的主实现 |
| `rules/default.rules` | 已批准的命令前缀规则 |
| `skills/.system/` | 安装的 system skills、引用文档、脚本和资产 |
| `templates/wiki-schema.md` | LLM Wiki schema 模板 |
| `auth.json`, `.credentials.json`, `installation_id` | 本机凭据和身份文件；默认不 ingest、不提交 |
| `*.sqlite`, `*.sqlite-wal`, `*.sqlite-shm` | Codex 本机数据库和运行状态；默认不 ingest、不提交 |
| `history.jsonl`, `sessions/`, `shell_snapshots/` | 会话历史和 shell 快照；默认不 ingest、不提交 |
| `cache/`, `tmp/`, `.tmp/`, `log/`, `app-server-control/` | 缓存、临时文件和运行控制状态；默认不 ingest、不提交 |
| `packages/standalone/` | Codex standalone release binaries；只记录版本和角色，不 ingest binaries |
| `backups/`, `*.bak-*` | 迁移或编辑备份；按需人工确认后再 ingest |

## Wiki Structure

```
wiki/
├── index.md              # 内容索引（必须）
├── log.md                # 操作日志（必须，append-only）
├── overview.md           # 项目全景
├── config/               # Codex 配置、MCP、approved rules
├── hooks/                # lifecycle hooks、governed gate、状态文件行为
├── contracts/            # governed task contracts
├── reviews/              # governed reviewer artifacts
├── skills/               # 已安装 skills 的目的、入口和资源
├── templates/            # 可复用模板说明
├── ops/                  # 运行态文件说明、排除规则、维护流程
└── decisions/            # durable decisions / architecture notes
```

分类子目录在首次 ingest 相关页面时创建；不要用空目录表达知识结构。

## Page Types

- **project-overview** — 当前 Codex home 的全局地图、边界和维护原则
- **codex-config** — `config.toml`、`hooks.json`、`rules/default.rules` 等配置页
- **lifecycle-hook** — hook event、governed path、状态文件、fail-open/fail-hard 逻辑
- **contract** — governed task 的 scope、non-goals、acceptance criteria、validation、risk、review checklist
- **review** — reviewer artifact，包含 Verdict、contract coverage、diff risk、validation evidence、issues、wiki ingest check
- **skill-package** — skill 的目的、触发条件、入口文件、脚本和引用资源
- **template-note** — 模板用途、输入输出边界和复用方式
- **runtime-state** — sqlite/log/cache/session 等运行态文件的解释与排除规则
- **decision** — 长期有效的设计取舍、迁移决定或维护策略

## Conventions

- 文件名：kebab-case，如 `codex-guard-hook.md`
- 内链：相对路径 markdown link，如 `[Codex Guard](hooks/codex-guard.md)`
- Frontmatter：每个 wiki 页面带 YAML frontmatter
  ```yaml
  ---
  title: 页面标题
  type: project-overview | codex-config | lifecycle-hook | contract | review | skill-package | template-note | runtime-state | decision
  updated: YYYY-MM-DD HH:MM
  sources:
    - path/to/source
  ---
  ```
- `updated` 精确到分钟，用 `date +"%Y-%m-%d %H:%M"` 获取当前时刻。
- `sources` 列出支撑页面内容的源文件；仅来自目录结构观察时可写 `sources: []`。
- 交叉引用：页面底部 `## See Also` 区域列出相关页面链接。
- 不把 secrets、tokens、credentials、session transcripts、large binaries 或本机 runtime databases 的内容复制到 wiki。
- 可以解释敏感或运行态文件的角色，但不要记录其私密值、完整路径 token、会话内容或数据库内容。
- `wiki/` 必须由 Git 追踪；不要加入 `.gitignore`。
- `wiki/log.md` 记录 durable project history；per-session trace 写入 `~/.codex/tmp/hooks/<session_id>/trace.jsonl`，不要混入 wiki log。

## Contract And Review Workflow

1. Ordinary changes need no contract or reviewer regardless of size. Governed implementation creates a short `wiki/contracts/<YYYY-MM-DD>-<task-slug>.md` before implementation.
2. Contract pages contain only Original request, Scope, Non-goals, Acceptance criteria, Required validation, Risk class, and Reviewer checklist.
3. Governed implementation uses one reviewer after a coherent checkpoint and records a concise `wiki/reviews/<YYYY-MM-DD>-<task-slug>-review.md`; incremental fragments are not separately reviewed.
4. Review pages link the contract and contain only Contract, Verdict, concrete validation evidence, blocking issues, residual risk, required fixes, and wiki check.
5. Valid verdicts are `PASS`, `FAIL`, and `NEEDS_HUMAN`. Only governed changes hard-block on a missing current contract or current PASS review with explicit validation evidence.
6. Planning, discussion, line count, and ordinary new files never trigger gates without governed code/config telemetry. External-operation authorization and receipts remain separate from code review artifacts.

## Ingest Workflow

1. Main agent 判断 source 变化是否产生长期有效的新知识；trivial 或 runtime-only 变化不 ingest。
2. 小而集中的 ingest 由 main agent 直接完成；大型、跨模块或已委托的实现才优先使用 wiki-ingest subagent。
3. 读取 source 前先检查它是否属于默认排除范围：凭据、数据库、会话历史、cache、tmp、standalone binaries。
4. 对默认排除文件，只写角色说明或维护策略，不读取或摘录敏感/运行态内容。
5. 对可 ingest 文件，完整读取 source，创建或更新对应 wiki 页面，并链式更新 overview、index 或相关概念页。
6. 更新 `wiki/index.md`，每个页面一行链接和单行摘要。
7. 在 `wiki/log.md` 追加记录，使用 `## [YYYY-MM-DD HH:MM] ingest | description`。
8. Main agent 验收覆盖范围，必要时补充遗漏，然后回到原任务。

### Default Ingest Targets

- `AGENTS.md`
- `README.md`
- `.gitignore`
- `config.toml`
- `harness_policy.yaml`
- `hooks.json`
- `hooks/codex_guard.py`
- `rules/default.rules`
- `skills/.system/*/SKILL.md`
- `templates/wiki-schema.md`

### Default Exclusions

- `auth.json`, `.credentials.json`, `installation_id`
- `*.sqlite`, `*.sqlite-wal`, `*.sqlite-shm`
- `history.jsonl`, `sessions/`, `shell_snapshots/`
- `cache/`, `tmp/`, `.tmp/`, `log/`, `app-server-control/`, `memories/`
- `packages/standalone/**` binaries
- `backups/`, `*.bak-*` unless explicitly requested

## Query Workflow

1. 每个 session/worktree 首次 codebase 任务读取 `SCHEMA.md` 与 `wiki/index.md`；未变化时不重复读取。
2. 每个问题先读取最多一个相关 wiki 页面；不足时再展开或回溯源文件。
3. 回答时区分 wiki 已记录内容、源文件事实和当前推断。
4. 只有长期有用的新分析才询问是否写入 wiki。

## Lint Checklist

- [ ] 页面间矛盾
- [ ] 过时信息（被新 source 取代的旧声明）
- [ ] 孤立页面（没有入链）
- [ ] 缺失页面（被引用但不存在的概念）
- [ ] 缺失交叉引用
- [ ] index 缺失新页面或摘要失真
- [ ] log 缺失 ingest / init / decision 记录
- [ ] wiki 页面错误摘录 secrets、session 内容或 runtime database 内容
- [ ] 可通过 source search 填补的信息空白

## Log Format

每条记录以二级标题开头，便于 grep 解析；时间精确到分钟：

```markdown
## [YYYY-MM-DD HH:MM] operation | description

简要说明做了什么、影响了哪些页面。
```
