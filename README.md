# Heap Analyzer MCP Server

This repository is a Python-based MCP (Model Context Protocol) server exposing tools:

- analyze_thread_dump: Parses a JVM thread dump text file and returns a summary of thread states and potential deadlocks.
- compare_thread_dumps: Parses two JVM thread dump text files and returns a comparison of thread state counts and deadlocks.

## Prerequisites
- Python 3.9+

## Installation
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## Running the server (stdio)
The entrypoint for stdio-based MCP is the console script `heap-analyzer-mcp`.

```bash
heap-analyzer-mcp
```

Most MCP clients will spawn this binary and communicate over stdio.

---

## Example usage

You can try the tools against the sample thread dumps in tests/.

- Analyze a single dump (tool: analyze_thread_dump):
  - Arguments example (JSON):
    ```json
    { "path": "tests/sample_thread_dump.txt", "max_threads": 5000 }
    ```
  - Example response (truncated):
    ```json
    {
      "summary": "Analyzed 4 threads (limit 5000). States: RUNNABLE=2, WAITING=2",
      "counts": {"RUNNABLE":2, "WAITING":2, "BLOCKED":0, "TIMED_WAITING":0, "NEW":0, "TERMINATED":0},
      "deadlocks": [{"threads":["Thread-1","Thread-2"], "monitor":"..."}]
    }
    ```

- Compare two dumps (tool: compare_thread_dumps):
  - Arguments example (JSON):
    ```json
    {
      "path_a": "tests/sample_thread_dump.txt",
      "path_b": "tests/sample_thread_dump_2.txt",
      "diff_mode": "full",
      "max_threads": 5000
    }
    ```
  - Example response (truncated):
    ```json
    {
      "summary": "State deltas: no changes; Deadlocks present only in A",
      "counts_a": {"RUNNABLE":2, "WAITING":2, "BLOCKED":0, "TIMED_WAITING":0, "NEW":0, "TERMINATED":0},
      "counts_b": {"RUNNABLE":2, "WAITING":2, "BLOCKED":0, "TIMED_WAITING":0, "NEW":0, "TERMINATED":0},
      "deltas": {"RUNNABLE":0, "WAITING":0, "BLOCKED":0, "TIMED_WAITING":0, "NEW":0, "TERMINATED":0},
      "deadlocks_a": [{"threads":["Thread-1","Thread-2"]}],
      "deadlocks_b": [],
      "notes": "Deadlocks present only in A"
    }
    ```
  - diff_mode options:
    - summary: returns only {"summary", "notes"}
    - states: returns {"summary", "counts_a", "counts_b", "deltas"}
    - full: returns all fields

---

## MCP client configuration (mcp.json)

Many clients (e.g., Claude Desktop) support a per-server JSON config. Save a minimal mcp.json in your client’s config directory, or next to the project, like:

```json
{
  "name": "heap-analyzer-mcp",
  "command": "heap-analyzer-mcp",
  "args": [],
  "env": {},
  "timeout": 120000
}
```

If you prefer using Python directly without installing as a console script, you can point command to Python and run the module:

```json
{
  "name": "heap-analyzer-mcp",
  "command": "python",
  "args": ["-m", "heap_analyzer_mcp"],
  "env": {}
}
```

Notes:
- The server communicates over stdio, so no host/port is required.
- Files referenced in arguments (path, path_a, path_b) must be accessible by the server process.
- Files larger than 10MB are rejected for safety.

For Claude Desktop, see their docs for where to place mcp.json. A common pattern is adding entries under a top-level mcpServers config. Example snippet:

```json
{
  "mcpServers": {
    "heap-analyzer-mcp": {
      "command": "heap-analyzer-mcp",
      "args": []
    }
  }
}
```
```

---

## Testing
You can run tests in two ways:

1) Standard install with extras
```bash
pip install -e .[test]
pytest -q
```

2) Without installing external MCP dependencies (adapter-based)
If installing model-context-protocol is not feasible in your environment, you can still run the parser and MCP-tools adapter tests without installing the package:
```bash
PYTHONPATH=src python3 -m pytest -q
```
This uses src/heap_analyzer_mcp/tools_adapter.py to mirror the MCP tools' behavior without importing modelcontextprotocol.

---

## Project layout
- src/heap_analyzer_mcp/__main__.py   # server and tool implementations
- src/heap_analyzer_mcp/parser.py     # dependency-free parser used by tools and tests
- src/heap_analyzer_mcp/tools_adapter.py  # MCP tool behavior for tests without MCP runtime
- tests/                              # pytest-based tests and sample thread dumps

## Troubleshooting
- If your client can’t start the server, try running `heap-analyzer-mcp` from a terminal to verify it launches.
- On Windows, activate the virtual environment via `.venv\Scripts\activate` before launching your client.
- If the client reports missing package model-context-protocol, ensure you installed with `pip install -e .` inside an active venv.
- Large files: Thread dumps >10MB are rejected by design.
