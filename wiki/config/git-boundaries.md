---
title: Git Boundaries
type: codex-config
updated: 2026-07-01 20:22
sources:
  - AGENTS.md
  - README.md
  - .gitignore
  - SCHEMA.md
---

# Git Boundaries

This repository is meant to synchronize human-maintained Codex rules and tools, not local Codex runtime state. The durable source set is configuration, hooks, rules, skills, templates, schema, and wiki pages.

## Durable Commit Candidates

README's first-commit guidance names the durable set: `.gitignore`, `README.md`, `AGENTS.md`, `config.toml`, `hooks.json`, `hooks/codex_guard.py`, `rules/default.rules`, `skills/.system`, and `templates/wiki-schema.md`. With the wiki enabled, `SCHEMA.md` and `wiki/` also belong in the maintainable set.

## Excluded Categories

`.gitignore` excludes:

- credentials and local identity: `auth.json`, `.credentials.json`, `installation_id`;
- Codex runtime state: `*.sqlite`, WAL/SHM files, `history.jsonl`, `models_cache.json`, `version.json`, `.personality_migration`;
- runtime directories: `cache/`, `log/`, `sessions/`, `shell_snapshots/`, `tmp/`, `.tmp/`, `app-server-control/`, `memories/`;
- standalone binaries: `packages/standalone/`;
- generated Python caches and migration/edit backups.

These exclusions are also wiki ingest boundaries. Their roles may be described, but their contents should not be read into the wiki.

## Collaboration Rules

`AGENTS.md` defines the repository's working discipline: speak Chinese in normal interaction, prefer `uv` for Python and `bun` for frontend work, do not start long-running servers unless asked, do not revert unrelated user changes, and ask before remote repository operations.

When `SCHEMA.md` exists, every session must read `SCHEMA.md` and `wiki/index.md` before codebase work. Code changes that materially affect durable knowledge should update wiki pages, `wiki/index.md`, and `wiki/log.md`.

## See Also

- [Codex Configuration](codex-config.md)
- [Runtime State](../ops/runtime-state.md)
- [Codex Home Overview](../overview.md)
