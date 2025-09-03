from dataclasses import dataclass
from typing import Dict, List, Optional

# This module intentionally has no external dependencies so it can be used in tests
# without requiring the MCP runtime libraries.

@dataclass
class ThreadDumpAnalysis:
    summary: str
    counts: Dict[str, int]
    deadlocks: List[Dict[str, object]]


def parse_thread_dump(text: str, max_threads: int = 5000) -> ThreadDumpAnalysis:
    import re

    thread_header_re = re.compile(r'^"(?P<name>.+?)"\s')
    state_re = re.compile(r'^\s*java\.lang\.Thread\.State:\s*(?P<state>[A-Z_]+)')

    counts: Dict[str, int] = {s: 0 for s in [
        "RUNNABLE", "BLOCKED", "WAITING", "TIMED_WAITING", "NEW", "TERMINATED"
    ]}
    total_threads = 0

    deadlocks: List[Dict[str, object]] = []

    lines = text.splitlines()
    i = 0
    while i < len(lines) and total_threads < max_threads:
        line = lines[i]
        m_header = thread_header_re.match(line)
        if m_header:
            total_threads += 1
            state: Optional[str] = None
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
