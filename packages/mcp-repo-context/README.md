# MCP Repo Context Server

This is a minimal **Model Context Protocol (MCP)** server that exposes your local repository context to AI assistants.

## What is MCP?
MCP is an open standard that allows AI models (like Claude or Gemini) to safely connect to external data sources and tools. Instead of you manually copy-pasting code or status, the AI can "browse" your repository structure, see recent commits, and find TODOs on its own.

## Features
- **Tools**:
  - `list_repo_structure`: Explore files and directories.
  - `get_recent_commits`: See what has changed recently.
  - `get_todos`: Find outstanding tasks (TODO/FIXME).
- **Resources**:
  - `repo://summary`: A quick overview of the repository state.
- **Prompts**:
  - `analyze-repo`: A pre-configured prompt to get a full repo audit.

## Installation

This package is part of the `utils-workspace`. You can install it using `uv`:

```bash
# From the root of the workspace
uv sync
```

## Running the Server

To run the server locally:

```bash
uv run mcp-repo-context
```

## Testing with MCP Inspector

The best way to see it in action without a full AI client is the **MCP Inspector**:

```bash
npx @modelcontextprotocol/inspector uv run mcp-repo-context
```
This will open a web interface where you can call the tools manually.

## Integrating with Claude Desktop

To use this with Claude Desktop, add the following to your `claude_desktop_config.json` (usually located in `~/Library/Application Support/Claude/` on macOS):

```json
{
  "mcpServers": {
    "repo-context": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/your/projects/utils",
        "run",
        "mcp-repo-context"
      ]
    }
  }
}
```

Replace `/absolute/path/to/your/projects/utils` with the actual path to this repository.
