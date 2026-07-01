---
title: Codex Configuration
type: codex-config
updated: 2026-07-01 20:22
sources:
  - config.toml
  - harness_policy.yaml
  - hooks.json
  - rules/default.rules
---

# Codex Configuration

`config.toml` is the durable local Codex configuration for GAIVR's Codex home. It sets the default model path, trusted project roots, MCP servers, and hook trust hashes. `harness_policy.yaml` controls Codex Loop Harness thresholds, risk paths, enforcement modes, generated path exclusions, and validation markers. The files reference environment variables for provider credentials; the wiki should describe those env-var names but never record secret values.

## Model And Runtime Defaults

- Default model: `gpt-5.5` through provider `openai`.
- Reasoning: `model_reasoning_effort = "xhigh"` and `plan_mode_reasoning_effort = "xhigh"`.
- Service tier: `fast`.
- Response storage is disabled with `disable_response_storage = true`.
- Approval review is assigned to the user through `approvals_reviewer = "user"`.
- Notices for full-access warning and rate-limit model nudges are hidden.

## Providers

The custom `zetatechs` provider uses the Responses wire API at `https://api.zetatechs.com/v1` and reads credentials from `ZETATECHS_API_KEY`. This is an env-var pointer, not a stored key.

## Trusted Projects

The config marks the Codex home itself and several GAIVR project paths as trusted. These trust entries are operational defaults for known workspaces; adding a new long-lived workspace should be done deliberately and reviewed as a local trust decision.

## MCP Servers

- `context7`: launched with `npx -y @upstash/context7-mcp` for current library/API docs.
- `github`: remote MCP endpoint at GitHub Copilot's MCP API, authenticated through `GITHUB_PERSONAL_ACCESS_TOKEN`.
- `alphaXiv`: remote MCP endpoint for arXiv-oriented academic paper lookup.
- `openaiDeveloperDocs`: remote MCP endpoint for official OpenAI developer docs.

## Harness, Hooks And Rules

`hooks.json` wires Codex lifecycle events to `python3 /home/gaivr/.codex/hooks/codex_guard.py <Event>`. Config stores trusted hashes for each hook entry under `[hooks.state]`; update these only when the corresponding hook command is intentionally changed.

`harness_policy.yaml` externalizes review thresholds and Stop enforcement policy so routine policy changes do not require editing Python.

`rules/default.rules` contains approved command prefixes for recurring operations, including OpenAI docs manual fetch, `uv run`, selected `tmux` inspection commands, `ssh`, and `git clone`.

## See Also

- [Codex Guard](../hooks/codex-guard.md)
- [Harness Policy](harness-policy.md)
- [Git Boundaries](git-boundaries.md)
- [Runtime State](../ops/runtime-state.md)
