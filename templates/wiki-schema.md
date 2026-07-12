# SCHEMA — LLM Wiki

## Project

<!-- 一句话项目描述。init 时填写 -->

## Project Structure

<!-- 项目的关键目录和文件角色。帮助 LLM 理解项目布局。所有文件均可编辑 -->

| 路径 | 角色 |
|------|------|
<!-- init 时填写，例如：-->
<!-- | `src/` | 应用源码 | -->
<!-- | `docs/` | 设计文档和参考材料 | -->
<!-- | `tests/` | 测试用例 | -->

## Wiki Structure

<!-- init 时根据项目特点定义。目录和页面类型完全由项目决定 -->

```
wiki/
├── index.md          # 内容索引（必须）
├── log.md            # 操作日志（必须）
├── overview.md       # 项目全景（推荐）
└── ...               # 按项目需要扩展子目录
```

## Page Types

<!-- init 时根据项目需要定义。以下仅为占位示例，应全部替换 -->

- **overview** — 项目全景综述
- **source-summary** — 某个文件/模块的摘要
- **concept** — 关键概念解释

## Conventions

- 文件名：kebab-case（如 `subcultural-alignment.md`）
- 内链：相对路径 markdown link `[页面名](path/to/page.md)`
- Frontmatter：每个 wiki 页面带 YAML frontmatter
  ```yaml
  ---
  title: 页面标题
  type: overview | source-summary | concept | ...
  updated: YYYY-MM-DD HH:MM
  ---
  ```
  > `updated` 精确到分钟，用 `date +"%Y-%m-%d %H:%M"` 取当前时刻
- 交叉引用：页面底部 `## See Also` 区域列出相关页面链接

## Ingest Workflow

<!-- init 时可根据项目特化。以下为通用流程 -->

1. Main agent 判断 source 变化是否产生长期知识；trivial 或 runtime-only 变化不 ingest
2. 小而集中的 ingest 由 main agent 直接完成；大型或跨模块 ingest 才委托 focused subagent
3. 完整读取目标 source，更新相关 wiki 页面，并链式更新受影响页面
4. 更新 `wiki/index.md`，在 `wiki/log.md` 追加一条简洁记录
5. Main agent 验收覆盖范围，然后回到原任务

## Query Workflow

1. 每个 session/worktree 首次任务读取 schema 与 `wiki/index.md`，未变化时不重复读取
2. 每个问题先读取最多一个相关 wiki 页面
3. 信息不足时再展开或回溯源文件
4. 回答问题；只有长期有用的新分析才征求是否写入 wiki

## Lint Checklist

- [ ] 页面间矛盾
- [ ] 过时信息（被新 source 取代的旧声明）
- [ ] 孤立页面（没有入链）
- [ ] 缺失页面（被引用但不存在的概念）
- [ ] 缺失交叉引用
- [ ] 可通过搜索填补的信息空白

## Log Format

每条记录以二级标题开头，便于 grep 解析（时间精确到分钟，用 `date +"%Y-%m-%d %H:%M"` 取当前时刻）：

```markdown
## [YYYY-MM-DD HH:MM] operation | description

简要说明做了什么、影响了哪些页面。
```
