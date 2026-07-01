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

1. Main agent 判断需要 ingest 的 source 文件和原因
2. Main agent 将 ingest 委托给 wiki-ingest subagent（除非用户要求单 agent 执行或 subagent 不可用）
3. wiki-ingest subagent 完整读取 source 文件
4. wiki-ingest subagent 写新 wiki 页面或更新已有页面，并链式更新受影响页面
5. wiki-ingest subagent 更新 `wiki/index.md`
6. wiki-ingest subagent 在 `wiki/log.md` 追加记录
7. Main agent 验收覆盖范围，必要时集成 subagent 变更，然后回到原任务

## Query Workflow

1. 读 `wiki/index.md` 定位相关页面
2. 读取相关 wiki 页面
3. 如果 wiki 信息不足，回溯到源文件或代码
4. 回答问题
5. 有价值的新分析可（征求用户同意后）存入 wiki

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
