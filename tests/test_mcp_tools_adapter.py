from pathlib import Path
import json

from heap_analyzer_mcp.tools_adapter import (
    analyze_tool_call,
    compare_tool_call,
)

BASE_DIR = Path(__file__).parent


def test_analyze_adapter_happy_path():
    path = str(BASE_DIR / "sample_thread_dump.txt")
    result = analyze_tool_call(path)
    assert result.ok, f"expected ok result, got error {result.error_code}: {result.error_message}"

    payload = json.loads(result.text or "{}")
    counts = payload["counts"]
    assert counts["RUNNABLE"] == 2
    assert counts["WAITING"] == 2
    assert counts["BLOCKED"] == 0
    assert counts["TIMED_WAITING"] == 0
    assert counts["NEW"] == 0
    assert counts["TERMINATED"] == 0

    deadlocks = payload["deadlocks"]
    assert len(deadlocks) >= 1
    threads = set(deadlocks[0]["threads"])  # type: ignore[index]
    assert threads == {"Thread-1", "Thread-2"}


def test_compare_adapter_happy_modes():
    path_a = str(BASE_DIR / "sample_thread_dump.txt")
    path_b = str(BASE_DIR / "sample_thread_dump_2.txt")

    # full mode
    res_full = compare_tool_call(path_a, path_b, diff_mode="full")
    assert res_full.ok, f"full mode failed: {res_full.error_code} {res_full.error_message}"
    payload_full = json.loads(res_full.text or "{}")
    assert payload_full["deltas"]["RUNNABLE"] == 0
    assert payload_full["deltas"]["WAITING"] == 0
    assert payload_full["notes"] == "Deadlocks present only in A"

    # states mode
    res_states = compare_tool_call(path_a, path_b, diff_mode="states")
    assert res_states.ok, f"states mode failed: {res_states.error_code} {res_states.error_message}"
    payload_states = json.loads(res_states.text or "{}")
    assert payload_states["deltas"]["RUNNABLE"] == 0
    assert payload_states["deltas"]["WAITING"] == 0
    assert "counts_a" in payload_states and "counts_b" in payload_states

    # summary mode
    res_summary = compare_tool_call(path_a, path_b, diff_mode="summary")
    assert res_summary.ok, f"summary mode failed: {res_summary.error_code} {res_summary.error_message}"
    payload_summary = json.loads(res_summary.text or "{}")
    assert set(payload_summary.keys()) == {"summary", "notes"}


def test_analyze_adapter_missing_file_error():
    result = analyze_tool_call("/path/that/does/not/exist.txt")
    assert not result.ok
    assert result.error_code == "INVALID_PARAMS"


def test_compare_adapter_invalid_mode_and_missing_file():
    path_a = str(BASE_DIR / "sample_thread_dump.txt")
    path_b = str(BASE_DIR / "sample_thread_dump_2.txt")

    # invalid diff_mode
    bad_mode = compare_tool_call(path_a, path_b, diff_mode="invalid")
    assert not bad_mode.ok and bad_mode.error_code == "INVALID_PARAMS"

    # missing path_b
    missing = compare_tool_call(path_a, "/definitely/missing.txt")
    assert not missing.ok and missing.error_code == "INVALID_PARAMS"


def test_analyze_adapter_invalid_max_threads():
    path = str(BASE_DIR / "sample_thread_dump.txt")
    res = analyze_tool_call(path, max_threads=0)
    assert not res.ok and res.error_code == "INVALID_PARAMS"
