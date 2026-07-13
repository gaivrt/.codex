import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("codex_guard", ROOT / "hooks" / "codex_guard.py")
codex_guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = codex_guard
SPEC.loader.exec_module(codex_guard)


CONTRACT_TEXT = """# Contract: test

## Original request
Implement the governed change.

## Scope
Only the requested harness behavior.

## Non-goals
No unrelated changes.

## Acceptance criteria
- Governed behavior works.

## Required validation
- Run the harness tests.

## Risk class
Governed harness policy.

## Reviewer checklist
- Check correctness and enforcement boundaries.
"""


def review_text(contract: str = "wiki/contracts/test.md", *, explicit_validation: bool = True) -> str:
    validation = (
        "- Command: `python3 -m unittest discover -s tests`\n- Result: PASS (exit 0)"
        if explicit_validation
        else "Tests looked good."
    )
    return f"""# Review: test

## Contract
[{contract}]({contract})

## Verdict
PASS

## Validation evidence
{validation}

## Blocking issues
None.

## Residual risk
None.

## Required fixes before merge
None.

## Wiki check
Current.
"""


class CodexGuardV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.state_dir = self.tmp / "state"
        self.old_state_dir = codex_guard.STATE_DIR
        codex_guard.STATE_DIR = self.state_dir
        self.root = self.tmp / "repo"
        self.root.mkdir()
        (self.root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
        (self.root / "SCHEMA.md").write_text("# schema\n", encoding="utf-8")
        (self.root / "wiki" / "contracts").mkdir(parents=True)
        (self.root / "wiki" / "reviews").mkdir()
        (self.root / "wiki" / "index.md").write_text("# index\n", encoding="utf-8")
        shutil.copy(ROOT / "harness_policy.yaml", self.root / "harness_policy.yaml")
        self.data = {"cwd": str(self.root), "session_id": "session-a", "turn_id": "turn-1"}

    def tearDown(self) -> None:
        codex_guard.STATE_DIR = self.old_state_dir
        shutil.rmtree(self.tmp)

    def capture(self, function, data: dict | None = None) -> str:
        output = io.StringIO()
        with redirect_stdout(output):
            function(data or self.data)
        return output.getvalue()

    def begin(self, prompt: str = "Implement an ordinary feature") -> str:
        payload = dict(self.data, prompt=prompt)
        return self.capture(codex_guard.hook_user_prompt, payload)

    def state(self) -> dict:
        return codex_guard.load_state(codex_guard.governed_state_path(self.data))

    def patch(self, *paths: str, tool_name: str = "functions.apply_patch") -> str:
        declarations = "\n".join(f"*** Update File: {path}" for path in paths)
        payload = dict(
            self.data,
            tool_name=tool_name,
            tool_input={"command": f"*** Begin Patch\n{declarations}\n*** End Patch"},
        )
        return self.capture(codex_guard.hook_post_tool, payload)

    def create_current_artifacts(
        self,
        *,
        contract: str = "wiki/contracts/test.md",
        review_contract: str | None = None,
        explicit_validation: bool = True,
    ) -> tuple[Path, Path]:
        contract_path = self.root / contract
        contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        review_path = self.root / "wiki/reviews/test-review.md"
        review_path.write_text(
            review_text(review_contract or contract, explicit_validation=explicit_validation),
            encoding="utf-8",
        )
        return contract_path, review_path

    def test_policy_has_no_size_or_command_gates(self) -> None:
        policy = codex_guard.load_harness_policy(self.root)
        self.assertEqual(policy["policy_version"], 3)
        self.assertNotIn("thresholds", policy)
        self.assertNotIn("validation_commands", policy)
        self.assertEqual(policy["enforcement"]["missing_governed_artifacts"], "block")

    def test_governed_policy_patterns_cover_objective_risk_paths(self) -> None:
        policy = codex_guard.load_harness_policy(self.root)
        paths = [
            "hooks/guard.py",
            "auth/session.py",
            "src/auth.py",
            ".github/workflows/ci.yml",
            "deploy/release.sh",
            "src/permission_check.py",
        ]
        flags = codex_guard.governed_flags_for_paths(paths, policy)
        self.assertEqual(len(flags), len(paths))
        self.assertEqual(codex_guard.governed_flags_for_paths(["src/author.py"], policy), [])

    def test_latin_prompt_terms_use_token_boundaries(self) -> None:
        policy = codex_guard.load_harness_policy(self.root)
        self.assertEqual(codex_guard.prompt_risk_reason("Implement author metadata", policy), "")
        self.assertEqual(codex_guard.prompt_risk_reason("Implement auth metadata", policy), "auth")

    def test_performance_sensitive_optimize_and_update_are_actionable(self) -> None:
        policy = codex_guard.load_harness_policy(self.root)
        prompts = [
            "Optimize this performance-sensitive loop",
            "优化这个性能敏感路径",
            "Update this performance-sensitive loop",
            "更新这个性能敏感路径",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                self.assertTrue(codex_guard.prompt_risk_reason(prompt, policy))

    def test_post_tool_matcher_targets_only_structured_file_tools(self) -> None:
        config = json.loads((ROOT / "hooks.json").read_text(encoding="utf-8"))
        matcher = config["hooks"]["PostToolUse"][0]["matcher"]
        self.assertIsNotNone(re.fullmatch(matcher, "functions.apply_patch"))
        self.assertIsNotNone(re.fullmatch(matcher, "multi_tool_use.parallel"))
        self.assertIsNone(re.fullmatch(matcher, "functions.exec_command"))
        self.assertIsNone(re.fullmatch(matcher, "Bash"))

    def test_ordinary_large_change_is_silent(self) -> None:
        self.begin()
        (self.root / "feature.py").write_text("value = 1\n" * 10_000, encoding="utf-8")
        self.assertEqual(self.patch("feature.py"), "")
        state = self.state()
        self.assertEqual(state["changed_paths"], ["feature.py"])
        self.assertFalse(state["governed"])
        self.assertEqual(self.capture(codex_guard.hook_stop), "")

    def test_no_path_tool_skips_state_lock(self) -> None:
        payload = dict(self.data, tool_name="functions.exec_command", tool_input={"cmd": "git status"})
        with mock.patch.object(
            codex_guard, "locked_governed_state", side_effect=AssertionError("state lock used")
        ):
            self.assertEqual(self.capture(codex_guard.hook_post_tool, payload), "")

    def test_bash_patch_text_is_not_file_evidence(self) -> None:
        self.begin()
        payload = dict(
            self.data,
            tool_name="Bash",
            tool_input={"command": "apply_patch <<'PATCH'\n*** Update File: hooks/guard.py\nPATCH"},
        )
        self.assertEqual(self.capture(codex_guard.hook_post_tool, payload), "")
        self.assertEqual(self.state()["changed_paths"], [])

    def test_apply_patch_uses_only_declared_paths(self) -> None:
        self.begin()
        payload = dict(
            self.data,
            tool_name="apply_patch",
            tool_input={
                "command": "*** Begin Patch\n*** Update File: feature.py\n+ mentions hooks/guard.py\n*** End Patch"
            },
        )
        self.capture(codex_guard.hook_post_tool, payload)
        self.assertEqual(self.state()["changed_paths"], ["feature.py"])
        self.assertFalse(self.state()["governed"])

    def test_parallel_nested_apply_patch_is_attributed(self) -> None:
        self.begin()
        payload = dict(
            self.data,
            tool_name="multi_tool_use.parallel",
            tool_input={
                "tool_uses": [
                    {
                        "recipient_name": "functions.apply_patch",
                        "parameters": {
                            "command": "*** Begin Patch\n*** Update File: hooks/guard.py\n*** End Patch"
                        },
                    }
                ]
            },
        )
        output = self.capture(codex_guard.hook_post_tool, payload)
        self.assertIn("governed change detected", output)
        self.assertTrue(self.state()["governed"])

    def test_governed_path_triggers_one_nudge(self) -> None:
        self.begin()
        first = self.patch("hooks/guard.py")
        second = self.patch("hooks/other.py")
        self.assertIn("governed change detected", first)
        self.assertEqual(second, "")
        self.assertEqual(self.state()["governed_paths"], ["hooks/guard.py", "hooks/other.py"])

    def test_sensitive_implementation_prompt_plus_code_is_governed(self) -> None:
        self.begin("请实现 security hardening")
        self.patch("feature.py")
        state = self.state()
        self.assertTrue(state["governed"])
        self.assertIn("prompt:security", state["risk_flags"])

    def test_sensitive_discussion_is_not_governed(self) -> None:
        self.begin("讨论 security architecture，不修改代码")
        self.patch("feature.py")
        self.assertFalse(self.state()["governed"])

    def test_external_operation_without_file_write_is_not_governed(self) -> None:
        self.begin("Implement the deploy operation")
        payload = dict(self.data, tool_name="Bash", tool_input={"command": "deploy --dry-run"})
        self.capture(codex_guard.hook_post_tool, payload)
        self.assertFalse(self.state()["governed"])

    def test_generated_paths_and_ordinary_guidance_are_not_governed(self) -> None:
        self.begin()
        self.patch(".pytest_cache/generated.py", "AGENTS.md", "SCHEMA.md")
        state = self.state()
        self.assertEqual(state["changed_paths"], ["AGENTS.md", "SCHEMA.md"])
        self.assertFalse(state["governed"])

    def test_session_and_turn_state_are_isolated(self) -> None:
        self.begin()
        first = codex_guard.governed_state_path(self.data)
        other_session = dict(self.data, session_id="session-b")
        other_turn = dict(self.data, turn_id="turn-2")
        self.assertNotEqual(first, codex_guard.governed_state_path(other_session))
        self.assertNotEqual(first, codex_guard.governed_state_path(other_turn))

    def test_session_id_prefers_explicit_value(self) -> None:
        with mock.patch.dict(os.environ, {"CODEX_SESSION_ID": "environment"}):
            self.assertEqual(codex_guard.session_id({"session_id": "explicit"}), "explicit")

    def test_bootstrap_is_deduplicated_and_policy_change_warns(self) -> None:
        first = self.capture(codex_guard.hook_session_start)
        second = self.capture(codex_guard.hook_session_start)
        self.assertIn("Wiki bootstrap", first)
        self.assertEqual(second, "")
        policy_path = self.root / "harness_policy.yaml"
        policy_path.write_text(policy_path.read_text() + "\n# changed\n", encoding="utf-8")
        third = self.capture(codex_guard.hook_session_start)
        self.assertIn("start a new Codex session", third)

    def test_legacy_bootstrap_state_requests_a_new_session(self) -> None:
        identity = codex_guard.worktree_identity(self.root)
        codex_guard.save_state(
            codex_guard.meta_path(self.data),
            {"wiki_bootstrap": {"scope_key": identity["scope_key"]}},
        )
        output = self.capture(codex_guard.hook_session_start)
        self.assertIn("Harness V3 replaced the active policy", output)

    def test_non_git_worktree_identity_is_root_scoped(self) -> None:
        other = self.tmp / "other"
        other.mkdir()
        first = codex_guard.worktree_identity(self.root)
        same = codex_guard.worktree_identity(self.root)
        different = codex_guard.worktree_identity(other)
        self.assertTrue(codex_guard.same_worktree(first, same))
        self.assertFalse(codex_guard.same_worktree(first, different))

    def test_preexisting_artifacts_do_not_satisfy_current_turn(self) -> None:
        (self.root / "wiki/contracts/test.md").write_text(CONTRACT_TEXT, encoding="utf-8")
        (self.root / "wiki/reviews/test-review.md").write_text(review_text(), encoding="utf-8")
        self.begin()
        self.patch("hooks/guard.py")
        touched = os.stat(self.root).st_mtime_ns + 1_000_000
        os.utime(self.root / "wiki/contracts/test.md", ns=(touched, touched))
        os.utime(self.root / "wiki/reviews/test-review.md", ns=(touched, touched))
        evidence = codex_guard.evaluate_artifacts(self.root, self.state())
        self.assertEqual(evidence["missing"], ["contract", "current_pass_review"])

    def test_current_contract_and_fresh_bound_pass_review_satisfy_gate(self) -> None:
        self.begin()
        self.patch("hooks/guard.py")
        self.create_current_artifacts()
        evidence = codex_guard.evaluate_artifacts(self.root, self.state())
        self.assertEqual(evidence["missing"], [])
        self.assertEqual(self.capture(codex_guard.hook_stop), "")

    def test_review_must_bind_to_current_contract(self) -> None:
        (self.root / "wiki/contracts/old.md").write_text(CONTRACT_TEXT, encoding="utf-8")
        self.begin()
        self.patch("hooks/guard.py")
        self.create_current_artifacts(review_contract="wiki/contracts/old.md")
        evidence = codex_guard.evaluate_artifacts(self.root, self.state())
        self.assertEqual(evidence["missing"], ["current_pass_review"])

    def test_review_must_have_explicit_validation_command_and_result(self) -> None:
        self.begin()
        self.patch("hooks/guard.py")
        self.create_current_artifacts(explicit_validation=False)
        evidence = codex_guard.evaluate_artifacts(self.root, self.state())
        self.assertEqual(evidence["missing"], ["current_pass_review"])

    def test_validation_rejects_pass_with_nonzero_exit(self) -> None:
        sections = codex_guard.markdown_sections(
            "## Validation evidence\n- Command: `python3 -m unittest`\n- Result: PASS (exit 1)\n"
        )
        self.assertFalse(codex_guard.validation_is_explicit(sections))

    def test_review_becomes_stale_after_later_code_edit(self) -> None:
        self.begin()
        self.patch("hooks/guard.py")
        self.create_current_artifacts()
        self.patch("hooks/guard.py")
        review_path = self.root / "wiki/reviews/test-review.md"
        review_path.write_text(review_path.read_text(encoding="utf-8"), encoding="utf-8")
        evidence = codex_guard.evaluate_artifacts(self.root, self.state())
        self.assertEqual(evidence["missing"], ["current_pass_review"])

    def test_ordinary_stop_is_silent_and_governed_stop_blocks(self) -> None:
        self.begin()
        self.patch("feature.py")
        self.assertEqual(self.capture(codex_guard.hook_stop), "")
        self.patch("hooks/guard.py")
        output = self.capture(codex_guard.hook_stop)
        payload = json.loads(output)
        self.assertEqual(payload["decision"], "block")
        self.assertIn("contract", payload["reason"])
        self.assertIn("current_pass_review", payload["reason"])

    def test_stop_loop_guard_is_silent(self) -> None:
        self.begin()
        self.patch("hooks/guard.py")
        output = self.capture(codex_guard.hook_stop, dict(self.data, stop_hook_active=True))
        self.assertEqual(output, "")

    def test_worktree_mismatch_fails_open(self) -> None:
        self.begin()
        self.patch("hooks/guard.py")
        with codex_guard.locked_governed_state(self.data) as (_, state):
            state["worktree"] = {"scope_key": "different", "root": "/elsewhere"}
        self.assertEqual(self.capture(codex_guard.hook_stop), "")

    def test_legacy_snapshot_and_validation_trackers_are_removed(self) -> None:
        self.assertFalse(hasattr(codex_guard, "build_snapshot"))
        self.assertFalse(hasattr(codex_guard, "record_validation"))
        self.assertFalse(hasattr(codex_guard, "compile_changed_python"))


if __name__ == "__main__":
    unittest.main()
