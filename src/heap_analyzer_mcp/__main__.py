import asyncio
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from heap_analyzer_mcp.parser import ThreadDumpAnalysis, parse_thread_dump
from modelcontextprotocol.server import Server
from modelcontextprotocol.transport.stdio import StdioServerTransport
from modelcontextprotocol.types import (
    CallToolResult,
    ErrorCode,
    JSONValue,
    TextContent,
    Tool,
    ToolInputSchema,
)


@dataclass
class ThreadDumpAnalysis:
    summary: str
    counts: Dict[str, int]
    deadlocks: List[Dict[str, JSONValue]]


def parse_thread_dump(text: str, max_threads: int = 5000) -> ThreadDumpAnalysis:
    import re

    thread_header_re = re.compile(r'^"(?P<name>.+?)"\s')
    state_re = re.compile(r'^\s*java\.lang\.Thread\.State:\s*(?P<state>[A-Z_]+)')

    counts: Dict[str, int] = {s: 0 for s in [
        "RUNNABLE", "BLOCKED", "WAITING", "TIMED_WAITING", "NEW", "TERMINATED"
    ]}
    total_threads = 0

    deadlocks: List[Dict[str, JSONValue]] = []

    lines = text.splitlines()
    i = 0
    while i < len(lines) and total_threads < max_threads:
        line = lines[i]
        m_header = thread_header_re.match(line)
        if m_header:
            total_threads += 1
            state = None
            for j in range(1, 6):
                if i + j >= len(lines):
                    break
                m_state = state_re.match(lines[i + j])
                if m_state:
                    state = m_state.group('state')
                    break
            if state and state in counts:
                counts[state] += 1
            i += 1
            continue
        if line.lower().startswith('found one java-level deadlock'):
            threads: List[str] = []
            monitor: Optional[str] = None
            for j in range(1, 50):
                if i + j >= len(lines):
                    break
                l2 = lines[i + j].strip()
                if not l2:
                    break
                if l2.startswith('"'):
                    t = l2.split('"')
                    if len(t) >= 3:
                        threads.append(t[1])
                if 'monitor' in l2.lower() or 'ownable synchronizer' in l2.lower():
                    monitor = l2
            if threads:
                deadlocks.append({"threads": threads, "monitor": monitor or "unknown"})
        i += 1

    analyzed_threads = sum(counts.values())
    summary = (
        f"Analyzed {analyzed_threads} threads (limit {max_threads}). "
        f"States: " + ", ".join(f"{k}={v}" for k, v in counts.items() if v)
    ) or "No threads parsed."

    return ThreadDumpAnalysis(summary=summary, counts=counts, deadlocks=deadlocks)


async def main_async() -> None:
    server = Server("heap-analyzer-mcp")

    analyze_tool = Tool(
        name="analyze_thread_dump",
        description=(
            "Parses a JVM thread dump text and returns a summary of thread states and potential deadlocks."
        ),
        input_schema=ToolInputSchema.json_schema({
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Path to thread dump text file"},
                "max_threads": {"type": "integer", "minimum": 1, "default": 5000},
            },
            "additionalProperties": False,
        }),
    )

    @server.tool(analyze_tool)
    async def analyze_thread_dump_tool(call) -> CallToolResult:
        try:
            path = call.arguments.get("path")
            if not isinstance(path, str) or not path:
                return CallToolResult.error(ErrorCode.INVALID_PARAMS, "'path' must be a non-empty string")
            max_threads = call.arguments.get("max_threads", 5000)
            if not isinstance(max_threads, int) or max_threads <= 0:
                return CallToolResult.error(ErrorCode.INVALID_PARAMS, "'max_threads' must be a positive integer")

            if not os.path.exists(path):
                return CallToolResult.error(ErrorCode.INVALID_PARAMS, f"File not found: {path}")
            if os.path.isdir(path):
                return CallToolResult.error(ErrorCode.INVALID_PARAMS, f"Path is a directory: {path}")

            if os.path.getsize(path) > 10 * 1024 * 1024:
                return CallToolResult.error(ErrorCode.INTERNAL_ERROR, "File too large (>10MB)")

            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()

            analysis = parse_thread_dump(text, max_threads=max_threads)

            payload: Dict[str, JSONValue] = {
                "summary": analysis.summary,
                "counts": analysis.counts,
                "deadlocks": analysis.deadlocks,
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(payload))]
            )
        except Exception as e:
            return CallToolResult.error(ErrorCode.INTERNAL_ERROR, f"Exception: {e}")

    compare_tool = Tool(
        name="compare_thread_dumps",
        description=(
            "Parses two JVM thread dump text files and returns a comparison of thread state counts and deadlocks."
        ),
        input_schema=ToolInputSchema.json_schema({
            "type": "object",
            "required": ["path_a", "path_b"],
            "properties": {
                "path_a": {"type": "string", "description": "Path to first thread dump text file"},
                "path_b": {"type": "string", "description": "Path to second thread dump text file"},
                "max_threads": {"type": "integer", "minimum": 1, "default": 5000},
                "diff_mode": {"type": "string", "enum": ["summary", "states", "full"], "default": "full"}
            },
            "additionalProperties": False,
        }),
    )

    @server.tool(compare_tool)
    async def compare_thread_dumps_tool(call) -> CallToolResult:
        try:
            path_a = call.arguments.get("path_a")
            path_b = call.arguments.get("path_b")
            max_threads = call.arguments.get("max_threads", 5000)
            diff_mode = call.arguments.get("diff_mode", "full")

            if not isinstance(path_a, str) or not path_a:
                return CallToolResult.error(ErrorCode.INVALID_PARAMS, "'path_a' must be a non-empty string")
            if not isinstance(path_b, str) or not path_b:
                return CallToolResult.error(ErrorCode.INVALID_PARAMS, "'path_b' must be a non-empty string")
            if not isinstance(max_threads, int) or max_threads <= 0:
                return CallToolResult.error(ErrorCode.INVALID_PARAMS, "'max_threads' must be a positive integer")
            if diff_mode not in ("summary", "states", "full"):
                return CallToolResult.error(ErrorCode.INVALID_PARAMS, "'diff_mode' must be one of: summary|states|full")

            for p in (path_a, path_b):
                if not os.path.exists(p):
                    return CallToolResult.error(ErrorCode.INVALID_PARAMS, f"File not found: {p}")
                if os.path.isdir(p):
                    return CallToolResult.error(ErrorCode.INVALID_PARAMS, f"Path is a directory: {p}")
                if os.path.getsize(p) > 10 * 1024 * 1024:
                    return CallToolResult.error(ErrorCode.INTERNAL_ERROR, f"File too large (>10MB): {p}")

            with open(path_a, 'r', encoding='utf-8', errors='replace') as fa:
                text_a = fa.read()
            with open(path_b, 'r', encoding='utf-8', errors='replace') as fb:
                text_b = fb.read()

            a = parse_thread_dump(text_a, max_threads=max_threads)
            b = parse_thread_dump(text_b, max_threads=max_threads)

            states = sorted(set(list(a.counts.keys()) + list(b.counts.keys())))
            deltas = {s: (b.counts.get(s, 0) - a.counts.get(s, 0)) for s in states}

            deadlock_note = None
            if a.deadlocks and not b.deadlocks:
                deadlock_note = "Deadlocks present only in A"
            elif b.deadlocks and not a.deadlocks:
                deadlock_note = "Deadlocks present only in B"
            elif a.deadlocks and b.deadlocks:
                deadlock_note = "Deadlocks present in both"

            def make_summary() -> str:
                parts = []
                if diff_mode in ("summary", "full", "states"):
                    parts.append("State deltas: " + ", ".join(f"{s}={deltas[s]:+d}" for s in states if deltas[s] != 0) or "no changes")
                if deadlock_note:
                    parts.append(deadlock_note)
                return "; ".join(parts) if parts else "No notable differences"

            payload: Dict[str, JSONValue] = {
                "summary": make_summary(),
                "counts_a": a.counts,
                "counts_b": b.counts,
                "deltas": deltas,
                "deadlocks_a": a.deadlocks,
                "deadlocks_b": b.deadlocks,
                "notes": deadlock_note or "",
            }

            if diff_mode == "summary":
                payload = {"summary": payload["summary"], "notes": payload["notes"]}
            elif diff_mode == "states":
                payload = {"summary": payload["summary"], "counts_a": a.counts, "counts_b": b.counts, "deltas": deltas}

            return CallToolResult(content=[TextContent(type="text", text=json.dumps(payload))])
        except Exception as e:
            return CallToolResult.error(ErrorCode.INTERNAL_ERROR, f"Exception: {e}")

    transport = StdioServerTransport()
    await server.run(transport)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
