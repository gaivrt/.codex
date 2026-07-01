---
title: System Skills
type: skill-package
updated: 2026-07-01 20:22
sources:
  - skills/.system/imagegen/SKILL.md
  - skills/.system/openai-docs/SKILL.md
  - skills/.system/plugin-creator/SKILL.md
  - skills/.system/skill-creator/SKILL.md
  - skills/.system/skill-installer/SKILL.md
---

# System Skills

`skills/.system/` contains preinstalled Codex system skills. The wiki records their purpose and navigation points, not their full instructions.

## imagegen

Use for raster image generation or editing: photos, illustrations, textures, sprites, mockups, transparent cutouts, and similar bitmap assets. The default path is the built-in `image_gen` tool. CLI fallback through `scripts/image_gen.py` is reserved for explicit CLI/API/model requests or confirmed native-transparency fallback.

Important resources:

- `scripts/image_gen.py`: fallback CLI with `generate`, `edit`, and `generate-batch`.
- `scripts/remove_chroma_key.py`: local alpha extraction helper for built-in transparent-image workflows.
- `references/prompting.md` and `references/sample-prompts.md`: shared prompt guidance.
- `references/cli.md`, `references/image-api.md`, `references/codex-network.md`: CLI-only fallback details.

## openai-docs

Use for OpenAI product/API documentation, Codex self-knowledge, model selection, latest-model guidance, and model or prompt upgrades. It prioritizes OpenAI Developer Docs MCP, uses a Codex manual helper for broad Codex questions, and restricts web fallback to official OpenAI domains.

Important resources:

- `scripts/fetch-codex-manual.mjs`: fetches and outlines the Codex manual into a temp cache.
- `scripts/resolve-latest-model-info.js`: resolves latest/current model migration guidance.
- `references/latest-model.md`, `references/upgrade-guide.md`, `references/prompting-guide.md`: bundled fallbacks.

## plugin-creator

Use to scaffold or update Codex plugins with `.codex-plugin/plugin.json`, optional folders, and personal marketplace entries. The default marketplace path is `~/.agents/plugins/marketplace.json`; repo/team marketplace work is opt-in.

Important resources:

- `scripts/create_basic_plugin.py`: plugin and marketplace scaffold.
- `scripts/validate_plugin.py`: plugin validation.
- `scripts/update_plugin_cachebuster.py`: local plugin update flow.
- `scripts/read_marketplace_name.py`: reads marketplace names.
- `references/plugin-json-spec.md` and `references/installing-and-updating.md`: manifest and reinstall guidance.

## skill-creator

Use to create or update Codex skills. It defines skill anatomy, progressive disclosure, naming, initialization, validation, and forward-testing workflow. It emphasizes concise `SKILL.md` instructions, optional `agents/openai.yaml`, scripts, references, and assets.

Important resources:

- `scripts/init_skill.py`: creates a new skill skeleton.
- `scripts/generate_openai_yaml.py`: regenerates UI metadata.
- `scripts/quick_validate.py`: validates frontmatter and naming.
- `references/openai_yaml.md`: UI metadata field reference.

## skill-installer

Use to list and install Codex skills from OpenAI curated/experimental collections or another GitHub repo path. Its scripts use network access, install into `$CODEX_HOME/skills`, and abort if the destination already exists.

Important resources:

- `scripts/list-skills.py`: lists curated or experimental skills.
- `scripts/install-skill-from-github.py`: installs one or more skills from GitHub.
- `scripts/github_utils.py`: shared GitHub helper logic.

## Non-Ingested Skill Assets

Skill image assets and license files are durable package files, but they are not operational instructions for this ingest. They should be left as package assets unless a future task specifically asks to audit assets or licensing.

## See Also

- [Codex Configuration](../config/codex-config.md)
- [Git Boundaries](../config/git-boundaries.md)
- [Wiki Schema Template](../templates/wiki-schema-template.md)
