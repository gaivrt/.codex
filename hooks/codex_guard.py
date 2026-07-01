#!/usr/bin/env python3
"""Codex lifecycle discipline hooks.

This is the Codex port of the old Claude Code hook philosophy:

1. Inject the project discipline early.
2. Track concrete tool-side effects during the turn.
3. Keep Stop fail-open; reminders must never terminate a turn after ingest.

The implementation stays in one dispatcher because Codex hook handlers are
cheap command hooks and share the same per-session state files.
"""

from __future__ import annotations

import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from fnmatch import fnmatchcase
from hashlib import sha1
from pathlib import Path
from typing import Any, Callable, Iterable


GAN_REVIEW_LINE_THRESHOLD = 50
GAN_INCREMENTAL_LINE_THRESHOLD = 80
GAN_NEW_FILE_LINE_THRESHOLD = 20
GAN_INCREMENTAL_NEW_FILE_THRESHOLD = 3
GAN_LARGE_LINE_THRESHOLD = 100
GAN_LARGE_NEW_FILE_THRESHOLD = 2

DEFAULT_POLICY: dict[str, Any] = {
    "thresholds": {
        "review_net_new_lines": GAN_REVIEW_LINE_THRESHOLD,
        "incremental_reminder_lines": GAN_INCREMENTAL_LINE_THRESHOLD,
        "new_file_min_lines": GAN_NEW_FILE_LINE_THRESHOLD,
        "incremental_new_files": GAN_INCREMENTAL_NEW_FILE_THRESHOLD,
        "large_change_lines": GAN_LARGE_LINE_THRESHOLD,
        "large_change_new_files": GAN_LARGE_NEW_FILE_THRESHOLD,
    },
    "enforcement": {
        "default": "remind",
        "medium_change": "remind",
        "large_change": "block",
        "risky_change": "block",
        "harness_self_modification": "block",
        "missing_contract_for_large_change": "block",
        "missing_reviewer_for_large_change": "block",
        "missing_validation_for_large_change": "block",
        "missing_wiki_ingest": "remind",
    },
    "risky_paths": [
        "hooks/**",
        "hooks.json",
        "harness_policy.yaml",
        ".codex/**",
        "AGENTS.md",
        "SCHEMA.md",
        "**/auth/**",
        "**/migrations/**",
        "**/deploy/**",
        "**/.github/workflows/**",
        "**/config*.toml",
        "**/config*.yaml",
        "**/config*.yml",
        "**/*sandbox*",
        "**/*permission*",
    ],
    "harness_self_paths": [
        "hooks/**",
        "hooks.json",
        "harness_policy.yaml",
        "AGENTS.md",
        "SCHEMA.md",
    ],
    "generated_paths": [
        ".git/**",
        ".mypy_cache/**",
        ".pytest_cache/**",
        ".ruff_cache/**",
        ".venv/**",
        "__pycache__/**",
        "build/**",
        "data/**",
        "dist/**",
        "node_modules/**",
        "probes/results/**",
        "scratch/**",
        "cache/**",
        "tmp/**",
        ".tmp/**",
        "log/**",
        "app-server-control/**",
    ],
    "validation_commands": [
        "pytest",
        "unittest",
        "py_compile",
        "ruff",
        "mypy",
        "tsc",
        "npm test",
        "bun test",
        "cargo test",
        "go test",
    ],
}

REQUIRED_CONTRACT_SECTIONS = (
    "Original request",
    "Scope",
    "Non-goals",
    "Acceptance criteria",
    "Required validation",
    "Risk class",
    "Reviewer checklist",
)
REQUIRED_REVIEW_SECTIONS = (
    "Verdict",
    "Contract coverage",
    "Diff risk",
    "Validation evidence",
    "Issues",
    "Required fixes before merge",
    "Wiki ingest check",
)
VALID_REVIEW_VERDICTS = {"PASS", "FAIL", "NEEDS_HUMAN"}

REVIEW_RE = re.compile(r"discriminat|review|审查|critique|reviewer", re.IGNORECASE)
WIKI_INGEST_RE = re.compile(
    r"wiki[-_ ]?ingest|"
    r"ingest\b.{0,80}\b(?:into|to)\s+(?:the\s+)?(?:project\s+)?(?:wiki|knowledge\s+base)|"
    r"(?:update|write|append|maintain)\s+(?:to\s+)?(?:the\s+)?(?:project\s+)?"
    r"(?:wiki\s+pages?|wiki/index\.md|wiki/log\.md|wiki|knowledge\s+base)|"
    r"(?:更新|写入|追加|维护)\s*(?:项目)?(?:wiki\s*页面|wiki/index\.md|wiki/log\.md|wiki|知识库)|"
    r"吸收.{0,20}(?:到|进|至)\s*(?:wiki|知识库)",
    re.IGNORECASE | re.DOTALL,
)
IMPLEMENT_RE = re.compile(
    r"实现|新功能|新模块|重构|架构|新增模块|"
    r"new\s+feature|implement|refactor|new\s+module|architecture|"
    r"build\s+a|create\s+a\s+(?:new\s+)?(?:module|component|service|system)",
    re.IGNORECASE,
)

PROJECT_MARKERS = (
    "SCHEMA.md",
    "AGENTS.md",
    ".git",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
)
DOC_DIR_PREFIXES = ("wiki/", "docs/", "reports/")
GENERATED_DIR_PREFIXES = (
    ".git/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".venv/",
    "__pycache__/",
    "build/",
    "data/",
    "dist/",
    "node_modules/",
    "probes/results/",
    "scratch/",
)
DOC_SUFFIXES = {".md", ".rst", ".txt", ".bib"}
CONFIG_SUFFIXES = {".json", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".lock"}
CODE_SUFFIXES = {
    ".bash",
    ".c",
    ".cc",
    ".cjs",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".jl",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".lua",
    ".mjs",
    ".php",
    ".py",
    ".r",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".sql",
    ".swift",
    ".svelte",
    ".ts",
    ".tsx",
    ".vue",
    ".zsh",
}
CODE_FILENAMES = {"Dockerfile", "Makefile", "Rakefile", "Justfile"}
ERROR_LOG = Path("/tmp/codex-hook-errors.log")
STATE_DIR = Path.home() / ".codex" / "tmp" / "hooks"
UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
SESSION_ID_KEYS = (
    "session_id",
    "sessionId",
    "thread_id",
    "threadId",
    "conversation_id",
    "conversationId",
)
PARENT_ID_KEYS = ("parent_thread_id", "parentThreadId")
TURN_ID_KEYS = (
    "turn_id",
    "turnId",
    "user_message_id",
    "userMessageId",
    "prompt_id",
    "promptId",
    "conversation_turn_id",
    "conversationTurnId",
    "message_id",
    "messageId",
)
PATH_ID_KEYS = (
    "transcript_path",
    "transcriptPath",
    "session_path",
    "sessionPath",
    "log_path",
    "logPath",
)
NESTED_ID_CONTAINERS = (
    "hook_input",
    "session",
    "thread",
    "conversation",
    "payload",
    "metadata",
    "context",
)
ENV_SESSION_ID_KEYS = (
    "CODEX_SESSION_ID",
    "CODEX_THREAD_ID",
    "OPENAI_CODEX_SESSION_ID",
    "OPENAI_CODEX_THREAD_ID",
)


@dataclass
class ChangeSummary:
    net_lines: int = 0
    touched_files: list[str] = field(default_factory=list)
    new_files: list[str] = field(default_factory=list)

    def extend(self, other: "ChangeSummary") -> None:
        self.net_lines += other.net_lines
        for path in other.touched_files:
            add_unique(self.touched_files, path)
        for path in other.new_files:
            add_unique(self.new_files, path)


def add_unique(items: list[str], item: str) -> None:
    if item and item not in items:
        items.append(item)


def parse_policy_scalar(raw: str) -> Any:
    value = raw.strip()
    if not value:
        return ""
    if value[0:1] in {"'", '"'} and value[-1:] == value[0]:
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        return value


def strip_yaml_comment(line: str) -> str:
    quote: str | None = None
    for index, char in enumerate(line):
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
        elif char == "#" and quote is None:
            return line[:index]
    return line


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small policy YAML subset used by harness_policy.yaml."""
    result: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = strip_yaml_comment(raw_line).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            key, sep, value = stripped.partition(":")
            if not sep:
                continue
            current_key = key.strip()
            if value.strip():
                result[current_key] = parse_policy_scalar(value)
            else:
                result[current_key] = {}
            continue

        if current_key is None:
            continue
        container = result.setdefault(current_key, {})
        if stripped.startswith("- "):
            if not isinstance(container, list):
                container = []
                result[current_key] = container
            container.append(parse_policy_scalar(stripped[2:]))
            continue

        key, sep, value = stripped.partition(":")
        if sep and isinstance(container, dict):
            container[key.strip()] = parse_policy_scalar(value)
    return result


def merge_policy(default: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key, value in default.items():
        if isinstance(value, dict):
            merged[key] = dict(value)
        elif isinstance(value, list):
            merged[key] = list(value)
        else:
            merged[key] = value
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        elif isinstance(value, list):
            merged[key] = list(value)
        else:
            merged[key] = value
    return merged


def load_harness_policy(root: Path | None) -> dict[str, Any]:
    if root is None:
        return merge_policy(DEFAULT_POLICY, {})
    path = root / "harness_policy.yaml"
    try:
        parsed = parse_simple_yaml(path.read_text(errors="replace"))
    except OSError:
        return merge_policy(DEFAULT_POLICY, {})
    return merge_policy(DEFAULT_POLICY, parsed)


def threshold(policy: dict[str, Any], name: str) -> int:
    value = policy.get("thresholds", {}).get(name, DEFAULT_POLICY["thresholds"][name])
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(DEFAULT_POLICY["thresholds"][name])


def enforcement_mode(policy: dict[str, Any], name: str) -> str:
    mode = str(policy.get("enforcement", {}).get(name) or policy.get("enforcement", {}).get("default") or "remind")
    return mode if mode in {"observe", "remind", "block"} else "remind"


def path_matches_any(rel: str, patterns: Iterable[str]) -> str | None:
    normalized = rel.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    for pattern in patterns:
        pat = str(pattern).replace("\\", "/")
        if pat.startswith("./"):
            pat = pat[2:]
        candidates = [pat]
        if pat.startswith("**/"):
            candidates.append(pat[3:])
        for candidate in candidates:
            if fnmatchcase(normalized, candidate):
                return pat
    return None


def risk_flags_for_paths(paths: Iterable[str], policy: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    risky_paths = policy.get("risky_paths", [])
    harness_paths = policy.get("harness_self_paths", [])
    for rel in paths:
        harness_match = path_matches_any(rel, harness_paths)
        if harness_match:
            add_unique(flags, f"harness_self:{harness_match}")
        risky_match = path_matches_any(rel, risky_paths)
        if risky_match:
            add_unique(flags, f"risky_path:{risky_match}")
    return flags


def is_risky_path(rel: str, policy: dict[str, Any]) -> bool:
    return bool(risk_flags_for_paths([rel], policy))


def load_event() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def safe_id(value: Any) -> str:
    raw = os.path.basename(str(value).strip())
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw)
    if len(safe) <= 140:
        return safe or "unknown"
    digest = sha1(safe.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"{safe[:120]}-{digest}"


def short_hash(value: Any) -> str:
    return sha1(str(value).encode("utf-8", errors="replace")).hexdigest()[:12]


def nested_values(data: dict[str, Any], keys: tuple[str, ...], *, include_plain_id: bool = False) -> Iterable[Any]:
    stack: list[tuple[dict[str, Any], bool]] = [(data, False)]
    seen: set[int] = set()
    while stack:
        current, allow_plain_id = stack.pop()
        obj_id = id(current)
        if obj_id in seen:
            continue
        seen.add(obj_id)

        search_keys = keys + (("id",) if include_plain_id and allow_plain_id else ())
        for key in search_keys:
            value = current.get(key)
            if value:
                yield value

        for key in NESTED_ID_CONTAINERS:
            nested = current.get(key)
            if isinstance(nested, dict):
                stack.append((nested, key in {"session", "thread", "conversation"}))


def id_from_path_value(value: Any) -> str | None:
    match = UUID_RE.search(str(value))
    return safe_id(match.group(0)) if match else None


def looks_like_codex_process(argv: list[str]) -> bool:
    if not argv:
        return False
    exe = Path(argv[0]).name.lower()
    if exe == "codex" or exe.startswith("codex-"):
        return True
    if exe not in {"node", "bun", "deno"}:
        return False
    for arg in argv[1:6]:
        name = Path(arg).name.lower()
        if name == "codex" or name.startswith("codex-") or "codex-cli" in name:
            return True
    return False


def codex_process_scope() -> str | None:
    pid = os.getppid()
    for _ in range(8):
        if pid <= 1:
            break
        proc = Path("/proc") / str(pid)
        try:
            cmd_parts = [
                part.decode(errors="replace")
                for part in (proc / "cmdline").read_bytes().split(b"\x00")
                if part
            ]
            stat_parts = (proc / "stat").read_text(errors="replace").split()
        except OSError:
            break

        start_time = stat_parts[21] if len(stat_parts) > 21 else "0"
        if looks_like_codex_process(cmd_parts):
            return safe_id(f"pid{pid}-{start_time}")

        try:
            pid = int(stat_parts[3])
        except (IndexError, ValueError):
            break

    for key in ("WT_SESSION", "TMUX", "STY", "SSH_TTY", "TERM_SESSION_ID"):
        value = os.environ.get(key)
        if value:
            return safe_id(f"{key.lower()}-{short_hash(value)}")
    return None


def session_id(data: dict[str, Any]) -> str:
    for value in nested_values(data, SESSION_ID_KEYS, include_plain_id=True):
        base = safe_id(value)
        if base != "unknown":
            break
    else:
        base = ""

    if not base:
        for key in ENV_SESSION_ID_KEYS:
            value = os.environ.get(key)
            if value:
                base = safe_id(value)
                break

    if not base:
        for value in nested_values(data, PATH_ID_KEYS):
            parsed = id_from_path_value(value)
            if parsed:
                base = parsed
                break

    if not base:
        for value in nested_values(data, PARENT_ID_KEYS):
            parent = safe_id(value)
            if parent != "unknown":
                base = f"parent-{parent}"
                break

    if not base:
        base = f"unknown-cwd-{short_hash(cwd_from(data))}"

    process_scope = codex_process_scope()
    if process_scope:
        base = f"{base}.{process_scope}"
    elif base.startswith("unknown-cwd-"):
        # No reliable session/thread/process identity: keep the hook fail-open
        # rather than sharing state between concurrent terminals in one cwd.
        base = f"{base}.hookpid{os.getpid()}"
    return safe_id(base)


def state_dir() -> Path:
    try:
        STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        return STATE_DIR
    except OSError:
        return Path("/tmp")


def session_trace_dir(data: dict[str, Any]) -> Path:
    path = state_dir() / session_id(data)
    try:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        return path
    except OSError:
        return Path("/tmp")


def append_trace(data: dict[str, Any], event: str, payload: dict[str, Any]) -> None:
    record = {
        "event": event,
        "time": datetime.now().isoformat(timespec="seconds"),
        **payload,
    }
    path = session_trace_dir(data) / "trace.jsonl"
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def write_loop_state(data: dict[str, Any], payload: dict[str, Any]) -> None:
    path = session_trace_dir(data) / "state.json"
    current = load_state(path)
    current.update(payload)
    current["updated"] = datetime.now().isoformat(timespec="seconds")
    save_state(path, current)


def meta_path(data: dict[str, Any]) -> Path:
    return state_dir() / f"codex-hook-meta-{session_id(data)}.json"


def explicit_turn_id(data: dict[str, Any]) -> str | None:
    for value in nested_values(data, TURN_ID_KEYS):
        turn = safe_id(value)
        if turn != "unknown":
            return turn
    return None


def current_turn_id(data: dict[str, Any]) -> str:
    explicit = explicit_turn_id(data)
    if explicit:
        return explicit
    meta = load_state(meta_path(data))
    return safe_id(meta.get("active_turn") or "unknown")


def begin_turn(data: dict[str, Any]) -> str:
    path = meta_path(data)
    with state_file_lock(path):
        meta = load_state(path)
        explicit = explicit_turn_id(data)
        if explicit:
            meta["active_turn"] = explicit
        else:
            meta["turn_counter"] = int(meta.get("turn_counter", 0)) + 1
            meta["active_turn"] = str(meta["turn_counter"])
        save_state(path, meta)
        return safe_id(meta["active_turn"])


def event_id(data: dict[str, Any], prefix: str) -> Path:
    return state_dir() / f"{prefix}-{session_id(data)}-{current_turn_id(data)}.json"


def load_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


@contextmanager
def state_file_lock(path: Path) -> Iterable[None]:
    lock_file = path.with_suffix(path.suffix + ".lock")
    handle = None
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        handle = lock_file.open("a")
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        yield
    finally:
        if handle is not None:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (ImportError, OSError):
                pass
            try:
                handle.close()
            except OSError:
                pass


def save_state(path: Path, state: dict[str, Any]) -> None:
    tmp: Path | None = None
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False))
        os.replace(tmp, path)
    except OSError:
        if tmp is not None:
            try:
                tmp.unlink()
            except OSError:
                pass
        pass


def cwd_from(data: dict[str, Any]) -> Path:
    cwd = data.get("cwd") or data.get("working_directory") or os.getcwd()
    return Path(str(cwd)).expanduser().resolve()


def parent_chain(path: Path) -> Iterable[Path]:
    current = path
    while True:
        yield current
        if current.parent == current:
            return
        current = current.parent


def find_project_root(cwd: Path) -> Path | None:
    for current in parent_chain(cwd):
        if any((current / marker).exists() for marker in PROJECT_MARKERS):
            return current
    return None


def find_schema_root(cwd: Path) -> Path | None:
    for current in parent_chain(cwd):
        if (current / "SCHEMA.md").is_file():
            return current
    return None


def path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def rel_for_display(cwd: Path, raw_path: str) -> str:
    path = resolve_path(cwd, raw_path)
    try:
        return path.resolve().relative_to(cwd.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def resolve_path(cwd: Path, raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = cwd / path
    return path


def tool_name(data: dict[str, Any]) -> str:
    return str(
        data.get("tool_name")
        or data.get("tool")
        or data.get("name")
        or data.get("hook_input", {}).get("tool_name")
        or data.get("tool_call", {}).get("tool_name")
        or data.get("tool_call", {}).get("name")
        or data.get("tool_result", {}).get("tool_name")
        or data.get("tool_result", {}).get("name")
        or ""
    )


def short_tool_name(name: str) -> str:
    return name.rsplit(".", 1)[-1]


def tool_input(data: dict[str, Any]) -> dict[str, Any]:
    value = (
        data.get("tool_input")
        or data.get("arguments")
        or data.get("input")
        or data.get("hook_input", {}).get("tool_input")
        or data.get("tool_call", {}).get("arguments")
        or data.get("tool_call", {}).get("input")
        or data.get("tool_result", {}).get("arguments")
        or data.get("tool_result", {}).get("input")
        or {}
    )
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {"cmd": value}
        return decoded if isinstance(decoded, dict) else {}
    return value if isinstance(value, dict) else {}


def iter_tool_calls(name: str, args: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    yield name, args
    if short_tool_name(name) != "parallel":
        return
    for item in args.get("tool_uses", []):
        if not isinstance(item, dict):
            continue
        nested_name = str(item.get("recipient_name") or item.get("name") or "")
        nested_args = item.get("parameters") or item.get("arguments") or {}
        if isinstance(nested_args, dict):
            yield nested_name, nested_args


def prompt_text(data: dict[str, Any]) -> str:
    prompt = data.get("prompt") or data.get("last_user_message") or ""
    if isinstance(prompt, str):
        return prompt
    return json.dumps(prompt, ensure_ascii=False)


def emit_additional_context(event: str, messages: list[str]) -> None:
    if not messages:
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": "\n".join(messages),
                }
            },
            ensure_ascii=False,
        )
    )


def count_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def is_doc_or_config_path(rel: str) -> bool:
    suffix = Path(rel).suffix.lower()
    return rel.startswith(DOC_DIR_PREFIXES) or suffix in DOC_SUFFIXES or suffix in CONFIG_SUFFIXES


def should_track_gan_path(cwd: Path, raw_path: str) -> bool:
    if not raw_path:
        return False
    path = resolve_path(cwd, raw_path)
    rel = rel_for_display(cwd, raw_path).replace("\\", "/").lstrip("./")
    policy = load_harness_policy(cwd)
    if path_matches_any(rel, policy.get("generated_paths", [])) or rel.startswith(GENERATED_DIR_PREFIXES):
        return False
    if is_risky_path(rel, policy):
        return True

    home_codex = Path.home() / ".codex"
    if path_is_relative_to(path, home_codex) and not path_is_relative_to(path, home_codex / "hooks"):
        return False

    if is_doc_or_config_path(rel):
        return False
    suffix = Path(rel).suffix.lower()
    return suffix in CODE_SUFFIXES or Path(rel).name in CODE_FILENAMES


def should_track_wiki_code_path(root: Path, raw_path: str) -> bool:
    path = resolve_path(root, raw_path)
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return False
    return not rel.startswith(("wiki/",)) and should_track_gan_path(root, rel)


def should_track_wiki_path(root: Path, raw_path: str) -> bool:
    path = resolve_path(root, raw_path)
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return False
    if rel in {"wiki/index.md", "wiki/log.md"}:
        return True
    if rel.startswith("wiki/") and Path(rel).suffix.lower() in DOC_SUFFIXES:
        return True
    return should_track_wiki_code_path(root, rel)


def git_candidate_paths(root: Path) -> list[str] | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def walk_candidate_paths(root: Path) -> list[str]:
    paths: list[str] = []
    try:
        iterator = root.rglob("*")
        for path in iterator:
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in GENERATED_DIR_PREFIXES):
                continue
            if path.is_file():
                paths.append(rel)
    except OSError:
        return paths
    return paths


def file_fingerprint(path: Path) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError:
        return {"exists": False, "lines": 0, "hash": ""}
    return {
        "exists": True,
        "lines": data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1),
        "hash": sha1(data).hexdigest(),
    }


def artifact_snapshot(root: Path, pattern: str) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    try:
        paths = sorted(root.glob(pattern))
    except OSError:
        return snapshot
    for path in paths:
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        snapshot[rel] = file_fingerprint(path)
    return snapshot


def candidate_artifacts(root: Path, pattern: str, before: Any, *, changed_only: bool) -> list[Path]:
    before_map = before if isinstance(before, dict) else {}
    after = artifact_snapshot(root, pattern)
    changed: list[Path] = []
    for rel, fingerprint in after.items():
        if before_map.get(rel) != fingerprint:
            changed.append(root / rel)
    if changed_only and before_map:
        return changed
    return changed or [root / rel for rel in sorted(after)]


def normalize_heading(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def markdown_sections(text: str) -> set[str]:
    sections: set[str] = set()
    for line in text.splitlines():
        match = re.match(r"^#{1,3}\s+(.+?)\s*$", line)
        if match:
            sections.add(normalize_heading(match.group(1)))
    return sections


def artifact_has_sections(path: Path, required: Iterable[str]) -> bool:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return False
    sections = markdown_sections(text)
    return all(normalize_heading(item) in sections for item in required)


def valid_contract_artifacts(root: Path, before: Any) -> list[str]:
    valid: list[str] = []
    for path in candidate_artifacts(root, "wiki/contracts/*.md", before, changed_only=False):
        if artifact_has_sections(path, REQUIRED_CONTRACT_SECTIONS):
            try:
                valid.append(path.relative_to(root).as_posix())
            except ValueError:
                valid.append(path.as_posix())
    return valid


def review_verdict(path: Path) -> str | None:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return None
    match = re.search(r"(?im)^##\s+Verdict\s*\n+\s*(PASS|FAIL|NEEDS_HUMAN)\b", text)
    if not match:
        match = re.search(r"(?im)^Verdict\s*:\s*(PASS|FAIL|NEEDS_HUMAN)\b", text)
    if not match:
        return None
    verdict = match.group(1).upper()
    return verdict if verdict in VALID_REVIEW_VERDICTS else None


def review_artifact_status(root: Path, before: Any) -> dict[str, Any]:
    statuses: list[dict[str, Any]] = []
    for path in candidate_artifacts(root, "wiki/reviews/*-review.md", before, changed_only=True):
        sections_ok = artifact_has_sections(path, REQUIRED_REVIEW_SECTIONS)
        verdict = review_verdict(path)
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.as_posix()
        statuses.append({"path": rel, "verdict": verdict or "MISSING", "sections_ok": sections_ok})
    passing = [item["path"] for item in statuses if item["verdict"] == "PASS" and item["sections_ok"]]
    failing = [item for item in statuses if item["verdict"] in {"FAIL", "NEEDS_HUMAN"}]
    return {"passing": passing, "failing": failing, "all": statuses}


def build_snapshot(root: Path, path_filter: Callable[[Path, str], bool]) -> dict[str, dict[str, Any]]:
    if not root.exists():
        return {}
    candidates = git_candidate_paths(root)
    if candidates is None:
        candidates = walk_candidate_paths(root)

    snapshot: dict[str, dict[str, Any]] = {}
    for rel in sorted(set(candidates)):
        if not path_filter(root, rel):
            continue
        snapshot[rel] = file_fingerprint(root / rel)
    return snapshot


def snapshot_delta(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    *,
    new_file_min_lines: int,
) -> ChangeSummary:
    summary = ChangeSummary()
    for rel in sorted(set(before) | set(after)):
        old = before.get(rel, {"exists": False, "lines": 0, "hash": ""})
        new = after.get(rel, {"exists": False, "lines": 0, "hash": ""})
        if old == new:
            continue
        add_unique(summary.touched_files, rel)
        old_lines = int(old.get("lines") or 0) if old.get("exists") else 0
        new_lines = int(new.get("lines") or 0) if new.get("exists") else 0
        summary.net_lines += max(0, new_lines - old_lines)
        if not old.get("exists") and new.get("exists") and new_lines >= new_file_min_lines:
            add_unique(summary.new_files, rel)
    return summary


def parse_apply_patch(
    cwd: Path,
    patch: str,
    *,
    path_filter: Callable[[Path, str], bool] | None = None,
    new_file_min_lines: int = 0,
) -> ChangeSummary:
    summary = ChangeSummary()
    current: str | None = None
    current_is_new = False
    current_added = 0
    current_removed = 0

    def included(path: str | None) -> bool:
        return bool(path) and (path_filter is None or path_filter(cwd, path))

    def finish_current() -> None:
        nonlocal current, current_is_new, current_added, current_removed
        if included(current) and current:
            net = max(0, current_added - current_removed)
            summary.net_lines += net
            if current_is_new and current_added >= new_file_min_lines:
                add_unique(summary.new_files, current)
        current = None
        current_is_new = False
        current_added = 0
        current_removed = 0

    for line in patch.splitlines():
        if line.startswith("*** Add File: "):
            finish_current()
            current = line.removeprefix("*** Add File: ").strip()
            current_is_new = True
            if included(current) and current:
                add_unique(summary.touched_files, current)
            continue
        if line.startswith("*** Update File: "):
            finish_current()
            current = line.removeprefix("*** Update File: ").strip()
            current_is_new = False
            if included(current) and current:
                add_unique(summary.touched_files, current)
            continue
        if line.startswith("*** Delete File: "):
            finish_current()
            current = line.removeprefix("*** Delete File: ").strip()
            current_is_new = False
            if included(current) and current:
                add_unique(summary.touched_files, current)
            continue
        if not included(current):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            current_added += 1
        elif line.startswith("-") and not line.startswith("---"):
            current_removed += 1
    finish_current()
    return summary


def summarize_tool_change(
    cwd: Path,
    name: str,
    args: dict[str, Any],
    path_filter: Callable[[Path, str], bool] | None,
) -> ChangeSummary:
    short = short_tool_name(name)
    summary = ChangeSummary()

    if short == "Write":
        file_path = args.get("file_path") or args.get("path")
        content = args.get("content", "")
        if isinstance(file_path, str) and (path_filter is None or path_filter(cwd, file_path)):
            add_unique(summary.touched_files, file_path)
            if isinstance(content, str):
                n_lines = count_lines(content)
                summary.net_lines += n_lines
                if n_lines >= GAN_NEW_FILE_LINE_THRESHOLD:
                    add_unique(summary.new_files, file_path)
        return summary

    if short == "Edit":
        file_path = args.get("file_path") or args.get("path")
        old = args.get("old_string", "")
        new = args.get("new_string", "")
        if isinstance(file_path, str) and (path_filter is None or path_filter(cwd, file_path)):
            add_unique(summary.touched_files, file_path)
            if isinstance(old, str) and isinstance(new, str):
                summary.net_lines += max(0, count_lines(new) - count_lines(old))
        return summary

    patch = args.get("patch") or args.get("input") or args.get("cmd") or ""
    if short in {"apply_patch", "Edit|Write"} or "patch" in args:
        if isinstance(patch, str):
            return parse_apply_patch(
                cwd,
                patch,
                path_filter=path_filter,
                new_file_min_lines=GAN_NEW_FILE_LINE_THRESHOLD,
            )
    if short in {"exec_command", "Bash"} and isinstance(patch, str) and "*** Begin Patch" in patch:
        return parse_apply_patch(
            cwd,
            patch,
            path_filter=path_filter,
            new_file_min_lines=GAN_NEW_FILE_LINE_THRESHOLD,
        )
    return summary


def collect_changed_paths(cwd: Path, calls: list[tuple[str, dict[str, Any]]]) -> list[str]:
    changed: list[str] = []
    for name, args in calls:
        summary = summarize_tool_change(cwd, name, args, path_filter=None)
        for path in summary.touched_files:
            add_unique(changed, path)
    return changed


def init_gan_state(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("prompt_signal", False)
    state.setdefault("plan_injected", False)
    state.setdefault("total_net_lines", 0)
    state.setdefault("touched_files", [])
    state.setdefault("new_files", [])
    state.setdefault("risk_flags", [])
    state.setdefault("triggered", False)
    state.setdefault("review_required", False)
    state.setdefault("large_change", False)
    state.setdefault("risky_change", False)
    state.setdefault("nudge_printed", False)
    state.setdefault("reviewer_called", False)
    state.setdefault("discriminator_called", False)
    state.setdefault("validation_seen", False)
    state.setdefault("validation_commands", [])
    state.setdefault("contract_files", [])
    state.setdefault("review_files", [])
    state.setdefault("team_created", False)
    state.setdefault("stop_blocks", 0)
    state.setdefault("lines_since_last_review", 0)
    state.setdefault("new_files_since_last_review", [])
    state.setdefault("incremental_nudge_printed", False)
    return state


def gan_state(data: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = event_id(data, "gan-hook")
    state = init_gan_state(load_state(path))
    return path, state


@contextmanager
def locked_gan_state(data: dict[str, Any]) -> Iterable[tuple[Path, dict[str, Any]]]:
    path = event_id(data, "gan-hook")
    with state_file_lock(path):
        state = init_gan_state(load_state(path))
        yield path, state
        save_state(path, state)


def init_wiki_state(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("plan_injected", False)
    state.setdefault("code_files", [])
    state.setdefault("wiki_files", [])
    state.setdefault("wiki_pages", [])
    state.setdefault("wiki_index", False)
    state.setdefault("wiki_log", False)
    state.setdefault("wiki_agent_called", False)
    state.setdefault("stop_blocks", 0)
    return state


def wiki_state(data: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = event_id(data, "wiki-hook")
    state = init_wiki_state(load_state(path))
    return path, state


@contextmanager
def locked_wiki_state(data: dict[str, Any]) -> Iterable[tuple[Path, dict[str, Any]]]:
    path = event_id(data, "wiki-hook")
    with state_file_lock(path):
        state = init_wiki_state(load_state(path))
        yield path, state
        save_state(path, state)


def hook_user_prompt(data: dict[str, Any]) -> int:
    begin_turn(data)
    cwd = cwd_from(data)
    prompt = prompt_text(data)
    project_root = find_project_root(cwd)
    schema_root = find_schema_root(cwd)
    policy_root = project_root or schema_root or cwd
    policy = load_harness_policy(policy_root)
    messages: list[str] = []
    classification = "nontrivial_code_task" if project_root and prompt and IMPLEMENT_RE.search(prompt) else "ordinary"

    if schema_root:
        messages.append(
            "Wiki: SCHEMA.md detected. Before codebase work, read wiki/index.md, "
            "then relevant wiki pages; delegate required ingest to a focused wiki-ingest "
            "subagent and fall back to source only when wiki is insufficient."
        )

    if project_root and prompt and IMPLEMENT_RE.search(prompt):
        with locked_gan_state(data) as (_, state):
            state["prompt_signal"] = True
            state["project_root"] = str(project_root)
            state["last_snapshot"] = build_snapshot(project_root, should_track_gan_path)
            state["contract_snapshot"] = artifact_snapshot(project_root, "wiki/contracts/*.md")
            state["review_snapshot"] = artifact_snapshot(project_root, "wiki/reviews/*-review.md")
            if not state.get("plan_injected"):
                state["plan_injected"] = True
                messages.append(
                    "GAN hard gate: if this becomes nontrivial implementation, the hook will "
                    f"count real code edits and Stop will require contract/review/validation after >="
                    f"{threshold(policy, 'review_net_new_lines')} net new code lines, risky paths, "
                    f"or >=1 new code file ({threshold(policy, 'new_file_min_lines')} lines). "
                    "Planning is not a review; use Codex spawn_agent/send_input with review/审查 "
                    "and write a wiki/reviews/*-review.md artifact when the gate trips."
                )

        if schema_root:
            with locked_wiki_state(data) as (_, wiki):
                wiki["plan_injected"] = True
                wiki["schema_root"] = str(schema_root)
                wiki["last_snapshot"] = build_snapshot(schema_root, should_track_wiki_path)
    else:
        if project_root:
            with locked_gan_state(data) as (_, state):
                state["project_root"] = str(project_root)
                state["last_snapshot"] = build_snapshot(project_root, should_track_gan_path)
                state["contract_snapshot"] = artifact_snapshot(project_root, "wiki/contracts/*.md")
                state["review_snapshot"] = artifact_snapshot(project_root, "wiki/reviews/*-review.md")
        if schema_root:
            with locked_wiki_state(data) as (_, wiki):
                wiki["schema_root"] = str(schema_root)
                wiki["last_snapshot"] = build_snapshot(schema_root, should_track_wiki_path)

    append_trace(
        data,
        "UserPromptSubmit",
        {
            "classification": classification,
            "project_root": str(project_root) if project_root else "",
            "schema_root": str(schema_root) if schema_root else "",
        },
    )
    emit_additional_context("UserPromptSubmit", messages)
    return 0


def hook_session_start(data: dict[str, Any]) -> int:
    cwd = cwd_from(data)
    project_root = find_project_root(cwd)
    schema_root = find_schema_root(cwd)
    messages: list[str] = []
    source = str(data.get("source") or data.get("start_source") or "")

    if schema_root:
        messages.append(
            "Wiki: SCHEMA.md detected. Query wiki/index.md and relevant wiki pages "
            "before source when doing codebase work; delegate any required ingest to a "
            "focused wiki-ingest subagent."
        )
    if project_root:
        messages.append(
            "Codex Loop Harness: large or risky code edits require a contract, validation "
            "evidence, and a PASS review artifact before Stop; first missing objective "
            "requirement can hard-block."
        )
    append_trace(
        data,
        "SessionStart",
        {
            "source": source,
            "project_root": str(project_root) if project_root else "",
            "schema_root": str(schema_root) if schema_root else "",
            "messages": messages,
        },
    )

    if source == "compact":
        if schema_root:
            messages.append(
                "Wiki: Context compacted in a SCHEMA.md project. Re-read SCHEMA.md "
                "and wiki/index.md before continuing wiki-sensitive work."
            )
        if project_root:
            messages.append(
                "Codex Loop Harness: context compacted. Keep contract/review/validation "
                "requirements active for large or risky edits."
            )
        emit_additional_context("SessionStart", messages)
        return 0

    if not schema_root:
        emit_additional_context("SessionStart", messages)
        return 0

    log_file = schema_root / "wiki" / "log.md"
    if not log_file.is_file():
        messages.append("Wiki: wiki/log.md not found. Consider a wiki health check.")
        emit_additional_context("SessionStart", messages)
        return 0

    content = log_file.read_text(errors="replace")
    dates = re.findall(r"## \[(\d{4}-\d{2}-\d{2})[^\]]*\] lint", content)
    if not dates:
        messages.append("Wiki: No lint records found in wiki/log.md. Consider a wiki health check.")
        emit_additional_context("SessionStart", messages)
        return 0

    last = max(datetime.strptime(d, "%Y-%m-%d") for d in dates)
    days = (datetime.now() - last).days
    if days > 7:
        messages.append(
            f"Wiki: Last wiki lint was {days} days ago "
            f"({last.strftime('%Y-%m-%d')}). Consider a wiki health check."
        )
    emit_additional_context("SessionStart", messages)
    return 0


def mark_reviewer_if_needed(state: dict[str, Any], name: str, args: dict[str, Any]) -> bool:
    short = short_tool_name(name)
    haystack = f"{name} {json.dumps(args, ensure_ascii=False)}"

    if short in {"TeamCreate", "team_create"}:
        state["team_created"] = True
        state["reviewer_called"] = True
        state["discriminator_called"] = True
        return True

    reviewer_tool = short in {
        "Agent",
        "SendMessage",
        "Task",
        "send_input",
        "spawn_agent",
        "request_copilot_review",
    }
    if reviewer_tool and REVIEW_RE.search(haystack):
        state["reviewer_called"] = True
        state["discriminator_called"] = True
        state["lines_since_last_review"] = 0
        state["new_files_since_last_review"] = []
        state["incremental_nudge_printed"] = False
        return True
    return False


def mark_validation_if_needed(state: dict[str, Any], name: str, args: dict[str, Any], policy: dict[str, Any]) -> bool:
    short = short_tool_name(name)
    if short not in {"exec_command", "Bash"}:
        return False
    cmd = str(args.get("cmd") or args.get("command") or "")
    if not cmd:
        return False
    haystack = cmd.lower()
    for marker in policy.get("validation_commands", []):
        if str(marker).lower() in haystack:
            state["validation_seen"] = True
            add_unique(state["validation_commands"], cmd[:240])
            return True
    return False


def mark_wiki_agent_if_needed(state: dict[str, Any], name: str, args: dict[str, Any]) -> bool:
    short = short_tool_name(name)
    wiki_agent_tool = short in {
        "Agent",
        "SendMessage",
        "Task",
        "send_input",
        "spawn_agent",
        "TeamCreate",
        "team_create",
    }
    if not wiki_agent_tool:
        return False

    haystack = f"{name} {json.dumps(args, ensure_ascii=False)}"
    if WIKI_INGEST_RE.search(haystack):
        state["wiki_agent_called"] = True
        return True
    return False


def track_gan_changes(data: dict[str, Any], calls: list[tuple[str, dict[str, Any]]], cwd: Path) -> tuple[list[str], list[str]]:
    with locked_gan_state(data) as (_, state):
        reviewer_seen = False
        project_root = Path(str(state.get("project_root"))) if state.get("project_root") else find_project_root(cwd)
        policy = load_harness_policy(project_root or cwd)

        for name, args in calls:
            if mark_reviewer_if_needed(state, name, args):
                reviewer_seen = True
            mark_validation_if_needed(state, name, args, policy)

        change = ChangeSummary()
        changed_abs: list[str] = []
        if project_root:
            before = state.get("last_snapshot")
            after = build_snapshot(project_root, should_track_gan_path)
            if isinstance(before, dict):
                change = snapshot_delta(
                    before,
                    after,
                    new_file_min_lines=threshold(policy, "new_file_min_lines"),
                )
                changed_abs = [str(project_root / rel) for rel in change.touched_files]
            state["project_root"] = str(project_root)
            state["last_snapshot"] = after

        was_nudge_printed_before = bool(state.get("nudge_printed"))

        if change.net_lines > 0:
            state["total_net_lines"] += change.net_lines
            state["lines_since_last_review"] += change.net_lines
        for path in change.touched_files:
            add_unique(state["touched_files"], rel_for_display(cwd, path))
        for path in change.new_files:
            display = rel_for_display(cwd, path)
            add_unique(state["new_files"], display)
            add_unique(state["new_files_since_last_review"], display)

        for flag in risk_flags_for_paths(change.touched_files, policy):
            add_unique(state["risk_flags"], flag)

        state["risky_change"] = bool(state["risk_flags"])
        state["large_change"] = (
            state["total_net_lines"] >= threshold(policy, "large_change_lines")
            or len(state["new_files"]) >= threshold(policy, "large_change_new_files")
        )
        state["review_required"] = (
            state["total_net_lines"] >= threshold(policy, "review_net_new_lines")
            or bool(state["new_files"])
            or state["risky_change"]
        )

        if state["review_required"]:
            state["triggered"] = True

        messages: list[str] = []
        if state["triggered"] and not was_nudge_printed_before and not state.get("reviewer_called"):
            state["nudge_printed"] = True
            if state.get("plan_injected"):
                messages.append(
                    f"GAN: review gate tripped ({state['total_net_lines']} net new code lines, "
                    f"{len(state['new_files'])} new code file(s)). Spawn/send a reviewer before Stop."
                )
            else:
                messages.append(
                    f"GAN: Threshold reached ({state['total_net_lines']} net new code lines, "
                    f"{len(state['new_files'])} new code file(s)). Use Codex spawn_agent/send_input "
                    "with review/审查 and iterate until PASS before ending."
                )
        elif (
            was_nudge_printed_before
            and not reviewer_seen
            and not state.get("incremental_nudge_printed")
            and (
                state["lines_since_last_review"] >= threshold(policy, "incremental_reminder_lines")
                or len(state["new_files_since_last_review"]) >= threshold(policy, "incremental_new_files")
            )
        ):
            state["incremental_nudge_printed"] = True
            messages.append(
                f"GAN incremental: {state['lines_since_last_review']} net new code lines and "
                f"{len(state['new_files_since_last_review'])} new files since last review. "
                "Ask the current reviewer to review this checkpoint."
            )

        append_trace(
            data,
            "PostToolUse",
            {
                "gate": "diff_telemetry",
                "changed_files": change.touched_files,
                "delta_lines": change.net_lines,
                "new_files": change.new_files,
                "risk_flags": state["risk_flags"],
                "review_required": state["review_required"],
                "large_change": state["large_change"],
                "validation_seen": state["validation_seen"],
            },
        )
        return messages, changed_abs


def track_wiki_edits(data: dict[str, Any], calls: list[tuple[str, dict[str, Any]]], cwd: Path) -> list[str]:
    schema_root = find_schema_root(cwd)
    if not schema_root:
        return []

    with locked_wiki_state(data) as (_, state):
        for name, args in calls:
            mark_wiki_agent_if_needed(state, name, args)

        root_raw = state.get("schema_root")
        root = Path(str(root_raw)) if root_raw else schema_root
        before = state.get("last_snapshot")
        after = build_snapshot(root, should_track_wiki_path)
        changed_abs: list[str] = []
        if isinstance(before, dict):
            summary = snapshot_delta(before, after, new_file_min_lines=0)
            changed_abs = [str(root / rel) for rel in summary.touched_files]
            for rel in summary.touched_files:
                if rel == "wiki/index.md":
                    add_unique(state["wiki_files"], rel)
                    state["wiki_index"] = True
                elif rel == "wiki/log.md":
                    add_unique(state["wiki_files"], rel)
                    state["wiki_log"] = True
                elif rel.startswith("wiki/"):
                    add_unique(state["wiki_files"], rel)
                    add_unique(state["wiki_pages"], rel)
                elif should_track_wiki_code_path(root, rel):
                    add_unique(state["code_files"], rel)
        state["schema_root"] = str(root)
        state["last_snapshot"] = after
        return changed_abs


def compile_python(path: Path) -> str | None:
    cfile = Path("/tmp") / f"codex-hook-pycompile-{os.getpid()}-{abs(hash(str(path)))}.pyc"
    try:
        py_compile.compile(str(path), cfile=str(cfile), doraise=True)
        return None
    except py_compile.PyCompileError as exc:
        return f"Validation failed: `{path}` does not py_compile: {exc.msg}"
    except OSError as exc:
        return f"Validation skipped: could not read `{path}`: {exc}"
    finally:
        try:
            cfile.unlink()
        except OSError:
            pass


def maybe_compile_changed_files(cwd: Path, changed_paths: list[str]) -> list[str]:
    messages: list[str] = []
    py_paths: list[Path] = []
    ts_seen = False

    for raw in changed_paths:
        path = resolve_path(cwd, raw)
        suffix = path.suffix.lower()
        if suffix == ".py" and path.is_file():
            py_paths.append(path)
        elif suffix in {".ts", ".tsx"}:
            ts_seen = True

    for path in py_paths:
        failure = compile_python(path)
        if failure:
            messages.append(failure)

    if ts_seen:
        tsc = cwd / "node_modules" / ".bin" / "tsc"
        cmd = [str(tsc), "--noEmit"] if tsc.exists() else None
        if cmd is None and shutil.which("tsc"):
            cmd = ["tsc", "--noEmit"]
        if cmd is None:
            messages.append("Validation skipped: TypeScript changed but no local/global `tsc` was found.")
        else:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(cwd),
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                    check=False,
                )
                if proc.returncode != 0:
                    output = (proc.stderr or proc.stdout).strip().splitlines()
                    snippet = "\n".join(output[:8])
                    messages.append(f"Validation failed: `{' '.join(cmd)}` exited {proc.returncode}:\n{snippet}")
            except (OSError, subprocess.TimeoutExpired) as exc:
                messages.append(f"Validation skipped: TypeScript check could not run: {exc}")
    return messages


def hook_post_tool(data: dict[str, Any]) -> int:
    cwd = cwd_from(data)
    calls = list(iter_tool_calls(tool_name(data), tool_input(data)))
    messages: list[str] = []

    changed_paths = track_wiki_edits(data, calls, cwd)
    gan_messages, gan_changed_paths = track_gan_changes(data, calls, cwd)
    changed_paths.extend(gan_changed_paths)
    messages.extend(gan_messages)
    validation_messages = maybe_compile_changed_files(cwd, changed_paths)
    messages.extend(validation_messages)
    if validation_messages:
        append_trace(
            data,
            "Validation",
            {
                "changed_paths": changed_paths,
                "messages": validation_messages,
            },
        )
    _, gan = gan_state(data)
    _, wiki = wiki_state(data)
    write_loop_state(
        data,
        {
            "repo": str(find_project_root(cwd) or cwd),
            "changed_files": gan.get("touched_files", []),
            "net_new_code_lines": gan.get("total_net_lines", 0),
            "new_files": len(gan.get("new_files", [])),
            "risk_flags": gan.get("risk_flags", []),
            "review_required": gan.get("review_required", False),
            "review_seen": gan.get("reviewer_called", False),
            "validation_seen": gan.get("validation_seen", False),
            "wiki_ingest_needed": bool(wiki.get("code_files")),
            "wiki_ingest_seen": bool(wiki.get("wiki_pages") and wiki.get("wiki_index") and wiki.get("wiki_log")),
        },
    )
    emit_additional_context("PostToolUse", messages)
    return 0


def enforce_wiki(data: dict[str, Any], cwd: Path, *, block: bool = False) -> int:
    schema_root = find_schema_root(cwd)
    if not schema_root:
        return 0
    policy = load_harness_policy(schema_root)
    with locked_wiki_state(data) as (_, state):
        code_files = state.get("code_files", [])
        if not code_files:
            append_trace(data, "Stop", {"gate": "Wiki", "result": "pass", "reason": "no_code_files"})
            return 0

        missing: list[str] = []
        if not state.get("wiki_pages"):
            missing.append("wiki pages not updated")
        if not state.get("wiki_index"):
            missing.append("wiki/index.md not updated")
        if not state.get("wiki_log"):
            missing.append("wiki/log.md not updated")
        if not missing:
            append_trace(data, "Stop", {"gate": "Wiki", "result": "pass", "code_files": code_files})
            return 0

        mode = "block" if block else enforcement_mode(policy, "missing_wiki_ingest")
        if mode == "observe":
            append_trace(data, "Stop", {"gate": "Wiki", "result": "observe", "missing": missing})
            return 0
        label = "Required" if mode == "block" else "Reminder"
        suffix = (
            "if this is genuinely trivial, the next Stop only reminds."
            if mode == "block"
            else "then continue the original task; this Stop hook is reminder-only."
        )
        if state.get("wiki_agent_called"):
            action = (
                "A wiki-ingest subagent was called; integrate or verify its output so "
                "wiki pages, wiki/index.md, and wiki/log.md are updated; "
            )
        else:
            action = (
                "Delegate this to a wiki-ingest subagent to update wiki pages, "
                "wiki/index.md, and wiki/log.md; "
            )
        msg = (
            f"[Wiki Ingest {label}] Code edited: "
            + ", ".join(code_files[:5])
            + ". Missing: "
            + "; ".join(missing)
            + ". "
            + action
            + suffix
        )
        if mode == "block":
            state["stop_blocks"] = state.get("stop_blocks", 0) + 1
            rc = 2
        else:
            state["stop_reminders"] = state.get("stop_reminders", 0) + 1
            rc = 0
    append_trace(
        data,
        "Stop",
        {
            "gate": "Wiki",
            "result": "blocked" if rc == 2 else mode,
            "missing": missing,
            "code_files": code_files,
        },
    )
    if mode == "block":
        print(msg, file=sys.stderr)
    else:
        emit_additional_context("Stop", [msg])
    return rc


def stop_mode_for_change(policy: dict[str, Any], state: dict[str, Any]) -> str:
    modes = ["observe", "remind", "block"]
    selected = enforcement_mode(policy, "default")
    if state.get("large_change"):
        selected = enforcement_mode(policy, "large_change")
    if state.get("risky_change"):
        selected = enforcement_mode(policy, "risky_change")
    if any(str(flag).startswith("harness_self:") for flag in state.get("risk_flags", [])):
        selected = enforcement_mode(policy, "harness_self_modification")
    return selected if selected in modes else "remind"


def evaluate_stop_requirements(root: Path, state: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    contract_files = valid_contract_artifacts(root, state.get("contract_snapshot"))
    review_status = review_artifact_status(root, state.get("review_snapshot"))
    review_files = review_status.get("passing", [])
    failing_reviews = review_status.get("failing", [])
    large_or_risky = bool(state.get("large_change") or state.get("risky_change"))

    missing: list[str] = []
    blockers: list[str] = []
    if large_or_risky and not contract_files:
        missing.append("contract")
        if enforcement_mode(policy, "missing_contract_for_large_change") == "block":
            blockers.append("missing_contract")
    if large_or_risky and not review_files:
        missing.append("review_artifact")
        if enforcement_mode(policy, "missing_reviewer_for_large_change") == "block":
            blockers.append("missing_review")
    if failing_reviews:
        missing.append("passing_review")
        blockers.append("review_not_passed")
    if large_or_risky and not state.get("validation_seen"):
        missing.append("validation_evidence")
        if enforcement_mode(policy, "missing_validation_for_large_change") == "block":
            blockers.append("missing_validation")

    state["contract_files"] = contract_files
    state["review_files"] = review_files
    return {
        "large_or_risky": large_or_risky,
        "missing": missing,
        "blockers": blockers,
        "contract_files": contract_files,
        "review_files": review_files,
        "review_status": review_status,
    }


def enforce_gan(data: dict[str, Any], cwd: Path) -> int:
    with locked_gan_state(data) as (_, state):
        if not state.get("triggered"):
            append_trace(data, "Stop", {"gate": "GAN", "result": "pass", "reason": "not_triggered"})
            return 0

        root_raw = state.get("project_root")
        root = Path(str(root_raw)) if root_raw else find_project_root(cwd)
        if root is None:
            append_trace(data, "Stop", {"gate": "GAN", "result": "pass", "reason": "no_project_root"})
            return 0
        policy = load_harness_policy(root)

        n_lines = int(state.get("total_net_lines", 0))
        n_new = len(state.get("new_files", []))
        requirements = evaluate_stop_requirements(root, state, policy)
        if not requirements["large_or_risky"] and (
            state.get("reviewer_called") or state.get("discriminator_called")
        ):
            append_trace(
                data,
                "Stop",
                {
                    "gate": "GAN",
                    "result": "pass",
                    "reason": "medium_change_reviewer_seen",
                    "risk_flags": state.get("risk_flags", []),
                },
            )
            return 0
        if requirements["large_or_risky"] and not requirements["missing"]:
            append_trace(
                data,
                "Stop",
                {
                    "gate": "GAN",
                    "result": "pass",
                    "reason": "large_or_risky_requirements_satisfied",
                    "risk_flags": state.get("risk_flags", []),
                    "contract_files": requirements["contract_files"],
                    "review_files": requirements["review_files"],
                    "validation_seen": state.get("validation_seen", False),
                },
            )
            return 0
        mode = "block" if requirements["blockers"] else stop_mode_for_change(policy, state)
        if mode == "observe":
            append_trace(
                data,
                "Stop",
                {
                    "gate": "GAN",
                    "result": "observe",
                    "missing": requirements["missing"],
                    "risk_flags": state.get("risk_flags", []),
                },
            )
            return 0

        if requirements["large_or_risky"]:
            instruction = (
                "Large/risky change: provide a valid wiki/contracts/*.md, "
                "a wiki/reviews/*-review.md with Verdict PASS, and validation evidence."
            )
        else:
            instruction = "Spawn a Codex reviewer with review/审查 in the prompt before ending."
        label = "Required" if mode == "block" else "Reminder"
        missing_text = "; missing: " + ", ".join(requirements["missing"]) if requirements["missing"] else ""
        suffix = "" if mode == "block" else " Then continue the original task; this Stop hook is reminder-only."
        msg = (
            f"[GAN Review {label}] {n_lines} net new code lines across "
            f"{len(state.get('touched_files', []))} file(s), {n_new} new file(s). "
            f"Risk flags: {', '.join(state.get('risk_flags', [])) or 'none'}. "
            + instruction
            + missing_text
            + suffix
        )
        if mode == "block":
            state["stop_blocks"] = state.get("stop_blocks", 0) + 1
            rc = 2
        else:
            state["stop_reminders"] = state.get("stop_reminders", 0) + 1
            rc = 0
    append_trace(
        data,
        "Stop",
        {
            "gate": "GAN",
            "result": "blocked" if rc == 2 else mode,
            "missing": requirements["missing"],
            "blockers": requirements["blockers"],
            "risk_flags": state.get("risk_flags", []),
            "contract_files": requirements["contract_files"],
            "review_files": requirements["review_files"],
            "validation_seen": state.get("validation_seen", False),
        },
    )
    if mode == "block":
        print(msg, file=sys.stderr)
    else:
        emit_additional_context("Stop", [msg])
    return rc


def hook_stop(data: dict[str, Any]) -> int:
    cwd = cwd_from(data)
    wiki_rc = enforce_wiki(data, cwd, block=False)
    gan_rc = enforce_gan(data, cwd)
    return wiki_rc or gan_rc


def main() -> int:
    event = os.environ.get("CODEX_HOOK_EVENT") or (sys.argv[1] if len(sys.argv) > 1 else "")
    data = load_event()
    try:
        if event == "UserPromptSubmit":
            return hook_user_prompt(data)
        if event == "SessionStart":
            return hook_session_start(data)
        if event == "PostToolUse":
            return hook_post_tool(data)
        if event == "Stop":
            return hook_stop(data)
        return 0
    except Exception:
        try:
            with ERROR_LOG.open("a", encoding="utf-8") as f:
                f.write(f"\n## {datetime.now().isoformat()} event={event}\n")
                f.write(traceback.format_exc())
        except OSError:
            pass
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
