# Codex Home

这是 GAIVR 的个人 Codex home 仓库，用来管理可长期维护的 Codex 配置、Codex Loop Harness、rules、skills、templates 和 wiki memory。

这个仓库的目标是同步“人写下来的规则和工具”，不是同步 Codex 的本地运行状态。

## 内容地图

| 路径 | 用途 |
|---|---|
| `AGENTS.md` | Codex bootstrap 纪律和全局工程约定 |
| `SCHEMA.md` | LLM Wiki 结构、contract/review workflow、ingest/query/lint 规则 |
| `config.toml` | Codex 主配置：模型、provider、trusted projects、MCP servers、hook trust state |
| `harness_policy.yaml` | Codex Loop Harness policy：阈值、enforcement modes、risky/generated paths、validation markers |
| `hooks.json` | Codex lifecycle hooks 的入口配置 |
| `hooks/codex_guard.py` | Codex Loop Harness 主实现 |
| `rules/default.rules` | 已批准的命令前缀规则 |
| `skills/.system/` | 安装的 system skills、引用文档、脚本和资产 |
| `templates/` | 可复用模板，目前包含 wiki schema 模板 |
| `tests/test_codex_guard.py` | harness 行为测试 |
| `wiki/` | 长期项目知识、contracts、reviews、decisions、ingest log |
| `.gitignore` | 明确排除 secrets、runtime state、cache、standalone binaries |

## Harness 设计

这个仓库的核心不是单个 hook，而是一套 Codex Loop Harness：

```text
Bootstrap -> Contract -> Work -> Verify -> Review -> Ingest -> Trace -> Restart
```

各层职责：

| 层 | 位置 | 作用 |
|---|---|---|
| Bootstrap | `AGENTS.md`、`SessionStart` | 启动时要求先读 `SCHEMA.md` 和 `wiki/index.md` |
| Wiki Memory | `SCHEMA.md`、`wiki/index.md`、`wiki/**` | 把长期项目知识写到磁盘，不依赖上下文记忆 |
| Contract | `wiki/contracts/*.md` | 非平凡任务先定义 scope、non-goals、acceptance criteria、validation |
| Diff Telemetry | `hooks/codex_guard.py` | 用 Git/filesystem snapshot 观察真实文件变化，不信 agent 自述 |
| Review | `wiki/reviews/*-review.md` | 大改动或 risky 改动需要结构化 review artifact，`Verdict` 必须为 `PASS` |
| Validation | shell command markers + 自动 `py_compile` | 记录测试、lint、typecheck、smoke test 等客观证据 |
| Trace/Restart | `~/.codex/tmp/hooks/<session_id>/trace.jsonl`、`state.json` | 保存每轮 gate、diff、validation、Stop decision，方便复盘和恢复 |

Stop enforcement 有三档：

| 模式 | 行为 |
|---|---|
| `observe` | 只写 trace |
| `remind` | 给 Codex 追加上下文提醒，但不阻止退出 |
| `block` | 对客观缺失项返回 `2`，要求继续补齐 |

当前 policy 让小/中改动保持 reminder-oriented；large、risky、harness self-modification 在缺少 contract、PASS review 或 validation evidence 时 hard-block。主观质量问题交给 reviewer，不由 hook 直接判定。

运行 harness 测试：

```sh
python3 -m py_compile hooks/codex_guard.py tests/test_codex_guard.py
python3 -m unittest discover -s tests
```

## 不提交的内容

以下内容属于本机状态、敏感信息或生成产物，默认不进入 Git：

| 类型 | 示例 |
|---|---|
| 凭据和本机身份 | `auth.json`、`.credentials.json`、`installation_id` |
| 数据库和 WAL/SHM | `*.sqlite`、`*.sqlite-wal`、`*.sqlite-shm` |
| 会话和历史 | `history.jsonl`、`sessions/`、`shell_snapshots/` |
| 缓存和临时文件 | `cache/`、`tmp/`、`.tmp/`、`log/` |
| 安装包和二进制 | `packages/standalone/` |
| 迁移或编辑备份 | `backups/`、`*.bak-*` |

新增文件前先判断它是“可复用配置”还是“本机运行状态”。只有前者应该提交。

## 常用检查

查看当前 Git 状态：

```sh
git status --short --untracked-files=all
```

确认敏感文件是否被 ignore：

```sh
git status --ignored --short auth.json .credentials.json history.jsonl logs_2.sqlite
```

查看远端：

```sh
git remote -v
```

## 首次提交建议

仓库已连接到：

```text
git@github.com:gaivrt/.codex.git
```

建议提交只包含可维护配置：

```sh
git add .gitignore README.md AGENTS.md SCHEMA.md config.toml harness_policy.yaml hooks.json hooks/codex_guard.py rules/default.rules skills/.system templates/wiki-schema.md tests wiki
git commit -m "update codex home"
git push
```

push 前再跑一次 `git status --ignored --short`，确认 secrets 和 runtime state 没有进入 staged set。

## Wiki 约定

如果当前目录后续启用 LLM Wiki，项目根会出现 `SCHEMA.md` 和 `wiki/`：

- `SCHEMA.md` 定义 wiki 结构和 ingest/query workflow。
- `wiki/index.md` 是知识入口。
- `wiki/log.md` 是 append-only 变更日志。
- `wiki/` 应被 Git 追踪，不要加入 `.gitignore`。

初始化或重建 wiki 时使用 `$init-wiki` skill，不要手动套模板。
