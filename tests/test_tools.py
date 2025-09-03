from pathlib import Path

from heap_analyzer_mcp.parser import parse_thread_dump

BASE_DIR = Path(__file__).parent


def test_analyze_thread_dump_parsing_counts_and_deadlocks():
    text = (BASE_DIR / "sample_thread_dump.txt").read_text(encoding="utf-8")
    analysis = parse_thread_dump(text)

    assert analysis.counts["RUNNABLE"] == 2
    assert analysis.counts["WAITING"] == 2
    assert analysis.counts["BLOCKED"] == 0
    assert analysis.counts["TIMED_WAITING"] == 0
    assert analysis.counts["NEW"] == 0
    assert analysis.counts["TERMINATED"] == 0

    assert len(analysis.deadlocks) >= 1
    threads = analysis.deadlocks[0]["threads"]
    assert set(threads) == {"Thread-1", "Thread-2"}

def test_compare_thread_dumps_deltas():
    text_a = (BASE_DIR / "sample_thread_dump.txt").read_text(encoding="utf-8")
    text_b = (BASE_DIR / "sample_thread_dump_2.txt").read_text(encoding="utf-8")

    a = parse_thread_dump(text_a)
    b = parse_thread_dump(text_b)

    states = sorted(set(list(a.counts.keys()) + list(b.counts.keys())))
    deltas = {s: (b.counts.get(s, 0) - a.counts.get(s, 0)) for s in states}

    assert deltas["RUNNABLE"] == 0
    assert deltas["WAITING"] == 0

    assert len(a.deadlocks) >= 1
    assert len(b.deadlocks) == 0
