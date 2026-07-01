---
title: Wiki Schema Template
type: template-note
updated: 2026-07-01 20:22
sources:
  - templates/wiki-schema.md
  - AGENTS.md
  - SCHEMA.md
---

# Wiki Schema Template

`templates/wiki-schema.md` is the reusable skeleton for initializing an LLM Wiki in another project. It is intentionally generic and must be customized during init.

## Template Shape

The template contains placeholders for:

- one-sentence project description;
- project structure table;
- wiki directory structure;
- page types;
- naming, frontmatter, and cross-reference conventions;
- ingest, query, lint, and log workflows.

The template uses a minimal example set of page types: `overview`, `source-summary`, and `concept`. A real project should replace those with domain-specific page types.

## Intended Use

`AGENTS.md` says wiki initialization should use the `$init-wiki` skill instead of manually copying the template. The template is a starting point only: init should customize the project description, source map, page taxonomy, default ingest targets, exclusions, and workflow details.

For this Codex home, `SCHEMA.md` is already the customized schema derived from the template. It adds Codex-specific page types such as `codex-config`, `lifecycle-hook`, `skill-package`, `template-note`, `runtime-state`, and `decision`.

## See Also

- [Codex Home Overview](../overview.md)
- [System Skills](../skills/system-skills.md)
- [Runtime State](../ops/runtime-state.md)
