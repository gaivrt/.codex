---
title: Review: Risk-only Harness V3
type: review
updated: 2026-07-13 13:46
sources:
  - wiki/contracts/2026-07-13-risk-only-harness-v3.md
  - hooks/codex_guard.py
  - harness_policy.yaml
  - tests/test_codex_guard.py
---

# Review: Risk-only Harness V3

## Contract

`wiki/contracts/2026-07-13-risk-only-harness-v3.md`

## Verdict

PASS

## Validation evidence

Command: `python3 -m py_compile hooks/codex_guard.py tests/test_codex_guard.py && python3 -m unittest discover -s tests -v && python3 -m json.tool hooks.json >/dev/null && python3 -c 'import importlib.util, pathlib; p=pathlib.Path("hooks/codex_guard.py"); s=importlib.util.spec_from_file_location("guard", p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); policy=m.load_harness_policy(pathlib.Path(".")); assert policy["policy_version"] == 3; assert "thresholds" not in policy; assert "validation_commands" not in policy' && git diff --check -- AGENTS.md README.md SCHEMA.md harness_policy.yaml hooks.json hooks/codex_guard.py tests/test_codex_guard.py wiki/config/harness-policy.md wiki/contracts/2026-07-13-risk-only-harness-v3.md wiki/decisions/adr-0001-stop-enforcement-policy.md wiki/hooks/codex-guard.md wiki/index.md wiki/log.md wiki/overview.md`

Result: PASS (exit 0)

Focused reviewer re-check: 7 classifier, validation, and artifact-freshness regressions passed.

## Blocking issues

None. The first review found three blockers; exact auth token classification, actionable optimize/update terms, non-zero validation rejection, and content-hash freshness now close them.

## Residual risk

Bash-only writes intentionally remain fail-open because arbitrary command text does not provide reliable structured path ownership. Prompt classification remains a small policy heuristic, while objective governed paths cover enforcement and the named sensitive path families.

## Required fixes before merge

None.

## Wiki check

AGENTS, SCHEMA, README, policy documentation, hook behavior page, ADR, overview, index, and log consistently describe the risk-only model and content-based artifact freshness.
