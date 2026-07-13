# Global Codex Guidance

## Communication And Environment

- Normal interaction uses Chinese; keep clearer technical terms in English.
- The user is GAIVR and may be called 盖尔. The user uses vim.
- Environment: Win11 WSL. Prefer `uv` for Python and `bun` for frontend work.
- Do not start long-running servers unless explicitly requested; provide the command instead.
- If asked to record progress, update `/docs/DEV_LOG.md` with date, time, and concrete work.
- Keep modules concise and focused. Write long documents in edits of roughly 1,000 words or less.

## Session Bootstrap

When the project root contains `SCHEMA.md`:

1. On the first non-trivial codebase task for a session/worktree, read `SCHEMA.md` and `wiki/index.md`.
2. Do not reread them in the same session unless their content changed, the worktree changed, or relevant context was lost after compaction.
3. Read at most one relevant wiki page first; expand only when it is insufficient.
4. Fall back to source files for facts not covered by the wiki.

Do not rely on memory across sessions. `AGENTS.md` controls behavior; `SCHEMA.md` controls durable knowledge structure.

## Risk-Only Harness

The default path is silent. Change size, ordinary new files, planning, and discussion never trigger process gates.

- Ordinary implementation needs no contract or reviewer, regardless of line count.
- Governed implementation requires a short contract under `wiki/contracts/` and one coherent reviewer pass after implementation and targeted validation are complete.
- Governed paths include hook enforcement, harness policy, auth, sandbox, permissions, migrations, deploy, and CI. An explicit security, permission, deployment, migration, CI, or performance-sensitive implementation request is also governed when paired with a concrete code/config write.
- Ordinary `AGENTS.md`, `SCHEMA.md`, documentation, and general config edits are not governed by path alone.
- Stop may hard-block only a governed turn with an objectively missing current contract or current PASS review containing explicit validation evidence.

External operations are a separate control plane: obtain any required user authorization, state scope or budget when material, and report an execution receipt. An external operation alone does not require a code contract or review artifact.

## Artifact Ownership

Avoid repeating the same narrative across artifacts:

- Contract: target, scope, non-goals, acceptance criteria, required validation, risk class, reviewer checklist.
- Review artifact: contract link, verdict, concrete validation evidence, blocking issues, residual risk, wiki check.
- Wiki: current durable behavior only, not task discussion or review history.
- `wiki/log.md`: one concise durable change record.

Keep contract and review artifacts short. Valid review verdicts are `PASS`, `FAIL`, and `NEEDS_HUMAN`.

## Wiki Ingest

Ingest only when source changes create durable project knowledge:

- Small, focused changes: the main agent may update the relevant page, `wiki/index.md`, and `wiki/log.md` directly.
- Large, cross-cutting, or delegated implementation: use a focused wiki-ingest subagent when available.
- Documentation-only wording, trivial fixes, and runtime-only changes do not require ingest unless they change durable behavior.
- Keep `wiki/index.md` current and `wiki/log.md` append-only.
- `wiki/` must remain Git-tracked.

Before Git-managed checkpoints, check for stale pages, contradictions, orphan pages, broken links, and missing index/log entries relevant to the change.

## Safety Boundaries

- Do not read or ingest credentials, tokens, sqlite databases, session transcripts, cache, tmp, standalone binaries, or backups unless explicitly asked for recovery or inspection.
- Preserve unrelated user changes in a dirty worktree.
- Never use destructive Git or filesystem commands without explicit authorization.
- Ask before remote repository operations.
- Hook Stop blocks are authoritative when they identify missing objective risky-change artifacts.
- Unexpected hook failures should remain fail-open and be diagnosed from non-sensitive evidence.

## Engineering Workflow

- Before implementation, inspect project structure, package manager, config pattern, and directory conventions.
- For bug fixes, prefer a failing test first, then iterate until it passes.
- Define success with tests or other concrete validation.
- During iteration, run the narrowest relevant test. At a coherent checkpoint, run the related suite once; reserve full-suite validation for governed, release, commit, or explicitly requested work.
- Prefer the simplest correct implementation; avoid speculative wrappers, factories, and managers.
- Keep edits scoped. Report unrelated problems instead of fixing them silently.
- Surface ambiguous requirements and meaningful tradeoffs instead of inventing requirements.
- If the same approach fails three times, restate the root-cause hypothesis and switch strategy.
- If the same file has been read more than twice, summarize known and unclear facts before continuing.
- Remove dead code, unused imports, and task-created orphan files.

## Review Workflow

For governed changes, use one short-lived reviewer after a coherent checkpoint. Do not review incremental fragments. Review priorities:

1. Correctness and edge cases.
2. Security and permission boundaries.
3. Architecture consistency.
4. Performance impact.

The reviewer returns `PASS`, `FAIL: <blocking issues>`, or `NEEDS_HUMAN`. On `FAIL`, fix only the blockers and ask the same reviewer to re-check, with at most two focused re-checks. Governed changes require a concise `wiki/reviews/*-review.md` artifact with `Verdict: PASS` before completion.

Do not require reviewers for ordinary work based on size, or for small bug fixes, style changes, docs-only work, and ordinary config edits.

## Git

- Do not add `Co-Authored-By` lines.
- Keep commit messages short.
- Create a branch when it materially reduces collision risk.
- Do not revert unrelated user changes.
- Do not commit credentials, runtime state, generated caches, or standalone binaries.

## Tool Preferences

Use the most direct authoritative source available:

- Local wiki, then local source, for repository behavior.
- Context7 or official documentation for APIs and libraries.
- DeepWiki or local search for architecture.
- GitHub tools or `git`/`gh` for repository code.
- alphaXiv, arXiv, publisher pages, or source PDFs for papers.

Prefer `rg`/`rg --files` for local search. Prefer parallel read-only checks when independent.
