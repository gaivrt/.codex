import importlib.util
import io
import shutil
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

    def test_line_count_threshold_sets_review_required(self) -> None:
        self.seed_gan()
        (self.root / "feature.py").write_text("\n".join(f"line_{i} = {i}" for i in range(60)), encoding="utf-8")
        codex_guard.track_gan_changes(self.data, [], self.root)
        state = self.read_gan()
        self.assertTrue(state["review_required"])
        self.assertTrue(state["triggered"])
        self.assertGreaterEqual(state["total_net_lines"], 50)

    def test_risky_path_sets_review_required_for_small_diff(self) -> None:
        self.seed_gan()
        (self.root / "AGENTS.md").write_text("# agents\nsmall change\n", encoding="utf-8")
        codex_guard.track_gan_changes(self.data, [], self.root)
        state = self.read_gan()
        self.assertTrue(state["review_required"])
        self.assertTrue(state["risky_change"])
        self.assertTrue(any(flag.startswith("harness_self:") for flag in state["risk_flags"]))

    def test_ci_workflow_path_is_risky(self) -> None:
        policy = codex_guard.load_harness_policy(self.root)
        flags = codex_guard.risk_flags_for_paths([".github/workflows/ci.yml"], policy)
        self.assertTrue(any(flag.startswith("risky_path:") for flag in flags))

    def test_generated_cache_files_are_ignored(self) -> None:
        self.assertFalse(codex_guard.should_track_gan_path(self.root, "cache/generated.py"))
        self.assertFalse(codex_guard.should_track_gan_path(self.root, "tmp/generated.py"))
        self.assertFalse(codex_guard.should_track_gan_path(self.root, "dist/generated.py"))

    def test_large_change_missing_contract_blocks(self) -> None:
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["project_root"] = str(self.root)
            state["triggered"] = True
            state["review_required"] = True
            state["large_change"] = True
            state["total_net_lines"] = 120
            state["contract_snapshot"] = {}
            state["review_snapshot"] = {}
        with redirect_stderr(io.StringIO()):
            rc = codex_guard.enforce_gan(self.data, self.root)
        self.assertEqual(rc, 2)

    def test_large_change_missing_contract_blocks_repeated_stop(self) -> None:
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["project_root"] = str(self.root)
            state["triggered"] = True
            state["review_required"] = True
            state["large_change"] = True
            state["total_net_lines"] = 120
            state["contract_snapshot"] = {}
            state["review_snapshot"] = {}
        with redirect_stderr(io.StringIO()):
            first = codex_guard.enforce_gan(self.data, self.root)
            second = codex_guard.enforce_gan(self.data, self.root)
        self.assertEqual(first, 2)
        self.assertEqual(second, 2)

    def test_large_change_missing_review_blocks(self) -> None:
        (self.root / "wiki" / "contracts").mkdir()
        (self.root / "wiki" / "contracts" / "2026-07-01-test.md").write_text(CONTRACT_TEXT, encoding="utf-8")
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["project_root"] = str(self.root)
            state["triggered"] = True
            state["review_required"] = True
            state["large_change"] = True
            state["validation_seen"] = True
            state["total_net_lines"] = 120
            state["contract_snapshot"] = {}
            state["review_snapshot"] = {}
        with redirect_stderr(io.StringIO()):
            rc = codex_guard.enforce_gan(self.data, self.root)
        self.assertEqual(rc, 2)

    def test_pass_review_and_validation_allows_large_change(self) -> None:
        (self.root / "wiki" / "contracts").mkdir()
        (self.root / "wiki" / "reviews").mkdir()
        (self.root / "wiki" / "contracts" / "2026-07-01-test.md").write_text(CONTRACT_TEXT, encoding="utf-8")
        (self.root / "wiki" / "reviews" / "2026-07-01-test-review.md").write_text(
            REVIEW_PASS_TEXT,
            encoding="utf-8",
        )
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["project_root"] = str(self.root)
            state["triggered"] = True
            state["review_required"] = True
            state["large_change"] = True
            state["validation_seen"] = True
            state["total_net_lines"] = 120
            state["contract_snapshot"] = {}
            state["review_snapshot"] = {}
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
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["project_root"] = str(self.root)
            state["triggered"] = True
            state["review_required"] = True
            state["large_change"] = True
            state["validation_seen"] = True
            state["total_net_lines"] = 120
            state["contract_snapshot"] = contract_baseline
            state["review_snapshot"] = {}
        rc = codex_guard.enforce_gan(self.data, self.root)
        self.assertEqual(rc, 0)

    def test_small_change_only_reminds(self) -> None:
        with codex_guard.locked_gan_state(self.data) as (_, state):
            state["project_root"] = str(self.root)
            state["triggered"] = True
            state["review_required"] = True
            state["total_net_lines"] = 60
            state["contract_snapshot"] = {}
            state["review_snapshot"] = {}
        with redirect_stdout(io.StringIO()):
            rc = codex_guard.enforce_gan(self.data, self.root)
        self.assertEqual(rc, 0)

    def test_wiki_ingest_missing_is_reminder_by_default(self) -> None:
        with codex_guard.locked_wiki_state(self.data) as (_, state):
            state["schema_root"] = str(self.root)
            state["code_files"] = ["feature.py"]
        with redirect_stdout(io.StringIO()):
            rc = codex_guard.enforce_wiki(self.data, self.root)
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
