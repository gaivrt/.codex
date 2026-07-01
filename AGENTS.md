# Global Codex Guidance

## Codex Loop Harness Bootstrap

Before non-trivial work in this repository:

1. Read `SCHEMA.md`.
2. Read `wiki/index.md` and relevant wiki pages.
3. For non-trivial code work, create or update a contract under `wiki/contracts/`.
4. For large or risky code changes, produce validation evidence and use a reviewer that writes `wiki/reviews/*-review.md` with `Verdict` set to `PASS`.
5. Do not read credentials, sqlite databases, sessions, cache, tmp, or standalone binaries unless the user explicitly asks for recovery/inspection.
6. After durable changes, update relevant wiki pages, `wiki/index.md`, and `wiki/log.md`.
7. Hook Stop blocks are authoritative when they report missing objective artifacts such as contract, review, validation, or required wiki ingest.

`AGENTS.md` is bootstrap discipline. Durable project knowledge belongs in `SCHEMA.md` and `wiki/`.

## Communication

- Use Chinese for normal interaction. Keep technical terms in English when that is clearer.
- The user is GAIVR and may be called "盖尔".
- The user uses vim.
- Environment: Win11 WSL. For Python projects prefer `uv` (`uv run`, `uv sync`, `uv add`). For frontend projects prefer `bun`.
- Do not start long-running servers or dev servers in the shell unless the user explicitly asks. Tell the user the command instead.
- If the user asks to record progress, update `/docs/DEV_LOG.md` with date, time, and concrete content.
- Code style: modular, concise, elegant. Avoid very long files.
- For long documents or large files, write in chunks under about 1,000 words per edit.

## First Steps

- Before implementing, inspect the project structure, package manager, env-var pattern, config system, and directory conventions.
- For bug fixes, prefer writing or identifying a failing test first, then loop until it passes.
- If the same approach fails 3 times, stop, restate the root-cause hypothesis, and switch to a genuinely different strategy.
- If you read the same file more than twice, stop. Summarize what is known, state what is unclear, then proceed or ask one focused question.

## Git

- Do not add `Co-Authored-By` lines.
- Keep commit messages short.
- Create a branch for current work when appropriate, especially to avoid collisions between multiple agent sessions.
- Ask before remote repository operations.
- Do not revert unrelated user changes.

## LLM Wiki Workflow

This is a cross-project knowledge-management rule. If a project root contains `SCHEMA.md`, the project is wiki-enabled.

### Session Start

When `SCHEMA.md` exists:

1. Read `SCHEMA.md`.
2. Read `wiki/index.md`.
3. Follow the schema-defined workflow for later work.

Do not rely on memory. Read the latest schema and index for each session.

### Architecture

| Layer | Location | Meaning |
|---|---|---|
| Raw Sources | Project files | Code, docs, data, and other editable sources. |
| Wiki | `wiki/` | LLM-maintained markdown knowledge base. |
| Schema | `SCHEMA.md` | Wiki structure and workflow definition. |

`AGENTS.md` controls coding behavior. `SCHEMA.md` controls knowledge management.

### Init

Use the `$init-wiki` skill. Do not initialize manually unless the skill is unavailable.

The template is `~/.codex/templates/wiki-schema.md`. It is only a skeleton. Customize page types and structure for the project.

### Ingest

When the user adds files, asks to process a file, or code changes materially:

1. Main agent identifies the source files and the ingest reason.
2. Main agent delegates the ingest to a focused wiki-ingest subagent whenever subagents are available.
3. The wiki-ingest subagent reads each source file fully, writes or updates wiki pages, chain-updates affected pages such as concepts, overview, or summaries, updates `wiki/index.md`, and appends `wiki/log.md` with `## [YYYY-MM-DD HH:MM] ingest | description` using `date +"%Y-%m-%d %H:%M"`.
4. Main agent reviews the subagent result for coverage, integrates the changes if needed, and continues the original task.
5. Main agent only performs wiki writing directly when subagents are unavailable or the user explicitly asks for a single-agent workflow.

Do not omit index or log updates after ingest.

### Query

For codebase-related questions or code changes in wiki-enabled projects:

1. Read `wiki/index.md` first and locate relevant pages.
2. Read those wiki pages.
3. Fall back to source files only when wiki information is insufficient.
4. Answer from both wiki and source context.
5. If the answer produces durable new analysis, ask whether to store it in the wiki.

### Lint

When the user asks for lint, or before git-managed checkpoints in wiki-enabled projects, check:

- Contradictions between pages.
- Outdated pages.
- Orphan pages.
- Missing referenced concepts or pages.
- Missing cross-references.
- Obvious information gaps that source search can fill.

Report issues and concrete fixes before editing.

### Wiki Constraints

- `wiki/` must be git-tracked. Do not add it to `.gitignore`.
- `SCHEMA.md` belongs in the project root.
- `wiki/index.md` is the information entrypoint and must stay current.
- `wiki/log.md` is append-only and uses second-level headings for grep-friendly parsing.

## GAN Review Workflow For Codex

Use this only for nontrivial implementation work:

- New feature module with more than about 50 lines of new code.
- Architecture changes: new files, new modules, interface changes.
- Performance-sensitive path changes.

Do not force this for small bug fixes, style tweaks, config-only changes, or docs-only changes.

### Roles

- Generator: implements the code. This is usually the main session; spawn a `worker` only when the implementation chunk is large or isolated.
- Reviewer: a short-lived Codex subagent spawned with `spawn_agent` to review a checkpoint.

Reviewer priorities:

1. Correctness and edge cases.
2. Security, including OWASP-style risks where relevant.
3. Consistency with existing architecture.
4. Performance impact.

Do not spend review budget on low-value naming/style/import-order nits unless they affect behavior.

### Codex Tool Mapping

Claude `TeamCreate`/`SendMessage` maps to Codex as:

- Spawn reviewer: `spawn_agent(agent_type="default", message="... review ...")`.
- Send follow-up or re-review: `send_input(target=<agent_id>, message="... review ...")`.
- Wait only when the reviewer result blocks the next step: `wait_agent`.
- Close the reviewer after PASS: `close_agent(target=<agent_id>)`.

Codex subagents are explicit-delegation tools. Only spawn them when the user has authorized subagents or the current session instructions make reviewer delegation necessary for the change size. Keep small reviews local when spawning is not appropriate.

### Checkpoint Pattern

For each independent implementation unit:

1. Implement the unit locally, or spawn a `worker` for a disjoint large chunk.
2. Spawn a short-lived reviewer with a prompt containing `review` or `审查`.
3. Ask for verdict: `PASS`, `REVISE: <blocking issues>`, or `ESCALATE`.
4. On `REVISE`, fix and ask the same reviewer to re-review, up to 3 rounds.
5. On `PASS`, close the reviewer.

Do not batch all review at the end of a large change. Review each class, method group, module, or new file once it is coherent.

### Review Pattern Memory

Use project root `.review/log.md` for cross-checkpoint review memory when a project benefits from it.

Append format:

```markdown
## [YYYY-MM-DD HH:MM] <feature>/c<N> | PASS|REVISE|ESCALATE
Pattern: <1-2 line confirmed blocking pattern>
Context: <file:line>
```

Reviewers should read `.review/log.md` before review if it exists. It is separate from `wiki/log.md`.

## Engineering Rules

### Do Not Invent Requirements

- If requirements are ambiguous or multiple good implementations exist, ask one focused question.
- Surface contradictions instead of silently choosing one.
- When tradeoffs matter, present options and the reasoning.

### Avoid Overengineering

- Prefer the simplest correct implementation.
- Do not add wrappers, factories, managers, or abstraction layers unless the project already uses them or the user asks.
- Remove dead code, unused imports, and orphaned files created by the task.

### Keep Scope Tight

- Restrict edits to the task.
- Do not rewrite unrelated comments or code as a side effect.
- Report unrelated issues instead of fixing them without permission.

### Do Not Be A Yes-Man

- If the requested approach is flawed, say so directly and propose a better option.
- Be honest rather than agreeable.

### Declarative Thinking

- Prefer tests or concrete validation as the success definition.
- Write a naive correct version before optimizing.
- Describe the target state before listing steps.

## MCP Tool Preferences

Use the most direct source available:

| Need | Preferred tool |
|---|---|
| API/library docs | Context7 MCP if configured; otherwise official docs or package docs |
| Repository architecture | DeepWiki if available; otherwise local repo exploration |
| GitHub code | GitHub MCP if configured; otherwise `gh`/git/web as appropriate |
| Academic papers | alphaXiv if configured; otherwise arXiv/publisher/source PDF |

Typical chain: understand architecture with DeepWiki or local search, inspect concrete code with GitHub or local repo tools, confirm APIs with Context7 or official docs.
