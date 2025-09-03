import json
import os
from dataclasses import dataclass
from typing import Dict, Optional

from .parser import parse_thread_dump


@dataclass
class Result:
    ok: bool
    text: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    @staticmethod
    def ok_text(payload: Dict) -> "Result":
        return Result(ok=True, text=json.dumps(payload))

    @staticmethod
    def err(code: str, message: str) -> "Result":
        return Result(ok=False, error_code=code, error_message=message)


# Mirrors analyze_thread_dump tool logic from __main__.py but without MCP types

def analyze_tool_call(path: str, max_threads: int = 5000) -> Result:
    if not isinstance(path, str) or not path:
        return Result.err("INVALID_PARAMS", "'path' must be a non-empty string")
    if not isinstance(max_threads, int) or max_threads <= 0:
        return Result.err("INVALID_PARAMS", "'max_threads' must be a positive integer")

    try:
        if not os.path.exists(path):
            return Result.err("INVALID_PARAMS", f"File not found: {path}")
        if os.path.isdir(path):
            return Result.err("INVALID_PARAMS", f"Path is a directory: {path}")
        if os.path.getsize(path) > 10 * 1024 * 1024:
            return Result.err("INTERNAL_ERROR", "File too large (>10MB)")

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        analysis = parse_thread_dump(text, max_threads=max_threads)
        payload = {
            "summary": analysis.summary,
            "counts": analysis.counts,
            "deadlocks": analysis.deadlocks,
        }
        return Result.ok_text(payload)
    except Exception as e:  # pragma: no cover - defensive parity
        return Result.err("INTERNAL_ERROR", f"Exception: {e}")


# Mirrors compare_thread_dumps tool logic from __main__.py but without MCP types

def compare_tool_call(
    path_a: str,
    path_b: str,
    max_threads: int = 5000,
    diff_mode: str = "full",
) -> Result:
    if not isinstance(path_a, str) or not path_a:
        return Result.err("INVALID_PARAMS", "'path_a' must be a non-empty string")
    if not isinstance(path_b, str) or not path_b:
        return Result.err("INVALID_PARAMS", "'path_b' must be a non-empty string")
    if not isinstance(max_threads, int) or max_threads <= 0:
        return Result.err("INVALID_PARAMS", "'max_threads' must be a positive integer")
    if diff_mode not in ("summary", "states", "full"):
        return Result.err("INVALID_PARAMS", "'diff_mode' must be one of: summary|states|full")

    try:
        for p in (path_a, path_b):
            if not os.path.exists(p):
                return Result.err("INVALID_PARAMS", f"File not found: {p}")
            if os.path.isdir(p):
                return Result.err("INVALID_PARAMS", f"Path is a directory: {p}")
            if os.path.getsize(p) > 10 * 1024 * 1024:
                return Result.err("INTERNAL_ERROR", f"File too large (>10MB): {p}")

        with open(path_a, "r", encoding="utf-8", errors="replace") as fa:
            text_a = fa.read()
        with open(path_b, "r", encoding="utf-8", errors="replace") as fb:
            text_b = fb.read()

        a = parse_thread_dump(text_a, max_threads=max_threads)
        b = parse_thread_dump(text_b, max_threads=max_threads)

        states = sorted(set(list(a.counts.keys()) + list(b.counts.keys())))
        deltas = {s: (b.counts.get(s, 0) - a.counts.get(s, 0)) for s in states}

        deadlock_note: Optional[str] = None
        if a.deadlocks and not b.deadlocks:
            deadlock_note = "Deadlocks present only in A"
        elif b.deadlocks and not a.deadlocks:
            deadlock_note = "Deadlocks present only in B"
        elif a.deadlocks and b.deadlocks:
            deadlock_note = "Deadlocks present in both"

        def make_summary() -> str:
            parts = []
            if diff_mode in ("summary", "full", "states"):
                changes = ", ".join(f"{s}={deltas[s]:+d}" for s in states if deltas[s] != 0) or "no changes"
                parts.append("State deltas: " + changes)
            if deadlock_note:
                parts.append(deadlock_note)
            return "; ".join(parts) if parts else "No notable differences"

        payload: Dict[str, object] = {
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
            payload = {
                "summary": payload["summary"],
                "counts_a": a.counts,
                "counts_b": b.counts,
                "deltas": deltas,
            }

        return Result.ok_text(payload)
    except Exception as e:  # pragma: no cover - defensive parity
        return Result.err("INTERNAL_ERROR", f"Exception: {e}")
