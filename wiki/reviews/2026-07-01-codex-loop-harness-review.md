# Review: Codex Loop Harness

## Verdict
PASS

## Contract coverage
- Policy thresholds and enforcement modes are loaded from `harness_policy.yaml` with defaults present in `hooks/codex_guard.py`.
- Risk-based review triggers include harness self-modification, hook/config/schema/auth/migration/deploy/CI-style paths; `.github/workflows/ci.yml` now matches `**/.github/workflows/**`.
- Large/risky changes hard-block at Stop while objective blockers remain; repeated Stop attempts with missing contract/review/validation still return `2`.
- Existing valid contract artifacts can be reused across turns/restarts; review artifacts remain tied to the current risky change by changed/new review snapshot logic.
- Review artifacts require `Verdict` `PASS`; `FAIL` and `NEEDS_HUMAN` are classified as failing reviews.
- Validation evidence is tracked by configured command markers.
- Per-session trace writes to `~/.codex/tmp/hooks/<session_id>/trace.jsonl`; `wiki/log.md` remains durable ingest history.
- Wiki ingest reminders remain distinct from trace logging.
- Unexpected top-level hook errors remain fail-open through `main()`.

## Diff risk
- touched files: `hooks/codex_guard.py`, `harness_policy.yaml`, `tests/test_codex_guard.py`, `AGENTS.md`, `SCHEMA.md`, `wiki/hooks/codex-guard.md`, `wiki/config/harness-policy.md`, `wiki/decisions/adr-0001-stop-enforcement-policy.md`, `wiki/index.md`, `wiki/log.md`, `wiki/overview.md`
- risky paths: `hooks/codex_guard.py`, `harness_policy.yaml`, `AGENTS.md`, `SCHEMA.md`, hook/config/policy wiki pages
- unrelated changes: repository currently reports all listed project files as untracked, so this review did not attempt to distinguish unrelated untracked baseline changes or revert anything.

## Validation evidence
- tests run:
  - `python3 -m py_compile hooks/codex_guard.py tests/test_codex_guard.py`
  - `python3 -m unittest discover -s tests`
- commands:
  - `nl -ba hooks.json`
  - `python3 - <<'PY' ...` simulation for repeated Stop and CI risk matching
  - `python3 - <<'PY' ...` simulation for existing contract reuse with new review artifact
  - `python3 - <<'PY' ...` wiki/index link existence check
- outputs:
  - `py_compile`: exit 0, no output
  - `unittest`: `Ran 11 tests in 0.046s`, `OK`
  - repeated Stop simulation: `missing_contract_stop_rcs` was `[2, 2]`
  - CI risk simulation: `risk_flags_for_paths(['.github/workflows/ci.yml'])` returned `['risky_path:**/.github/workflows/**']`
  - existing contract reuse simulation: `existing_contract_new_review_rc` was `0`, `missing` was `[]`
  - wiki/index link check: `missing links: none`

## Issues
None.

## Required fixes before merge
None.

## Wiki ingest check
- [x] wiki/index.md updated if needed
- [x] wiki/log.md updated
- [x] durable page updated
