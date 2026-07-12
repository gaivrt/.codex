import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("codex_guard", ROOT / "hooks" / "codex_guard.py")
codex_guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = codex_guard
SPEC.loader.exec_module(codex_guard)


CONTRACT_TEXT = """---
title: Contract
---

# Contract: test

## Original request
Implement a test change.

## Scope
hooks only.

## Non-goals
No unrelated edits.

## Acceptance criteria
- [ ] works

## Required validation
- [ ] unittest

## Risk class
risky

## Reviewer checklist
- [ ] pass
"""


REVIEW_PASS_TEXT = """---
title: Review
---

# Review: test

## Verdict
PASS

## Contract coverage
Covered.

## Diff risk
Reviewed.

## Validation evidence
unittest

## Issues
None.

## Required fixes before merge
None.

## Wiki ingest check
Done.
"""

REVIEW_LEAN_PASS_TEXT = """# Review: lean

## Verdict
PASS

## Contract
wiki/contracts/test.md

## Validation evidence
unittest passed.

## Blocking issues
None.

## Residual risk
None.

## Required fixes before merge
None.

## Wiki check
Done.
"""


class CodexGuardHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / "state"
        self.old_state_dir = codex_guard.STATE_DIR
        codex_guard.STATE_DIR = self.state
        self.root = self.tmp / "repo"
        self.root.mkdir()
        (self.root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
        (self.root / "SCHEMA.md").write_text("# schema\n", encoding="utf-8")
        (self.root / "wiki").mkdir()
        (self.root / "wiki" / "index.md").write_text("# index\n", encoding="utf-8")
        (self.root / "wiki" / "log.md").write_text("# log\n", encoding="utf-8")
        shutil.copy(ROOT / "harness_policy.yaml", self.root / "harness_policy.yaml")
        self.data = {"cwd": str(self.root), "session_id": "test-session", "turn_id": "1"}

    def tearDown(self) -> None:
        codex_guard.STATE_DIR = self.old_state_dir
        shutil.rmtree(self.tmp)

    def seed_gan(self) -> None:
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["project_root"] = str(self.root)
            state["last_snapshot"] = codex_guard.build_snapshot(self.root, codex_guard.should_track_gan_path)
            state["contract_snapshot"] = codex_guard.artifact_snapshot(self.root, "wiki/contracts/*.md")
            state["review_snapshot"] = codex_guard.artifact_snapshot(self.root, "wiki/reviews/*-review.md")

    def read_gan(self) -> dict:
        _, state = codex_guard.gan_state(self.data)
        return state

    def seed_wiki(self) -> None:
        with codex_guard.locked_wiki_state(self.data) as (_, state):
            state["schema_root"] = str(self.root)
            state["last_snapshot"] = codex_guard.build_snapshot(self.root, codex_guard.should_track_wiki_path)

    def seed_strict_change(self, *, validation: bool = False) -> None:
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["project_root"] = str(self.root)
            state["triggered"] = True
            state["contract_required"] = True
            state["review_required"] = True
            state["risky_change"] = True
            state["risk_flags"] = ["risky_path:hooks/**"]
            state["validation_seen"] = validation
            state["contract_snapshot"] = {}
            state["review_snapshot"] = {}

    def test_150_lines_require_contract_but_not_review(self) -> None:
        self.seed_gan()
        (self.root / "feature.py").write_text("\n".join(f"line_{i} = {i}" for i in range(160)), encoding="utf-8")
        patch = "*** Begin Patch\n*** Add File: feature.py\n+content\n*** End Patch"
        codex_guard.track_gan_changes(self.data, [("apply_patch", {"command": patch})], self.root)
        state = self.read_gan()
        self.assertTrue(state["contract_required"])
        self.assertFalse(state["review_required"])
        self.assertTrue(state["triggered"])
        self.assertGreaterEqual(state["total_net_lines"], 150)

    def test_300_lines_require_review(self) -> None:
        self.seed_gan()
        (self.root / "feature.py").write_text("\n".join(f"line_{i} = {i}" for i in range(320)), encoding="utf-8")
        patch = "*** Begin Patch\n*** Add File: feature.py\n+content\n*** End Patch"
        codex_guard.track_gan_changes(self.data, [("apply_patch", {"command": patch})], self.root)
        state = self.read_gan()
        self.assertTrue(state["contract_required"])
        self.assertTrue(state["review_required"])

    def test_ordinary_new_file_does_not_trigger_review(self) -> None:
        self.seed_gan()
        (self.root / "small_module.py").write_text("\n".join(f"line_{i} = {i}" for i in range(100)), encoding="utf-8")
        patch = "*** Begin Patch\n*** Add File: small_module.py\n+content\n*** End Patch"
        codex_guard.track_gan_changes(self.data, [("apply_patch", {"command": patch})], self.root)
        state = self.read_gan()
        self.assertEqual(state["new_files"], ["small_module.py"])
        self.assertFalse(state["contract_required"])
        self.assertFalse(state["review_required"])
        self.assertFalse(state["triggered"])

    def test_architecture_signal_requires_contract_only(self) -> None:
        self.seed_gan()
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["architecture_signal"] = True
        (self.root / "feature.py").write_text("enabled = True\n", encoding="utf-8")
        patch = "*** Begin Patch\n*** Add File: feature.py\n+enabled = True\n*** End Patch"
        messages, _ = codex_guard.track_gan_changes(
            self.data, [("apply_patch", {"command": patch})], self.root
        )
        state = self.read_gan()
        self.assertTrue(state["contract_required"])
        self.assertFalse(state["review_required"])
        self.assertEqual(len(messages), 1)

    def test_security_signal_requires_contract_and_review(self) -> None:
        self.seed_gan()
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["sensitive_review_signal"] = True
        (self.root / "feature.py").write_text("enabled = True\n", encoding="utf-8")
        patch = "*** Begin Patch\n*** Add File: feature.py\n+enabled = True\n*** End Patch"
        codex_guard.track_gan_changes(self.data, [("apply_patch", {"command": patch})], self.root)
        state = self.read_gan()
        self.assertTrue(state["contract_required"])
        self.assertTrue(state["review_required"])

    def test_risky_path_sets_review_required_for_small_diff(self) -> None:
        self.seed_gan()
        (self.root / "hooks").mkdir()
        (self.root / "hooks" / "guard.py").write_text("enabled = True\n", encoding="utf-8")
        patch = "*** Begin Patch\n*** Add File: hooks/guard.py\n+enabled = True\n*** End Patch"
        codex_guard.track_gan_changes(self.data, [("apply_patch", {"command": patch})], self.root)
        state = self.read_gan()
        self.assertTrue(state["contract_required"])
        self.assertTrue(state["review_required"])
        self.assertTrue(state["risky_change"])
        self.assertTrue(any(flag.startswith("harness_self:") for flag in state["risk_flags"]))

    def test_agents_and_schema_are_not_hard_risk(self) -> None:
        policy = codex_guard.load_harness_policy(self.root)
        self.assertEqual(codex_guard.risk_flags_for_paths(["AGENTS.md", "SCHEMA.md"], policy), [])

    def test_ci_workflow_path_is_risky(self) -> None:
        policy = codex_guard.load_harness_policy(self.root)
        flags = codex_guard.risk_flags_for_paths([".github/workflows/ci.yml"], policy)
        self.assertTrue(any(flag.startswith("risky_path:") for flag in flags))

    def test_generated_cache_files_are_ignored(self) -> None:
        self.assertFalse(codex_guard.should_track_gan_path(self.root, "cache/generated.py"))
        self.assertFalse(codex_guard.should_track_gan_path(self.root, "tmp/generated.py"))
        self.assertFalse(codex_guard.should_track_gan_path(self.root, "dist/generated.py"))

    def test_unattributed_external_change_is_not_charged_to_bash(self) -> None:
        self.seed_gan()
        (self.root / "external.py").write_text("\n".join(f"line_{i} = {i}" for i in range(120)), encoding="utf-8")

        codex_guard.track_gan_changes(self.data, [("Bash", {"command": "pwd"})], self.root)

        state = self.read_gan()
        self.assertEqual(state["total_net_lines"], 0)
        self.assertEqual(state["touched_files"], [])
        self.assertFalse(state["triggered"])

    def test_official_apply_patch_command_attributes_only_declared_path(self) -> None:
        self.seed_gan()
        (self.root / "external.py").write_text("external = True\n", encoding="utf-8")
        (self.root / "owned.py").write_text("owned = True\n", encoding="utf-8")
        patch = """*** Begin Patch
*** Add File: owned.py
+owned = True
*** End Patch"""

        codex_guard.track_gan_changes(self.data, [("apply_patch", {"command": patch})], self.root)

        state = self.read_gan()
        self.assertEqual(state["touched_files"], ["owned.py"])
        self.assertNotIn("external.py", state["touched_files"])

    def test_unattributed_external_code_change_does_not_trigger_wiki_ingest(self) -> None:
        self.seed_wiki()
        (self.root / "external.py").write_text("external = True\n", encoding="utf-8")

        codex_guard.track_wiki_edits(self.data, [("Bash", {"command": "pwd"})], self.root)

        _, state = codex_guard.wiki_state(self.data)
        self.assertEqual(state["code_files"], [])

    def test_bash_patch_text_does_not_claim_session_root_collision(self) -> None:
        self.seed_gan()
        (self.root / "same_name.py").write_text(
            "\n".join(f"line_{i} = {i}" for i in range(120)),
            encoding="utf-8",
        )
        command = """apply_patch <<'PATCH'
*** Begin Patch
*** Add File: same_name.py
+sibling = True
*** End Patch
PATCH"""

        codex_guard.track_gan_changes(self.data, [("Bash", {"command": command})], self.root)

        state = self.read_gan()
        self.assertFalse(state["triggered"])
        self.assertEqual(state["touched_files"], [])
        self.assertEqual(state["total_net_lines"], 0)

    def test_worktree_identity_distinguishes_sibling_worktrees(self) -> None:
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "seed"], check=True)
        sibling = self.tmp / "sibling-worktree"
        subprocess.run(
            ["git", "-C", str(self.root), "worktree", "add", "-q", "-b", "sibling", str(sibling)],
            check=True,
        )

        primary = codex_guard.worktree_identity(self.root)
        secondary = codex_guard.worktree_identity(sibling)

        self.assertNotEqual(primary["scope_key"], secondary["scope_key"])
        self.assertEqual(primary["common_dir"], secondary["common_dir"])
        self.assertNotEqual(primary["git_dir"], secondary["git_dir"])

    def test_session_id_keeps_explicit_sessions_separate(self) -> None:
        first = dict(self.data, session_id="session-a")
        second = dict(self.data, session_id="session-b")
        self.assertNotEqual(codex_guard.session_id(first), codex_guard.session_id(second))
        self.assertNotEqual(codex_guard.meta_path(first), codex_guard.meta_path(second))

    def test_wiki_bootstrap_is_once_per_session_and_hash(self) -> None:
        first = codex_guard.wiki_bootstrap_message(self.data, self.root, self.root)
        second = codex_guard.wiki_bootstrap_message(self.data, self.root, self.root)
        self.assertIn("Wiki bootstrap", first or "")
        self.assertIsNone(second)

        index = self.root / "wiki" / "index.md"
        index.write_text(index.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
        changed = codex_guard.wiki_bootstrap_message(self.data, self.root, self.root)
        self.assertIn("wiki/index.md", changed or "")

        other = self.tmp / "other-worktree"
        other.mkdir()
        moved = codex_guard.wiki_bootstrap_message(self.data, self.root, other)
        self.assertIn("Wiki bootstrap", moved or "")

    def test_discussion_prompt_does_not_emit_gan_guidance(self) -> None:
        codex_guard.wiki_bootstrap_message(self.data, self.root, self.root)
        data = dict(self.data, prompt="讨论如何实现架构和 reviewer 规则")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            codex_guard.hook_user_prompt(data)
        self.assertEqual(stdout.getvalue(), "")
        self.assertFalse(codex_guard.gan_state(data)[1]["triggered"])

    def test_unknown_session_without_process_scope_fails_open_per_hook_process(self) -> None:
        old_scope = codex_guard.codex_process_scope
        saved_env = {key: os.environ.pop(key, None) for key in codex_guard.ENV_SESSION_ID_KEYS}
        try:
            codex_guard.codex_process_scope = lambda: None
            session = codex_guard.session_id({"cwd": str(self.root)})
        finally:
            codex_guard.codex_process_scope = old_scope
            for key, value in saved_env.items():
                if value is not None:
                    os.environ[key] = value
        self.assertIn("unknown-cwd-", session)
        self.assertIn(f"hookpid{os.getpid()}-", session)

    def test_hook_process_scope_includes_process_start_time(self) -> None:
        old_getpid = codex_guard.os.getpid
        old_start = codex_guard.process_start_time
        try:
            codex_guard.os.getpid = lambda: 12345
            codex_guard.process_start_time = lambda pid: "111"
            first = codex_guard.hook_process_scope()
            codex_guard.process_start_time = lambda pid: "222"
            second = codex_guard.hook_process_scope()
        finally:
            codex_guard.os.getpid = old_getpid
            codex_guard.process_start_time = old_start
        self.assertEqual(first, "hookpid12345-111")
        self.assertEqual(second, "hookpid12345-222")
        self.assertNotEqual(first, second)

    def test_codex_process_scope_ignores_terminal_only_scope(self) -> None:
        old_getppid = codex_guard.os.getppid
        saved_tmux = os.environ.get("TMUX")
        try:
            codex_guard.os.getppid = lambda: 1
            os.environ["TMUX"] = "shared-terminal-scope"
            self.assertIsNone(codex_guard.codex_process_scope())
        finally:
            codex_guard.os.getppid = old_getppid
            if saved_tmux is None:
                os.environ.pop("TMUX", None)
            else:
                os.environ["TMUX"] = saved_tmux

    def test_risky_change_missing_contract_blocks(self) -> None:
        self.seed_strict_change()
        with redirect_stderr(io.StringIO()):
            rc = codex_guard.enforce_gan(self.data, self.root)
        self.assertEqual(rc, 2)

    def test_risky_change_missing_contract_blocks_repeated_stop(self) -> None:
        self.seed_strict_change()
        with redirect_stderr(io.StringIO()):
            first = codex_guard.enforce_gan(self.data, self.root)
            second = codex_guard.enforce_gan(self.data, self.root)
        self.assertEqual(first, 2)
        self.assertEqual(second, 2)

    def test_risky_change_missing_review_blocks(self) -> None:
        (self.root / "wiki" / "contracts").mkdir()
        (self.root / "wiki" / "contracts" / "2026-07-01-test.md").write_text(CONTRACT_TEXT, encoding="utf-8")
        self.seed_strict_change(validation=True)
        with redirect_stderr(io.StringIO()):
            rc = codex_guard.enforce_gan(self.data, self.root)
        self.assertEqual(rc, 2)

    def test_lean_review_artifact_is_accepted(self) -> None:
        (self.root / "wiki" / "reviews").mkdir()
        review = self.root / "wiki" / "reviews" / "2026-07-12-lean-review.md"
        review.write_text(REVIEW_LEAN_PASS_TEXT, encoding="utf-8")
        status = codex_guard.review_artifact_status(self.root, {})
        self.assertEqual(status["passing"], ["wiki/reviews/2026-07-12-lean-review.md"])

    def test_pass_review_and_validation_allows_risky_change(self) -> None:
        (self.root / "wiki" / "contracts").mkdir()
        (self.root / "wiki" / "reviews").mkdir()
        (self.root / "wiki" / "contracts" / "2026-07-01-test.md").write_text(CONTRACT_TEXT, encoding="utf-8")
        (self.root / "wiki" / "reviews" / "2026-07-01-test-review.md").write_text(
            REVIEW_PASS_TEXT,
            encoding="utf-8",
        )
        self.seed_strict_change(validation=True)
        rc = codex_guard.enforce_gan(self.data, self.root)
        self.assertEqual(rc, 0)

    def test_existing_valid_contract_reused_across_turns(self) -> None:
        (self.root / "wiki" / "contracts").mkdir()
        (self.root / "wiki" / "reviews").mkdir()
        contract = self.root / "wiki" / "contracts" / "2026-07-01-test.md"
        review = self.root / "wiki" / "reviews" / "2026-07-01-test-review.md"
        contract.write_text(CONTRACT_TEXT, encoding="utf-8")
        review.write_text(REVIEW_PASS_TEXT, encoding="utf-8")
        contract_baseline = codex_guard.artifact_snapshot(self.root, "wiki/contracts/*.md")
        self.seed_strict_change(validation=True)
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["contract_snapshot"] = contract_baseline
        rc = codex_guard.enforce_gan(self.data, self.root)
        self.assertEqual(rc, 0)

    def test_ordinary_large_change_stop_is_silent(self) -> None:
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["project_root"] = str(self.root)
            state["triggered"] = True
            state["contract_required"] = True
            state["review_required"] = True
            state["large_change"] = True
            state["total_net_lines"] = 320
            state["contract_snapshot"] = {}
            state["review_snapshot"] = {}
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            rc = codex_guard.enforce_gan(self.data, self.root)
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")

    def test_wiki_ingest_missing_is_silent_by_default(self) -> None:
        with codex_guard.locked_wiki_state(self.data) as (_, state):
            state["schema_root"] = str(self.root)
            state["code_files"] = ["feature.py"]
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            rc = codex_guard.enforce_wiki(self.data, self.root)
        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")

    def test_hook_stop_is_silent_for_wiki_reminder(self) -> None:
        with codex_guard.locked_wiki_state(self.data) as (_, state):
            state["schema_root"] = str(self.root)
            state["code_files"] = ["feature.py"]

        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            rc = codex_guard.hook_stop(self.data)

        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")

    def test_hook_stop_block_outputs_decision_block_json(self) -> None:
        self.seed_strict_change()

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            rc = codex_guard.hook_stop(self.data)

        self.assertEqual(rc, 0)
        self.assertEqual(stderr.getvalue(), "")
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["decision"], "block")
        self.assertIn("missing: contract", payload["reason"].lower())

    def test_hook_stop_active_prevents_recursive_block_loop(self) -> None:
        active_data = dict(self.data, stop_hook_active=True)
        with codex_guard.locked_gan_state(active_data) as (_, state):
            state["project_root"] = str(self.root)
            state["triggered"] = True
            state["contract_required"] = True
            state["review_required"] = True
            state["risky_change"] = True
            state["risk_flags"] = ["risky_path:hooks/**"]
            state["contract_snapshot"] = {}
            state["review_snapshot"] = {}

        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            rc = codex_guard.hook_stop(active_data)

        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")
        state = codex_guard.gan_state(active_data)[1]
        self.assertEqual(state["stop_blocks"], 0)

    def test_stop_block_names_checked_worktree_scope(self) -> None:
        self.seed_strict_change()
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["worktree"] = codex_guard.worktree_identity(self.root)

        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            codex_guard.hook_stop(self.data)

        payload = json.loads(stdout.getvalue())
        self.assertIn(f"Worktree: {self.root}", payload["reason"])

    def test_stop_fails_open_when_turn_worktree_identity_mismatches_cwd(self) -> None:
        sibling = self.tmp / "other-repo"
        sibling.mkdir()
        (sibling / "AGENTS.md").write_text("# other\n", encoding="utf-8")
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["project_root"] = str(self.root)
            state["worktree"] = codex_guard.worktree_identity(sibling)
            state["triggered"] = True
            state["contract_required"] = True
            state["review_required"] = True
            state["risky_change"] = True
            state["contract_snapshot"] = {}
            state["review_snapshot"] = {}

        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            rc = codex_guard.hook_stop(self.data)

        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")

    def test_hook_stop_is_silent_for_advisory_gates(self) -> None:
        with codex_guard.locked_wiki_state(self.data) as (_, state):
            state["schema_root"] = str(self.root)
            state["code_files"] = ["feature.py"]
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["project_root"] = str(self.root)
            state["triggered"] = True
            state["contract_required"] = True
            state["review_required"] = True
            state["total_net_lines"] = 320
            state["contract_snapshot"] = {}
            state["review_snapshot"] = {}

        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
            rc = codex_guard.hook_stop(self.data)

        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
