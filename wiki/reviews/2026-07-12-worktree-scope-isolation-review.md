---
title: Review: Worktree Scope Isolation
type: review
updated: 2026-07-12 17:42
sources:
  - hooks/codex_guard.py
  - tests/test_codex_guard.py
  - wiki/contracts/2026-07-12-worktree-scope-isolation.md
  - https://learn.chatgpt.com/docs/hooks
---

# Review: Worktree Scope Isolation

## Verdict

PASS

## Contract coverage

- Worktree state records the resolved root, per-worktree Git dir, common Git dir, branch/detached HEAD, and a scope key derived from root plus Git dir. A real temporary Git repository test confirmed sibling worktrees share `common_dir` but have distinct `git_dir` and `scope_key` values.
- The implementation follows the release hook schema: common `cwd` remains the session cwd, while Bash and canonical `apply_patch` consume `tool_input.command`.
- Bash command text is never treated as file-ownership evidence, including commands that contain `apply_patch`-looking text. Calls without structured path evidence refresh the full baseline but contribute an empty scoped delta.
- Canonical `apply_patch` continues to parse its structured Add/Update/Delete paths; snapshot deltas are restricted to those declared paths, so unrelated concurrent files are not charged to the turn.
- Stop compares stored and current worktree identities and fails open with a trace record on mismatch.
- First Stop enforcement remains active when `stop_hook_active` is false or absent. A continuation Stop with `stop_hook_active=true` exits cleanly without another block.
- Stop reminder/block output remains one valid JSON object, and block diagnostics include the absolute worktree root plus branch/detached label.

## Diff risk

- Primary risky path: `hooks/codex_guard.py`, specifically filesystem attribution and Stop enforcement.
- Regression risks reviewed: false attribution from shared filesystems, false negatives for free-form Bash writes, sibling-worktree identity collisions, stale-state Stop enforcement, recursive Stop continuation, malformed Stop JSON, and extra Git/snapshot overhead.
- Bash writes intentionally fail open because the official release wire format does not expose the command's effective tool workdir. This is a documented safety boundary, not an accidental bypass claim.
- Worktree identity adds bounded Git subprocess calls. Normal PostToolUse reuses stored identity; existing repository snapshots remain the dominant cost.
- Unrelated dirty-worktree files shown by `git status` were not edited or reverted during review.

## Validation evidence

- `python3 -m py_compile hooks/codex_guard.py tests/test_codex_guard.py`: exit 0.
- `python3 -m unittest discover -s tests -v`: 26 tests run, all `OK`.
- Targeted regressions passed:
  - Bash with no path evidence does not claim an external change.
  - Bash containing patch text does not claim a same-name session-root collision.
  - Canonical `apply_patch` claims only its declared path.
  - Sibling Git worktrees have distinct identities.
  - Stop identity mismatch fails open.
  - First Stop emits `decision: block`; active continuation Stop emits nothing.
- Manual two-worktree simulation: created primary and sibling Git worktrees under `/tmp`; confirmed `main`/`sibling` identities had the same common dir but different scope keys, and a Bash command aimed at the sibling did not claim a concurrent same-name change in the primary. Result: PASS.
- `git diff --check -- hooks/codex_guard.py tests/test_codex_guard.py wiki/contracts/2026-07-12-worktree-scope-isolation.md`: no errors.

## Issues

- Initial review returned `REVISE`: mismatch detection depended on synthetic tool-level `workdir` fields that the official hook wire format does not provide, leaving a same-relative-path collision possible.
- The revision removed that dependency and stopped parsing Bash command text as ownership evidence. The new collision regression now exercises the official Bash `command` input boundary.
- The first manual validation fixture failed before exercising harness code because a dynamically imported dataclass module was not registered in `sys.modules`. The corrected fixture passed; this was a reviewer-fixture issue, not an implementation failure.
- No remaining blocking correctness, security, architecture, or performance issue was found within contract scope.

## Required fixes before merge

- No implementation fixes required.
- Complete the durable wiki ingest for this change: update the hook page, index, and append-only log, then index this review artifact.

## Wiki ingest check

- [x] contract page exists and matches the official hook schema boundary
- [x] review artifact created with `Verdict: PASS`
- [ ] `wiki/hooks/codex-guard.md` updated with worktree/path-attribution and `stop_hook_active` behavior
- [ ] `wiki/index.md` links the contract and review
- [ ] `wiki/log.md` includes the ingest entry

## See Also

- [Worktree Scope Isolation Contract](../contracts/2026-07-12-worktree-scope-isolation.md)
- [Codex Loop Harness](../hooks/codex-guard.md)
- [Session Isolation Hardening](../contracts/2026-07-01-session-isolation-hardening.md)
