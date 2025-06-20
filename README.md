# benchling-mcp

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MCP (Model Context Protocol) server for Benchling platform integration

This server implements the Model Context Protocol (MCP) for Benchling, providing a standardized interface for accessing laboratory data management and research workflows. MCP enables AI assistants and agents to interact with Benchling's comprehensive biological data platform through structured interfaces.

The Benchling MCP server provides access to:

- **Entries**: Laboratory notebook entries and experimental records
- **Sequences**: DNA, RNA, and protein sequences with annotations
- **Projects**: Project organization and collaboration data
- **Search**: Comprehensive search across all Benchling entities

## About MCP (Model Context Protocol)

MCP is a protocol that bridges the gap between AI systems and specialized domain knowledge. It enables:

- **Structured Access**: Direct connection to Benchling's laboratory data
- **Natural Language Queries**: Simplified interaction with complex biological datasets
- **Type Safety**: Strong typing and validation through FastMCP
- **AI Integration**: Seamless integration with AI assistants and agents

## Prerequisites

You'll need:
- A Benchling account with API access
- Benchling API key
- Your Benchling domain (e.g., "yourcompany.benchling.com")

## Configuration

Set the following environment variables:

```bash
export BENCHLING_API_KEY="your_api_key_here"
export BENCHLING_DOMAIN="yourcompany.benchling.com"
```

## Available Tools

This server provides the following tools for interacting with Benchling:

1. **`benchling_get_entries(folder_id?, project_id?, limit?)`** - Get laboratory notebook entries
2. **`benchling_get_sequences(sequence_type?, folder_id?, limit?)`** - Get DNA/RNA/protein sequences
3. **`benchling_get_projects(limit?)`** - Get projects and their metadata
4. **`benchling_search(query, entity_types?, limit?)`** - Search across Benchling entities

## Available Resources

1. **`resource://benchling_api-info`** - Benchling API documentation and usage guidelines

## Quick Start

### Installing uv

```bash
# Download and install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
uvx --version
```

### Running with uvx

You can run the benchling-mcp server directly using uvx:

```bash
# Set environment variables
export BENCHLING_API_KEY="your_api_key_here"
export BENCHLING_DOMAIN="yourcompany.benchling.com"

# Run the server in streamable HTTP mode (default)
uvx benchling-mcp
```

<details>
<summary>Other uvx modes (STDIO, HTTP, SSE)</summary>

#### STDIO Mode (for MCP clients that require stdio)

```bash
# Or explicitly specify stdio mode
uvx benchling-mcp stdio
```

#### HTTP Mode (Web Server)
```bash
# Run the server in streamable HTTP mode on default (3001) port
uvx benchling-mcp server

# Run on a specific port
uvx benchling-mcp server --port 8000
```

#### SSE Mode (Server-Sent Events)
```bash
# Run the server in SSE mode
uvx benchling-mcp sse
```

</details>

## Configuration Files

For AI clients, create configuration files based on your preferred mode:

### STDIO Mode Configuration (mcp-config-stdio.json)
```json
{
  "mcpServers": {
    "benchling-mcp": {
      "command": "uvx",
      "args": ["benchling-mcp", "stdio"],
      "env": {
        "BENCHLING_API_KEY": "your_api_key_here",
        "BENCHLING_DOMAIN": "yourcompany.benchling.com"
      }
    }
  }
}
```

### HTTP Mode Configuration (mcp-config.json)
```json
{
  "mcpServers": {
    "benchling-mcp": {
      "command": "uvx",
      "args": ["benchling-mcp", "server"],
      "env": {
        "BENCHLING_API_KEY": "your_api_key_here",
        "BENCHLING_DOMAIN": "yourcompany.benchling.com"
      }
    }
  }
}
```

## Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/benchling-mcp.git
cd benchling-mcp

# Install dependencies
uv sync

# Set environment variables
export BENCHLING_API_KEY="your_api_key_here"
export BENCHLING_DOMAIN="yourcompany.benchling.com"
```

### Running the MCP Server (Development)

```bash
# Start the MCP server locally (HTTP mode)
uv run server

# Or start in STDIO mode  
uv run stdio

# Or start in SSE mode
uv run sse
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=benchling_mcp

# Run specific test file
uv run pytest test/test_benchling_mcp.py
```

## Usage Examples

### Getting Laboratory Entries
```python
# Get recent entries from a specific project
entries = await mcp.get_entries(project_id="proj_12345", limit=10)

# Get entries from a specific folder
entries = await mcp.get_entries(folder_id="lib_67890")
```

### Searching for Sequences
```python
# Get DNA sequences
dna_sequences = await mcp.get_sequences(sequence_type="dna", limit=20)

# Get protein sequences from a folder
proteins = await mcp.get_sequences(
    sequence_type="aa", 
    folder_id="lib_proteins", 
    limit=50
)
```

### Searching Across Benchling
```python
# Search for entries containing "CRISPR"
results = await mcp.search(
    query="CRISPR",
    entity_types=["entries"],
    limit=25
)

# Search for sequences with specific names
results = await mcp.search(
    query="GFP",
    entity_types=["dna_sequences", "aa_sequences"]
)
```

## API Reference

### Authentication
The server uses Benchling's API key authentication. The API key should be provided via the `BENCHLING_API_KEY` environment variable.

### Rate Limiting
Benchling has rate limits on API calls. The server implements appropriate delays and error handling for rate limit responses.

### Error Handling
All API calls are wrapped with proper error handling and logging using the `eliot` library.

## Integration with AI Systems

Simply point your AI client (like Cursor, Windsurf, ClaudeDesktop, VS Code with Copilot, or others) to use the appropriate configuration file.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## GitHub Actions CI/CD

This project includes automated testing via GitHub Actions that runs both unit tests and real integration tests against the Benchling API.

### Setting up GitHub Secrets

To enable the full integration tests in CI/CD, you need to add the following secrets to your GitHub repository:

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Add the following repository secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `BENCHLING_API_KEY` | Your Benchling API key | `sk_BWKVnUFsCDDO966aCCVJN6oAdfnee` |
| `BENCHLING_DOMAIN` | Your Benchling domain | `benchling.com` |

### CI/CD Workflow

The GitHub Actions workflow (`.github/workflows/test.yml`) will:

1. **Always run**: Unit tests that don't require API access
2. **Only if secrets are available**: 
   - Real integration tests using actual Benchling API
   - Run the example script to ensure it works end-to-end
3. **Clean up**: Remove any downloaded files after tests
4. **Upload artifacts**: Save logs if tests fail for debugging

### Manual Workflow Trigger

You can manually trigger the workflow from the GitHub Actions tab using the "Run workflow" button.

### Test Structure

- `test/test_benchling_mcp.py` - Unit tests with mocked dependencies
- `test/test_benchling_mcp_real.py` - Integration tests using real Benchling API
- Both test files include comprehensive assertions based on actual run_example.py output

The real integration tests serve as both:
- **Living documentation** with concrete examples of API responses
- **Regression tests** ensuring the MCP server works with actual Benchling data
