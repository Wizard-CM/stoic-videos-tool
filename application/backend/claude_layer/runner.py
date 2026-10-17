"""Runs one headless Claude Code session (Claude Agent SDK) inside a task workspace.

The Opus lead gets Claude Code's own system prompt plus ToonForge's lead instructions, the file tools, the Agent tool
for its Sonnet and Haiku workers, and the in-process "toonforge" MCP tools (checks and previews). Every message is
turned into a short activity line for the UI, and the run ends as a ClaudeRun with a readable error when it fails.
"""

import asyncio
import concurrent.futures
import json
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from claude_layer import agents, prompts
from claude_layer.settings import api_key, claude_settings, fake_mode
from claude_layer.workspace import append_activity, now_iso, relative_name
from engine.errors import Cancelled

try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeSDKError,
        CLIJSONDecodeError,
        CLINotFoundError,
        ProcessError,
        ResultError,
        ResultMessage,
        SystemMessage,
        TextBlock,
        ToolResultBlock,
        ToolUseBlock,
        UserMessage,
        query,
    )

    SDK_IMPORT_ERROR: ImportError | None = None
except ImportError as import_error:  # the app still starts; the status route says what to install
    query = None
    SDK_IMPORT_ERROR = import_error

# Tests replace this with a fake async generator: QUERY(prompt=..., options=...) yields SDK message objects.
QUERY = query

MCP_SERVER_NAME = "toonforge"
BUILT_IN_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Agent"]
DELEGATION_TOOLS = ("Agent", "Task")  # "Task" on older Claude Code versions
CANCEL_POLL_SECONDS = 0.5
MAX_ACTIVITY_TEXT = 200
MAX_ERROR_DETAIL = 300
STDERR_LINES_KEPT = 40
MAX_TOOL_RESULT_CHARS = 4_000_000  # check tools return large images; keep them inline for Claude
# The SDK's subprocess transport defaults to a 1 MB cap per stdout line and raises CLIJSONDecodeError past it, well
# under what a check/preview tool's image can produce. Give it enough headroom above MAX_TOOL_RESULT_CHARS.
MAX_SDK_BUFFER_BYTES = 8_000_000
MAX_MCP_OUTPUT_TOKENS = "200000"
CLIENT_APP = "toonforge/2.0"

SDK_MISSING = "The Claude Agent SDK isn't installed. Run the setup script again (it installs claude-agent-sdk, which includes Claude Code)."
NOT_INSTALLED = (
    "Claude Code isn't installed. Run the setup script again (it installs claude-agent-sdk, which includes Claude Code), "
    "or set claude.cli_path in config.yaml to a claude executable."
)
SIGN_IN = (
    "Claude couldn't sign in. Run `claude login` to sign in with your Claude Pro/Max subscription, or set the "
    "{env} environment variable to an Anthropic API key, then restart ToonForge."
)
TURN_LIMIT = "Stopped: the task hit its turn limit (claude.max_turns in config.yaml). Raise the limit or try again."
BUDGET_LIMIT = "Stopped: the task hit its budget limit (claude.max_budget_usd in config.yaml). Raise the limit or try again."
RATE_LIMITED = "Claude is rate-limited right now (too many requests, or the usage limit was reached). Wait a few minutes and try again."
BILLING = "Claude refused the request because of a billing problem on the Anthropic account. Check the account's credit balance."
OVERLOADED = "Claude's servers are busy right now. Try again in a few minutes."
BAD_OUTPUT = "Claude Code sent output the app couldn't read. Update ToonForge (and claude-agent-sdk) and try again."
NO_RESULT = "Claude Code stopped without finishing the task. Try again."
SIGN_IN_HINTS = ("invalid api key", "api key", "authentication", "not logged in", "please run /login", "unauthorized", "401", "oauth")


@dataclass
class ClaudeRun:
    ok: bool
    text: str
    cost_usd: float | None
    turns: int
    error: str | None
    models: list[str] = field(default_factory=list)  # every model that worked on the run (lead first)
    session_id: str | None = None  # lets a follow-up run continue the same conversation


def short_text(text: str, limit: int = MAX_ACTIVITY_TEXT) -> str:
    """The first paragraph, on one line, cut to `limit` characters."""
    text = (text or "").strip()
    first = text.split("\n\n")[0]
    first = " ".join(first.split())
    if len(first) > limit:
        first = first[: limit - 1].rstrip() + "…"
    return first


def make_emitter(workspace: Path, on_activity: Callable[[dict], None]) -> Callable[..., None]:
    """emit(who, kind, text, **extra): logs the event to activity.jsonl and hands it to on_activity."""

    def emit(who: str, kind: str, text: str, **extra) -> None:
        event = {"t": now_iso(), "who": who, "kind": kind, "text": short_text(text), **extra}
        append_activity(workspace, event)
        try:
            on_activity(event)
        except Cancelled:
            raise
        except Exception:
            pass  # a progress callback must never break the run

    return emit


# ---------- messages -> activity ----------

def tool_result_text(content) -> str:
    """The text parts of a tool result (a string or a list of content blocks)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "\n".join(parts)


def first_line(text: str) -> str:
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


class ActivityMapper:
    """Turns SDK messages into (who, kind, text) activity lines and remembers the final result."""

    def __init__(self, workspace: Path, lead_model: str):
        self.workspace = workspace
        self.lead_model = lead_model
        self.workers_by_tool_use: dict[str, str] = {}  # Agent tool_use id -> worker name
        self.tool_names: dict[str, str] = {}  # tool_use id -> tool name
        self.result = None
        self.assistant_error: str | None = None
        self.last_text = ""
        self.started = False

    def who(self, parent_tool_use_id: str | None, model: str | None = None) -> str:
        if not parent_tool_use_id:
            return "lead"
        return self.workers_by_tool_use.get(parent_tool_use_id) or agents.worker_name_for_model(model) or "worker"

    def file_name(self, tool_input: dict) -> str:
        path = tool_input.get("file_path") or tool_input.get("path") or tool_input.get("notebook_path") or ""
        return relative_name(Path(path), self.workspace) if path else "a file"

    def describe_tool_use(self, block, who: str) -> list[tuple[str, str, str]]:
        name = block.name
        tool_input = block.input or {}
        self.tool_names[block.id] = name
        if name in DELEGATION_TOOLS:
            worker = str(tool_input.get("subagent_type") or "worker")
            self.workers_by_tool_use[block.id] = worker
            task = tool_input.get("description") or first_line(str(tool_input.get("prompt") or "")) or "a subtask"
            return [(who, "delegate", f"Delegated to {worker}: {task}")]
        if name.startswith(f"mcp__{MCP_SERVER_NAME}__"):
            return []  # the tool's result line says what it found
        if name == "Write":
            return [(who, "tool", f"Wrote {self.file_name(tool_input)}")]
        if name in ("Edit", "MultiEdit"):
            return [(who, "tool", f"Edited {self.file_name(tool_input)}")]
        if name == "Read":
            return [(who, "tool", f"Read {self.file_name(tool_input)}")]
        if name == "Glob":
            return [(who, "tool", f"Looked for files: {tool_input.get('pattern', '')}")]
        if name == "Grep":
            return [(who, "tool", f"Searched the files for \"{tool_input.get('pattern', '')}\"")]
        return [(who, "tool", f"Used {name}")]

    def describe_tool_result(self, block, who: str) -> list[tuple[str, str, str]]:
        tool_name = self.tool_names.get(block.tool_use_id, "")
        text = first_line(tool_result_text(block.content))
        if block.tool_use_id in self.workers_by_tool_use:
            worker = self.workers_by_tool_use[block.tool_use_id]
            if block.is_error:
                return [(worker, "result", f"{worker} stopped: {text or 'an error'}")]
            return [(worker, "result", f"{worker} finished: {text or 'done'}")]
        if tool_name.startswith(f"mcp__{MCP_SERVER_NAME}__"):
            short_name = tool_name.split("__", 2)[-1]
            if block.is_error:
                return [(who, "tool", f"{short_name} failed: {text}")]
            return [(who, "tool", text or f"Ran {short_name}")]
        return []

    def events_for(self, message) -> list[tuple[str, str, str]]:
        events: list[tuple[str, str, str]] = []
        if isinstance(message, AssistantMessage):
            who = self.who(message.parent_tool_use_id, message.model)
            if message.error and not message.parent_tool_use_id:
                self.assistant_error = str(message.error)
            for block in message.content:
                if isinstance(block, TextBlock) and block.text.strip():
                    if who == "lead":
                        self.last_text = block.text
                    events.append((who, "note", block.text))
                elif isinstance(block, ToolUseBlock):
                    events.extend(self.describe_tool_use(block, who))
        elif isinstance(message, UserMessage):
            who = self.who(message.parent_tool_use_id)
            if isinstance(message.content, list):
                for block in message.content:
                    if isinstance(block, ToolResultBlock):
                        events.extend(self.describe_tool_result(block, who))
        elif isinstance(message, ResultMessage):
            self.result = message
        elif isinstance(message, SystemMessage) and message.subtype == "init" and not self.started:
            self.started = True
            model = (message.data or {}).get("model") or self.lead_model
            events.append(("lead", "note", f"Claude Code started ({model})"))
        return events


# ---------- errors -> plain sentences ----------

def _sign_in_message() -> str:
    return SIGN_IN.format(env=claude_settings()["api_key_env"])


def _detail(text: str | None) -> str:
    return short_text(text or "", MAX_ERROR_DETAIL)


def error_for_status(status: int | None, detail: str) -> str | None:
    if status in (401, 403):
        return _sign_in_message()
    if status == 402:
        return BILLING
    if status == 429:
        return RATE_LIMITED
    if status in (500, 502, 503, 504, 529):
        return OVERLOADED
    if any(hint in detail.lower() for hint in SIGN_IN_HINTS):
        return _sign_in_message()
    return None


def error_for_result(subtype: str | None, terminal_reason: str | None, status: int | None, errors: list[str] | None,
                     result_text: str | None, assistant_error: str | None = None) -> str:
    """A plain sentence for a failed result (from a ResultMessage or a ResultError)."""
    if subtype == "error_max_turns" or terminal_reason == "max_turns":
        return TURN_LIMIT
    if subtype == "error_max_budget_usd" or terminal_reason in ("max_budget", "max_budget_usd"):
        return BUDGET_LIMIT
    if assistant_error == "authentication_failed":
        return _sign_in_message()
    if assistant_error == "billing_error":
        return BILLING
    if assistant_error == "rate_limit":
        return RATE_LIMITED
    if assistant_error == "server_error":
        return OVERLOADED
    detail = _detail("; ".join(errors or []) or result_text or "")
    by_status = error_for_status(status, detail)
    if by_status:
        return by_status
    if detail:
        return f"Claude stopped with an error: {detail}"
    return NO_RESULT


def error_for_exception(error: BaseException, mapper: ActivityMapper, stderr_tail: list[str]) -> str:
    """A plain sentence for an exception raised by the SDK."""
    if isinstance(error, ResultError):
        return error_for_result(error.subtype, error.terminal_reason, error.api_error_status, error.errors, error.result,
                                mapper.assistant_error)
    if isinstance(error, CLINotFoundError):
        return NOT_INSTALLED
    if isinstance(error, CLIJSONDecodeError):
        return BAD_OUTPUT
    if isinstance(error, ProcessError):
        stderr = (error.stderr or "") + "\n" + "\n".join(stderr_tail)
        if mapper.assistant_error == "authentication_failed" or any(hint in stderr.lower() for hint in SIGN_IN_HINTS):
            return _sign_in_message()
        if mapper.result is not None and (mapper.result.is_error or mapper.result.subtype != "success"):
            return result_error(mapper)
        tail = _detail(" ".join(line for line in stderr_tail[-3:] if line.strip()))
        code = f" (exit code {error.exit_code})" if error.exit_code is not None else ""
        return f"Claude Code stopped unexpectedly{code}." + (f" {tail}" if tail else "")
    if isinstance(error, ClaudeSDKError):
        return f"Claude Code failed: {_detail(str(error))}"
    if isinstance(error, FileNotFoundError):
        return NOT_INSTALLED
    return f"Claude Code failed ({type(error).__name__}): {_detail(str(error))}"


def result_error(mapper: ActivityMapper) -> str:
    result = mapper.result
    return error_for_result(result.subtype, result.terminal_reason, result.api_error_status, result.errors, result.result,
                            mapper.assistant_error)


def first_leaf_exception(error: BaseException) -> BaseException:
    while isinstance(error, BaseExceptionGroup) and error.exceptions:
        error = error.exceptions[0]
    return error


# ---------- options ----------

def claude_env(settings: dict) -> dict[str, str]:
    """Environment for the Claude Code process: the API key, the worker caps and a few output limits."""
    env = {
        "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",  # workers never spawn workers
        "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": str(settings["max_parallel_workers"]),
        "MAX_MCP_OUTPUT_TOKENS": MAX_MCP_OUTPUT_TOKENS,
        "CLAUDE_AGENT_SDK_CLIENT_APP": CLIENT_APP,
    }
    key = api_key(settings)
    if key:
        env["ANTHROPIC_API_KEY"] = key
    return env


def build_options(task: str, workspace: Path, tools: list, settings: dict, stderr: Callable[[str], None], resume: str | None = None):
    """ClaudeAgentOptions for the Opus lead with the workers and the toonforge tools."""
    from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, ToolAnnotations, create_sdk_mcp_server, tool

    annotations = ToolAnnotations(readOnlyHint=True, maxResultSizeChars=MAX_TOOL_RESULT_CHARS)
    sdk_tools = [tool(spec.name, spec.description, spec.input_schema, annotations=annotations)(spec.handler) for spec in tools]
    mcp_tool_names = [f"mcp__{MCP_SERVER_NAME}__{spec.name}" for spec in tools]
    workers = {name: AgentDefinition(**spec) for name, spec in agents.worker_agents(settings, mcp_tool_names).items()}
    options = {
        "model": settings["lead_model"],
        "system_prompt": {"type": "preset", "preset": "claude_code", "append": prompts.lead_system_prompt(task)},
        "cwd": str(workspace),
        "tools": list(BUILT_IN_TOOLS),
        "allowed_tools": list(DELEGATION_TOOLS) + mcp_tool_names,
        "permission_mode": "acceptEdits",
        "setting_sources": [],
        "agents": workers,
        "mcp_servers": {MCP_SERVER_NAME: create_sdk_mcp_server(name=MCP_SERVER_NAME, version="1.0.0", tools=sdk_tools)},
        "strict_mcp_config": True,
        "max_turns": settings["max_turns"],
        "max_budget_usd": settings["max_budget_usd"],
        "effort": settings["effort"],
        "env": claude_env(settings),
        "stderr": stderr,
        "forward_subagent_text": True,
        "max_buffer_size": MAX_SDK_BUFFER_BYTES,
    }
    if settings["cli_path"]:
        options["cli_path"] = settings["cli_path"]
    if resume:
        options["resume"] = resume
    return ClaudeAgentOptions(**options)


# ---------- the run ----------

def models_from_result(result, lead_model: str) -> list[str]:
    """Every model that worked on the run, the lead first."""
    models = [lead_model]
    for model in (getattr(result, "model_usage", None) or {}):
        if model not in models:
            models.append(model)
    return models


async def _consume(prompt: str, options, mapper: ActivityMapper, emit, should_cancel) -> None:
    stream = QUERY(prompt=prompt, options=options)
    try:
        async for message in stream:
            for who, kind, text in mapper.events_for(message):
                emit(who, kind, text)
            if should_cancel():
                break
    finally:
        close = getattr(stream, "aclose", None)
        if close is not None:
            await close()  # ends the Claude Code process


async def _run_async(prompt: str, options, workspace: Path, emit, should_cancel, lead_model: str, stderr_tail: deque) -> ClaudeRun:
    mapper = ActivityMapper(workspace, lead_model)
    consumer = asyncio.ensure_future(_consume(prompt, options, mapper, emit, should_cancel))
    while True:
        done, _ = await asyncio.wait({consumer}, timeout=CANCEL_POLL_SECONDS)
        if done:
            break
        if should_cancel():
            consumer.cancel()
            try:
                await consumer
            except BaseException:
                pass
            raise Cancelled()

    if should_cancel():
        raise Cancelled()

    result = mapper.result
    turns = result.num_turns if result is not None else 0
    cost = result.total_cost_usd if result is not None else None
    models = models_from_result(result, lead_model)
    session_id = getattr(result, "session_id", None)
    error = consumer.exception()
    if error is not None:
        message = error_for_exception(first_leaf_exception(error), mapper, list(stderr_tail))
        emit("lead", "result", message, cost_usd=cost)
        return ClaudeRun(ok=False, text=mapper.last_text, cost_usd=cost, turns=turns, error=message, models=models, session_id=session_id)
    if result is None:
        emit("lead", "result", NO_RESULT)
        return ClaudeRun(ok=False, text=mapper.last_text, cost_usd=None, turns=0, error=NO_RESULT, models=models)
    if result.subtype != "success" or result.is_error:
        message = result_error(mapper)
        emit("lead", "result", message, cost_usd=cost)
        return ClaudeRun(ok=False, text=result.result or "", cost_usd=cost, turns=turns, error=message, models=models, session_id=session_id)

    cost_text = f", ${cost:.2f}" if cost is not None else ""
    emit("lead", "result", f"Finished: {turns} turns{cost_text}", cost_usd=cost)
    return ClaudeRun(ok=True, text=result.result or mapper.last_text, cost_usd=cost, turns=turns, error=None, models=models, session_id=session_id)


def _run_in_new_loop(coroutine_factory) -> ClaudeRun:
    """asyncio.run, or on a fresh thread when this thread already runs an event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine_factory())
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coroutine_factory())).result()


def run_claude(task: str, prompt: str, workspace: Path, on_activity: Callable[[dict], None], should_cancel: Callable[[], bool],
               tools: list, resume: str | None = None) -> ClaudeRun:
    """One Claude Code session in `workspace`: the Opus lead, its workers and the toonforge tools.

    `task` is the task kind ("character", "character_revision", "background", "background_revision", "script",
    "direction"); it picks the lead's instructions (and, in fake mode, the fake that writes example files).
    Raises engine.errors.Cancelled when should_cancel() turns True; every other failure is a ClaudeRun with ok False.
    """
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    emit = make_emitter(workspace, on_activity)
    if fake_mode():
        from claude_layer.fakes import run_fake

        return run_fake(task, workspace, emit, should_cancel)
    if QUERY is None:
        emit("lead", "result", SDK_MISSING)
        return ClaudeRun(ok=False, text="", cost_usd=None, turns=0, error=SDK_MISSING)

    settings = claude_settings()
    stderr_tail: deque = deque(maxlen=STDERR_LINES_KEPT)
    stderr_log = workspace / "claude_stderr.log"

    def on_stderr(line: str) -> None:
        stderr_tail.append(line)
        try:
            with stderr_log.open("a", encoding="utf-8") as log:
                log.write(line.rstrip("\n") + "\n")
        except OSError:
            pass

    options = build_options(task, workspace, tools, settings, on_stderr, resume)
    emit("lead", "note", "Starting Claude: Opus leads, with Sonnet and Haiku workers")
    return _run_in_new_loop(lambda: _run_async(prompt, options, workspace, emit, should_cancel, settings["lead_model"], stderr_tail))


def describe_run(run: ClaudeRun) -> str:
    """One line for logs."""
    return json.dumps({"ok": run.ok, "turns": run.turns, "cost_usd": run.cost_usd, "error": run.error, "models": run.models})
