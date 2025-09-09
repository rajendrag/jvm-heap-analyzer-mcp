# Heap Analyzer MCP Server

This repository provides a Python-based MCP (Model Context Protocol) server that exposes tools for analyzing JVM thread dumps:

- **analyze_thread_dump**: Parses a JVM thread dump text file and returns a summary of thread states and potential deadlocks.
- **compare_thread_dumps**: Parses two JVM thread dump text files and returns a comparison of thread state counts and deadlocks.

## Prerequisites
- Python 3.9+
- pip (Python package installer)

## Installation

### Option 1: Clone and Build from Source (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/rajendrag/HeapAnalyzer.git
   cd HeapAnalyzer
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Build the wheel**:
   ```bash
   pip install build
   python -m build
   ```

4. **Install the package**:
   ```bash
   pip install dist/heap_analyzer_mcp_server-0.1.0-py3-none-any.whl
   ```

### Option 2: Development Installation

For development or if you want to modify the code:

```bash
git clone https://github.com/rajendrag/HeapAnalyzer.git
cd HeapAnalyzer
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## Usage with MCP Clients

After installation, the server can be used with any MCP-compatible client. The console script `heap-analyzer-mcp-server` will be available in your PATH.

### Claude Desktop Configuration

1. **Locate your Claude Desktop config directory**:
   - **macOS**: `~/Library/Application Support/Claude/`
   - **Windows**: `%APPDATA%\Claude\`

2. **Create or edit the `claude_desktop_config.json` file**:
   ```json
   {
     "mcpServers": {
       "heap-analyzer-mcp": {
         "command": "heap-analyzer-mcp-server",
         "args": []
       }
     }
   }
   ```

3. **Restart Claude Desktop** to load the new server configuration.

### Generic MCP Client Configuration

For other MCP clients, use this configuration:

```json
{
  "name": "heap-analyzer-mcp",
  "command": "heap-analyzer-mcp-server",
  "args": [],
  "env": {},
  "timeout": 120000
}
```

### Alternative: Using Python Module Directly

If you prefer not to use the console script:

```json
{
  "name": "heap-analyzer-mcp",
  "command": "python",
  "args": ["-m", "heap_analyzer_mcp"],
  "env": {}
}
```

## Testing the Server

You can test the server manually to ensure it's working:

```bash
# Test that the server starts without errors
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}' | heap-analyzer-mcp-server

# Test import functionality
python -c "from heap_analyzer_mcp.__main__ import main; print('✅ Server is working!')"
```

## Available Tools

### 1. analyze_thread_dump

Analyzes a single JVM thread dump file.

**Parameters**:
- `path` (required): Path to the thread dump text file
- `max_threads` (optional): Maximum number of threads to analyze (default: 5000)

**Example usage in MCP client**:
```json
{
  "path": "/path/to/thread_dump.txt",
  "max_threads": 5000
}
```

**Example response**:
```json
{
  "summary": "Analyzed 4 threads (limit 5000). States: RUNNABLE=2, WAITING=2",
  "counts": {
    "RUNNABLE": 2,
    "WAITING": 2,
    "BLOCKED": 0,
    "TIMED_WAITING": 0,
    "NEW": 0,
    "TERMINATED": 0
  },
  "deadlocks": [
    {
      "threads": ["Thread-1", "Thread-2"],
      "monitor": "java.lang.Object@12345"
    }
  ]
}
```

### 2. compare_thread_dumps

Compares two JVM thread dump files and shows the differences.

**Parameters**:
- `path_a` (required): Path to the first thread dump file
- `path_b` (required): Path to the second thread dump file
- `max_threads` (optional): Maximum number of threads to analyze (default: 5000)
- `diff_mode` (optional): Level of detail in comparison (default: "full")
  - `"summary"`: Returns only summary and notes
  - `"states"`: Returns summary, counts, and deltas
  - `"full"`: Returns all fields including deadlock details

**Example usage in MCP client**:
```json
{
  "path_a": "/path/to/dump1.txt",
  "path_b": "/path/to/dump2.txt",
  "diff_mode": "full",
  "max_threads": 5000
}
```

**Example response**:
```json
{
  "summary": "State deltas: RUNNABLE=+1, WAITING=-1; Deadlocks present only in A",
  "counts_a": {"RUNNABLE": 2, "WAITING": 2, "BLOCKED": 0, "TIMED_WAITING": 0, "NEW": 0, "TERMINATED": 0},
  "counts_b": {"RUNNABLE": 3, "WAITING": 1, "BLOCKED": 0, "TIMED_WAITING": 0, "NEW": 0, "TERMINATED": 0},
  "deltas": {"RUNNABLE": 1, "WAITING": -1, "BLOCKED": 0, "TIMED_WAITING": 0, "NEW": 0, "TERMINATED": 0},
  "deadlocks_a": [{"threads": ["Thread-1", "Thread-2"], "monitor": "java.lang.Object@12345"}],
  "deadlocks_b": [],
  "notes": "Deadlocks present only in A"
}
```

## Sample Thread Dumps

The repository includes sample thread dumps in the `tests/` directory that you can use for testing:
- `tests/sample_thread_dump.txt`
- `tests/sample_thread_dump_2.txt`

## Development and Testing

### Running Tests

1. **Install test dependencies**:
   ```bash
   pip install -e .[test]
   ```

2. **Run tests**:
   ```bash
   pytest -q
   ```

### Alternative Testing (without MCP dependencies)

If you can't install MCP dependencies in your environment:

```bash
PYTHONPATH=src python3 -m pytest -q
```

This uses the tools adapter to test functionality without requiring the full MCP runtime.

## Project Structure

```
HeapAnalyzer/
├── src/heap_analyzer_mcp/
│   ├── __init__.py
│   ├── __main__.py           # MCP server and tool implementations
│   ├── parser.py             # Core thread dump parsing logic
│   └── tools_adapter.py      # MCP tool behavior for testing
├── tests/                    # Test files and sample thread dumps
├── pyproject.toml           # Package configuration
└── README.md               # This file
```

## Limitations and Notes

- **File size limit**: Thread dump files larger than 10MB are rejected for safety
- **File access**: Files must be accessible by the server process (consider file permissions)
- **Thread limit**: By default, analysis is limited to 5000 threads per dump
- **Communication**: The server uses stdio for communication with MCP clients

## Troubleshooting

### Server Won't Start
- Verify installation: `heap-analyzer-mcp-server --help`
- Check Python environment: `which python` and `which heap-analyzer-mcp-server`
- Try running directly: `python -m heap_analyzer_mcp`

### Client Can't Connect
- Ensure the server binary is in your PATH
- Verify the client configuration file syntax
- Check that the virtual environment is activated when starting the client
- Look at client logs for specific error messages

### Permission Issues
- Ensure thread dump files are readable by the server process
- On Windows, you may need to use full paths in the configuration

### Import Errors
- Verify all dependencies are installed: `pip list | grep mcp`
- Try reinstalling: `pip uninstall heap-analyzer-mcp-server && pip install dist/heap_analyzer_mcp_server-0.1.0-py3-none-any.whl`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

This project is open source. Please check the repository for license details.
