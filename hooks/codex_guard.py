#!/usr/bin/env python3
"""Risk-only Codex lifecycle harness.

Ordinary work is deliberately silent. The hook expands process only after a
structured file tool proves that the current turn changed an objectively
governed path, or after an explicit sensitive implementation request is paired
with a review-relevant code/config write.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime
from fnmatch import fnmatchcase
from hashlib import sha1
from pathlib import Path
from typing import Any, Iterable


POLICY_VERSION = 3
DEFAULT_POLICY: dict[str, Any] = {
    "policy_version": POLICY_VERSION,
    "enforcement": {
        "default": "observe",
        "missing_governed_artifacts": "block",
    },
    "governed_paths": [
        "hooks/**",
        "hooks.json",
        "harness_policy.yaml",
        ".codex/**",
        "**/auth/**",
        "**/migrations/**",
        "**/deploy/**",
        "**/.github/workflows/**",
        "**/*sandbox*",
        "**/*permission*",
    ],
    "governed_path_terms": [
        "auth",
        "authentication",
        "authorization",
        "oauth",
        "oidc",
        "sso",
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
    "prompt_risk_terms": [
        "security",
        "安全",
        "auth",
        "authentication",
        "authorization",
        "oauth",
        "oidc",
        "sso",
        "permission",
        "权限",
        "sandbox",
        "migration",
        "迁移",
        "deploy",
        "部署",
        "ci",
        "hook enforcement",
        "harness enforcement",
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
    "Contract",
    "Validation evidence",
    "Blocking issues",
    "Residual risk",
    "Required fixes before merge",
    "Wiki check",
)
VALID_REVIEW_VERDICTS = {"PASS", "FAIL", "NEEDS_HUMAN"}

ACTION_RE = re.compile(
    r"实现|修改|修复|新增|重构|强化|加固|更改|优化|更新|"
    r"\b(?:implement|modify|fix|add|refactor|harden|secure|change|optimize|update)\b",
    re.IGNORECASE,
)
NEGATED_ACTION_RE = re.compile(
    r"(?:不|不要|无需|无须)\s*(?:实现|修改|修复|新增|重构|强化|加固|更改|优化|更新)|"
    r"\b(?:do\s+not|don't|without)\s+"
    r"(?:implement|modify|fix|add|refactor|harden|secure|change|optimize|update)\w*\b",
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
GUIDANCE_FILENAMES = {"AGENTS.md", "SCHEMA.md"}

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
HOOK_PROCESS_NONCE: str | None = None


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
    """Parse the small YAML subset used by harness_policy.yaml."""
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
            result[current_key] = parse_policy_scalar(value) if value.strip() else {}
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
        elif key in default:
            merged[key] = value
    return merged


def load_harness_policy(root: Path | None) -> dict[str, Any]:
    if root is None:
        return merge_policy(DEFAULT_POLICY, {})
    try:
        parsed = parse_simple_yaml((root / "harness_policy.yaml").read_text(errors="replace"))
    except OSError:
        return merge_policy(DEFAULT_POLICY, {})
    return merge_policy(DEFAULT_POLICY, parsed)


def enforcement_mode(policy: dict[str, Any], name: str) -> str:
    enforcement = policy.get("enforcement") if isinstance(policy.get("enforcement"), dict) else {}
    mode = str(enforcement.get(name) or enforcement.get("default") or "observe")
    return mode if mode in {"observe", "remind", "block"} else "observe"


def path_matches_any(rel: str, patterns: Iterable[str]) -> str | None:
    normalized = rel.replace("\\", "/").removeprefix("./")
    for pattern in patterns:
        pat = str(pattern).replace("\\", "/").removeprefix("./")
        candidates = [pat, pat[3:]] if pat.startswith("**/") else [pat]
        if any(fnmatchcase(normalized, candidate) for candidate in candidates):
            return pat
    return None


def governed_flags_for_paths(paths: Iterable[str], policy: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    patterns = policy.get("governed_paths", [])
    terms = {str(term).lower() for term in policy.get("governed_path_terms", []) if str(term)}
    for rel in paths:
        match = path_matches_any(rel, patterns)
        if match:
            add_unique(flags, f"governed_path:{match}")
            continue
        tokens = set(re.findall(r"[a-z0-9]+", rel.lower()))
        term = next((candidate for candidate in terms if candidate in tokens), None)
        if term:
            add_unique(flags, f"governed_term:{term}")
    return flags


def load_event() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
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


def nested_values(
    data: dict[str, Any], keys: tuple[str, ...], *, include_plain_id: bool = False
) -> Iterable[Any]:
    stack: list[tuple[dict[str, Any], bool]] = [(data, False)]
    seen: set[int] = set()
    while stack:
        current, allow_plain_id = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
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
    return any(
        Path(arg).name.lower() == "codex"
        or Path(arg).name.lower().startswith("codex-")
        or "codex-cli" in Path(arg).name.lower()
        for arg in argv[1:6]
    )


def process_start_time(pid: int) -> str | None:
    try:
        parts = (Path("/proc") / str(pid) / "stat").read_text(errors="replace").split()
    except OSError:
        return None
    return parts[21] if len(parts) > 21 else None


def codex_process_scope() -> str | None:
    pid = os.getppid()
    for _ in range(8):
        if pid <= 1:
            break
        proc = Path("/proc") / str(pid)
        try:
            argv = [
                part.decode(errors="replace")
                for part in (proc / "cmdline").read_bytes().split(b"\x00")
                if part
            ]
            stat = (proc / "stat").read_text(errors="replace").split()
        except OSError:
            break
        if looks_like_codex_process(argv):
            return safe_id(f"pid{pid}-{stat[21] if len(stat) > 21 else '0'}")
        try:
            pid = int(stat[3])
        except (IndexError, ValueError):
            break
    return None


def hook_process_scope() -> str:
    pid = os.getpid()
    started = process_start_time(pid)
    if started:
        return safe_id(f"hookpid{pid}-{started}")
    global HOOK_PROCESS_NONCE
    if HOOK_PROCESS_NONCE is None:
        HOOK_PROCESS_NONCE = short_hash(f"{pid}-{datetime.now().isoformat()}-{os.urandom(8).hex()}")
    return safe_id(f"hookpid{pid}-{HOOK_PROCESS_NONCE}")


def session_id(data: dict[str, Any]) -> str:
    base = ""
    for value in nested_values(data, SESSION_ID_KEYS, include_plain_id=True):
        base = safe_id(value)
        if base != "unknown":
            break
    if not base:
        for key in ENV_SESSION_ID_KEYS:
            if os.environ.get(key):
                base = safe_id(os.environ[key])
                break
    if not base:
        for value in nested_values(data, PATH_ID_KEYS):
            base = id_from_path_value(value) or ""
            if base:
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
        base = f"{base}.{hook_process_scope()}"
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
    record = {"event": event, "time": datetime.now().isoformat(timespec="seconds"), **payload}
    try:
        with (session_trace_dir(data) / "trace.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def meta_path(data: dict[str, Any]) -> Path:
    return state_dir() / f"codex-hook-meta-{session_id(data)}.json"


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
            handle.close()


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


def explicit_turn_id(data: dict[str, Any]) -> str | None:
    for value in nested_values(data, TURN_ID_KEYS):
        turn = safe_id(value)
        if turn != "unknown":
            return turn
    return None


def current_turn_id(data: dict[str, Any]) -> str:
    return explicit_turn_id(data) or safe_id(load_state(meta_path(data)).get("active_turn") or "unknown")


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


def governed_state_path(data: dict[str, Any]) -> Path:
    return state_dir() / f"governed-v3-{session_id(data)}-{current_turn_id(data)}.json"


@contextmanager
def locked_governed_state(data: dict[str, Any]) -> Iterable[tuple[Path, dict[str, Any]]]:
    path = governed_state_path(data)
    with state_file_lock(path):
        state = load_state(path)
        state.setdefault("policy_version", POLICY_VERSION)
        state.setdefault("changed_paths", [])
        state.setdefault("governed_paths", [])
        state.setdefault("risk_flags", [])
        state.setdefault("governed", False)
        state.setdefault("prompt_risk_signal", False)
        state.setdefault("prompt_risk_reason", "")
        state.setdefault("review_snapshot_at_last_edit", {})
        state.setdefault("nudge_printed", False)
        state.setdefault("contract_snapshot", {})
        state.setdefault("review_snapshot", {})
        yield path, state
        save_state(path, state)


def cwd_from(data: dict[str, Any]) -> Path:
    raw = data.get("cwd") or data.get("working_directory") or os.getcwd()
    return Path(str(raw)).expanduser().resolve()


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


def git_output(root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def resolve_git_path(root: Path, raw: str) -> str:
    if not raw:
        return ""
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = root / path
    try:
        return str(path.resolve())
    except OSError:
        return str(path.absolute())


def worktree_identity(root: Path) -> dict[str, str]:
    resolved_root = root.expanduser().resolve()
    top = git_output(resolved_root, "rev-parse", "--show-toplevel")
    worktree_root = resolve_git_path(resolved_root, top) or str(resolved_root)
    git_dir = resolve_git_path(resolved_root, git_output(resolved_root, "rev-parse", "--absolute-git-dir"))
    common_dir = resolve_git_path(resolved_root, git_output(resolved_root, "rev-parse", "--git-common-dir"))
    branch = git_output(resolved_root, "symbolic-ref", "--quiet", "--short", "HEAD")
    head = git_output(resolved_root, "rev-parse", "--verify", "HEAD")
    if not git_dir:
        branch = "non-git"
    elif not branch:
        branch = f"detached@{head[:12]}" if head else "detached"
    return {
        "root": worktree_root,
        "git_dir": git_dir,
        "common_dir": common_dir,
        "branch": branch,
        "head": head,
        "scope_key": short_hash(f"{worktree_root}\n{git_dir or 'non-git'}"),
    }


def same_worktree(first: Any, second: Any) -> bool:
    return bool(
        isinstance(first, dict)
        and isinstance(second, dict)
        and first.get("scope_key")
        and first.get("scope_key") == second.get("scope_key")
    )


def worktree_label(identity: Any, fallback: Path) -> str:
    value = identity if isinstance(identity, dict) else worktree_identity(fallback)
    return f"Worktree: {value.get('root') or fallback.resolve()} ({value.get('branch') or 'unknown'})"


def content_hash(path: Path) -> str:
    try:
        return sha1(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def bootstrap_message(data: dict[str, Any], schema_root: Path, project_root: Path | None) -> str | None:
    root = project_root or schema_root
    identity = worktree_identity(root)
    policy = load_harness_policy(root)
    current = {
        "scope_key": identity.get("scope_key", ""),
        "schema_hash": content_hash(schema_root / "SCHEMA.md"),
        "index_hash": content_hash(schema_root / "wiki" / "index.md"),
        "agents_hash": content_hash(root / "AGENTS.md"),
        "policy_hash": content_hash(root / "harness_policy.yaml"),
        "policy_version": int(policy.get("policy_version") or POLICY_VERSION),
    }
    path = meta_path(data)
    with state_file_lock(path):
        meta = load_state(path)
        previous = meta.get("bootstrap") if isinstance(meta.get("bootstrap"), dict) else {}
        legacy = meta.get("wiki_bootstrap") if isinstance(meta.get("wiki_bootstrap"), dict) else {}
        meta["bootstrap"] = current
        save_state(path, meta)
    if not previous and legacy.get("scope_key") == current["scope_key"]:
        return "Harness V3 replaced the active policy; start a new Codex session to drop stale instructions."
    if not previous or previous.get("scope_key") != current["scope_key"]:
        return "Wiki bootstrap: read SCHEMA.md and wiki/index.md once for this worktree."
    if (
        previous.get("agents_hash") != current["agents_hash"]
        or previous.get("policy_hash") != current["policy_hash"]
        or previous.get("policy_version") != current["policy_version"]
    ):
        return "Harness policy changed; start a new Codex session so stale AGENTS instructions cannot persist."
    changed: list[str] = []
    if previous.get("schema_hash") != current["schema_hash"]:
        changed.append("SCHEMA.md")
    if previous.get("index_hash") != current["index_hash"]:
        changed.append("wiki/index.md")
    return "Wiki changed: re-read " + " and ".join(changed) + "." if changed else None


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
            return {"command": value}
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
    value = data.get("prompt") or data.get("last_user_message") or ""
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def prompt_risk_reason(prompt: str, policy: dict[str, Any]) -> str:
    actionable = NEGATED_ACTION_RE.sub("", prompt)
    if not ACTION_RE.search(actionable):
        return ""
    lower = actionable.lower()
    for raw in policy.get("prompt_risk_terms", []):
        term = str(raw).lower()
        if term.isascii():
            if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower):
                return term
        elif term and term in lower:
            return term
    return ""


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


def emit_stop_block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


def resolve_path(cwd: Path, raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    return path if path.is_absolute() else cwd / path


def rel_in_root(root: Path, cwd: Path, raw_path: str) -> str | None:
    try:
        return resolve_path(cwd, raw_path).resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return None


def parse_apply_patch_paths(patch: str) -> list[str]:
    paths: list[str] = []
    for line in patch.splitlines():
        for prefix in ("*** Add File: ", "*** Update File: ", "*** Delete File: "):
            if line.startswith(prefix):
                add_unique(paths, line.removeprefix(prefix).strip())
                break
    return paths


def structured_paths(name: str, args: dict[str, Any]) -> list[str]:
    short = short_tool_name(name).lower()
    if short in {"write", "edit", "multiedit"}:
        raw = args.get("file_path") or args.get("path")
        return [raw] if isinstance(raw, str) and raw else []
    if short in {"apply_patch", "edit|write"}:
        patch = args.get("patch") or args.get("input") or args.get("command") or args.get("cmd") or ""
        return parse_apply_patch_paths(patch) if isinstance(patch, str) else []
    return []


def collect_structured_paths(root: Path, cwd: Path, calls: Iterable[tuple[str, dict[str, Any]]]) -> list[str]:
    paths: list[str] = []
    policy = load_harness_policy(root)
    for name, args in calls:
        for raw in structured_paths(name, args):
            rel = rel_in_root(root, cwd, raw)
            if rel and not path_matches_any(rel, policy.get("generated_paths", [])):
                add_unique(paths, rel)
    return paths


def is_artifact_path(rel: str) -> bool:
    return bool(
        re.fullmatch(r"wiki/contracts/[^/]+\.md", rel)
        or re.fullmatch(r"wiki/reviews/[^/]+-review\.md", rel)
    )


def is_review_relevant_path(rel: str) -> bool:
    if is_artifact_path(rel):
        return False
    if rel.startswith(DOC_DIR_PREFIXES) or Path(rel).suffix.lower() in DOC_SUFFIXES:
        return Path(rel).name in GUIDANCE_FILENAMES
    suffix = Path(rel).suffix.lower()
    return suffix in CODE_SUFFIXES or suffix in CONFIG_SUFFIXES or Path(rel).name in CODE_FILENAMES


def file_fingerprint(path: Path) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError:
        return {"exists": False, "hash": ""}
    return {
        "exists": True,
        "hash": sha1(data).hexdigest(),
    }


def artifact_snapshot(root: Path, pattern: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    try:
        paths = sorted(root.glob(pattern))
    except OSError:
        return result
    for path in paths:
        if path.is_file():
            try:
                result[path.relative_to(root).as_posix()] = file_fingerprint(path)
            except ValueError:
                continue
    return result


def changed_artifacts(
    root: Path, pattern: str, before: Any
) -> list[tuple[Path, dict[str, Any]]]:
    baseline = before if isinstance(before, dict) else {}
    after = artifact_snapshot(root, pattern)
    return [
        (root / rel, fingerprint)
        for rel, fingerprint in after.items()
        if not isinstance(baseline.get(rel), dict)
        or baseline[rel].get("hash") != fingerprint.get("hash")
    ]


def normalize_heading(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def markdown_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = re.match(r"^#{1,3}\s+(.+?)\s*$", line)
        if match:
            current = normalize_heading(match.group(1))
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)
    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def read_sections(path: Path) -> dict[str, str]:
    try:
        return markdown_sections(path.read_text(errors="replace"))
    except OSError:
        return {}


def contract_is_valid(path: Path) -> bool:
    sections = read_sections(path)
    return all(normalize_heading(name) in sections for name in REQUIRED_CONTRACT_SECTIONS)


def review_verdict(sections: dict[str, str]) -> str | None:
    value = sections.get(normalize_heading("Verdict"), "")
    match = re.search(r"\b(PASS|FAIL|NEEDS_HUMAN)\b", value, re.IGNORECASE)
    if not match:
        return None
    verdict = match.group(1).upper()
    return verdict if verdict in VALID_REVIEW_VERDICTS else None


def review_contract_path(sections: dict[str, str]) -> str | None:
    value = sections.get(normalize_heading("Contract"), "")
    match = re.search(r"wiki/contracts/[A-Za-z0-9._/-]+\.md", value)
    return match.group(0) if match else None


def validation_is_explicit(sections: dict[str, str]) -> bool:
    value = sections.get(normalize_heading("Validation evidence"), "")
    has_command = bool(re.search(r"(?im)^\s*(?:[-*]\s*)?Command\s*:\s*`?\S+", value))
    result = re.search(r"(?im)^\s*(?:[-*]\s*)?Result\s*:\s*(.+)$", value)
    if not result:
        return False
    outcome = result.group(1)
    has_failure = bool(
        re.search(r"\b(?:FAIL|FAILED|ERROR)\b|\bexit(?:\s+code)?\s*[:=]?\s*[1-9]\d*\b", outcome, re.IGNORECASE)
    )
    has_success = bool(
        re.search(r"\b(?:PASS|SUCCESS|OK)\b|\bexit(?:\s+code)?\s*[:=]?\s*0\b", outcome, re.IGNORECASE)
    )
    return has_command and has_success and not has_failure


def evaluate_artifacts(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    contracts = changed_artifacts(root, "wiki/contracts/*.md", state.get("contract_snapshot"))
    reviews = changed_artifacts(root, "wiki/reviews/*-review.md", state.get("review_snapshot"))
    valid_changed_contracts = {
        path.relative_to(root).as_posix() for path, _ in contracts if contract_is_valid(path)
    }
    last_edit_snapshot = state.get("review_snapshot_at_last_edit")
    if not isinstance(last_edit_snapshot, dict):
        last_edit_snapshot = {}
    review_status: list[dict[str, Any]] = []
    referenced_valid_contracts: set[str] = set()
    passing: list[str] = []
    for path, fingerprint in reviews:
        sections = read_sections(path)
        rel = path.relative_to(root).as_posix()
        contract_rel = review_contract_path(sections)
        contract_ok = bool(contract_rel and contract_rel in valid_changed_contracts)
        if contract_ok and contract_rel:
            referenced_valid_contracts.add(contract_rel)
        headings_ok = all(normalize_heading(name) in sections for name in REQUIRED_REVIEW_SECTIONS)
        previous_at_edit = last_edit_snapshot.get(rel)
        fresh = not isinstance(previous_at_edit, dict) or (
            previous_at_edit.get("hash") != fingerprint.get("hash")
        )
        verdict = review_verdict(sections)
        validation_ok = validation_is_explicit(sections)
        item = {
            "path": rel,
            "verdict": verdict or "MISSING",
            "headings_ok": headings_ok,
            "contract": contract_rel or "",
            "contract_ok": contract_ok,
            "validation_ok": validation_ok,
            "fresh": fresh,
        }
        review_status.append(item)
        if verdict == "PASS" and headings_ok and contract_ok and validation_ok and fresh:
            passing.append(rel)
    contract_ok = bool(valid_changed_contracts)
    missing: list[str] = []
    if not contract_ok:
        missing.append("contract")
    if not passing:
        missing.append("current_pass_review")
    return {
        "missing": missing,
        "contracts": sorted(valid_changed_contracts | referenced_valid_contracts),
        "passing_reviews": passing,
        "reviews": review_status,
    }


def initialize_turn(data: dict[str, Any], prompt: str) -> tuple[Path | None, Path | None]:
    cwd = cwd_from(data)
    root = find_project_root(cwd)
    schema_root = find_schema_root(cwd)
    begin_turn(data)
    if root:
        policy = load_harness_policy(root)
        reason = prompt_risk_reason(prompt, policy)
        with locked_governed_state(data) as (_, state):
            state.clear()
            state.update(
                {
                    "policy_version": int(policy.get("policy_version") or POLICY_VERSION),
                    "project_root": str(root),
                    "worktree": worktree_identity(root),
                    "changed_paths": [],
                    "governed_paths": [],
                    "risk_flags": [],
                    "governed": False,
                    "prompt_risk_signal": bool(reason),
                    "prompt_risk_reason": reason,
                    "review_snapshot_at_last_edit": {},
                    "nudge_printed": False,
                    "contract_snapshot": artifact_snapshot(root, "wiki/contracts/*.md"),
                    "review_snapshot": artifact_snapshot(root, "wiki/reviews/*-review.md"),
                }
            )
    return root, schema_root


def hook_user_prompt(data: dict[str, Any]) -> int:
    root, schema_root = initialize_turn(data, prompt_text(data))
    messages: list[str] = []
    if schema_root:
        message = bootstrap_message(data, schema_root, root)
        if message:
            messages.append(message)
    emit_additional_context("UserPromptSubmit", messages)
    return 0


def hook_session_start(data: dict[str, Any]) -> int:
    cwd = cwd_from(data)
    root = find_project_root(cwd)
    schema_root = find_schema_root(cwd)
    messages: list[str] = []
    if schema_root:
        message = bootstrap_message(data, schema_root, root)
        if message:
            messages.append(message)
    emit_additional_context("SessionStart", messages)
    return 0


def hook_post_tool(data: dict[str, Any]) -> int:
    cwd = cwd_from(data)
    root = find_project_root(cwd)
    if root is None:
        return 0
    calls = list(iter_tool_calls(tool_name(data), tool_input(data)))
    paths = collect_structured_paths(root, cwd, calls)
    if not paths:
        return 0
    with locked_governed_state(data) as (_, state):
        root_raw = state.get("project_root")
        stored_root = Path(str(root_raw)) if root_raw else root
        if stored_root.resolve() != root.resolve():
            root = stored_root
            paths = collect_structured_paths(root, cwd, calls)
            if not paths:
                return 0
        state.setdefault("project_root", str(root))
        state.setdefault("worktree", worktree_identity(root))
        policy = load_harness_policy(root)
        for rel in paths:
            add_unique(state["changed_paths"], rel)
        relevant = [rel for rel in paths if is_review_relevant_path(rel)]
        flags = governed_flags_for_paths(paths, policy)
        prompt_trigger = bool(state.get("prompt_risk_signal") and relevant)
        if flags or prompt_trigger:
            for rel in relevant or paths:
                add_unique(state["governed_paths"], rel)
            for flag in flags:
                add_unique(state["risk_flags"], flag)
            if prompt_trigger:
                add_unique(state["risk_flags"], f"prompt:{state.get('prompt_risk_reason')}")
            first = not state.get("governed")
            state["governed"] = True
            if first:
                append_trace(
                    data,
                    "GovernedChange",
                    {
                        "paths": state["governed_paths"],
                        "risk_flags": state["risk_flags"],
                        "worktree": state.get("worktree", {}),
                    },
                )
        if state.get("governed") and relevant:
            state["review_snapshot_at_last_edit"] = artifact_snapshot(
                root, "wiki/reviews/*-review.md"
            )
        if state.get("governed") and not state.get("nudge_printed"):
            state["nudge_printed"] = True
            emit_additional_context(
                "PostToolUse",
                ["Harness V3: governed change detected; finish with a short contract and one current PASS review."],
            )
    return 0


def hook_stop(data: dict[str, Any]) -> int:
    if data.get("stop_hook_active") is True:
        append_trace(data, "Stop", {"result": "pass", "reason": "stop_hook_active"})
        return 0
    cwd = cwd_from(data)
    with locked_governed_state(data) as (_, state):
        if not state.get("governed"):
            return 0
        root_raw = state.get("project_root")
        root = Path(str(root_raw)) if root_raw else find_project_root(cwd)
        if root is None:
            return 0
        stored = state.get("worktree")
        current_root = find_project_root(cwd) or root
        current = worktree_identity(current_root)
        if stored and not same_worktree(stored, current):
            append_trace(
                data,
                "Stop",
                {
                    "result": "pass",
                    "reason": "worktree_scope_mismatch",
                    "stored_worktree": stored,
                    "current_worktree": current,
                },
            )
            return 0
        policy = load_harness_policy(root)
        evidence = evaluate_artifacts(root, state)
        if not evidence["missing"]:
            append_trace(
                data,
                "Stop",
                {
                    "result": "pass",
                    "reason": "governed_requirements_satisfied",
                    "contracts": evidence["contracts"],
                    "reviews": evidence["passing_reviews"],
                },
            )
            return 0
        mode = enforcement_mode(policy, "missing_governed_artifacts")
        if mode != "block":
            append_trace(data, "Stop", {"result": mode, "missing": evidence["missing"]})
            return 0
        reason = (
            f"[Harness V3 block] Governed change missing: {', '.join(evidence['missing'])}. "
            f"Add/update one short contract and a fresh PASS review linked to it, then continue. "
            f"{worktree_label(stored, root)}"
        )
        append_trace(
            data,
            "Stop",
            {
                "result": "blocked",
                "missing": evidence["missing"],
                "risk_flags": state.get("risk_flags", []),
                "reviews": evidence["reviews"],
            },
        )
        emit_stop_block(reason)
    return 0


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
            with ERROR_LOG.open("a", encoding="utf-8") as handle:
                handle.write(f"\n## {datetime.now().isoformat()} event={event}\n")
                handle.write(traceback.format_exc())
        except OSError:
            pass
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
