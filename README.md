# Codex Home

这是 GAIVR 的个人 Codex home 仓库，用来管理可长期维护的 Codex 配置、hook、rules、skills 和 templates。

这个仓库的目标是同步“人写下来的规则和工具”，不是同步 Codex 的本地运行状态。

## 内容地图

| 路径 | 用途 |
|---|---|
| `AGENTS.md` | 全局 Codex 行为约定，包括沟通风格、工程规则、wiki workflow、GAN review workflow |
| `config.toml` | Codex 主配置：模型、provider、trusted projects、MCP servers、hook trust state |
| `hooks.json` | Codex lifecycle hooks 的入口配置 |
| `hooks/codex_guard.py` | wiki/GAN discipline hook 的主实现 |
| `rules/default.rules` | 已批准的命令前缀规则 |
| `skills/.system/` | 安装的 system skills、引用文档、脚本和资产 |
| `templates/` | 可复用模板，目前包含 wiki schema 模板 |
| `.gitignore` | 明确排除 secrets、runtime state、cache、standalone binaries |

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
https://github.com/gaivrt/.codex.git
```

建议首次提交只包含可维护配置：

```sh
git add .gitignore README.md AGENTS.md config.toml hooks.json hooks/codex_guard.py rules/default.rules skills/.system templates/wiki-schema.md
git commit -m "init codex home"
git push -u origin main
```

push 前再跑一次 `git status --ignored --short`，确认 secrets 和 runtime state 没有进入 staged set。

## Wiki 约定

如果当前目录后续启用 LLM Wiki，项目根会出现 `SCHEMA.md` 和 `wiki/`：

- `SCHEMA.md` 定义 wiki 结构和 ingest/query workflow。
- `wiki/index.md` 是知识入口。
- `wiki/log.md` 是 append-only 变更日志。
- `wiki/` 应被 Git 追踪，不要加入 `.gitignore`。

初始化或重建 wiki 时使用 `$init-wiki` skill，不要手动套模板。
