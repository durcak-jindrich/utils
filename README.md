# Python Utilities

A workspace for Python utility scripts, managed with `uv`.

## One-Time Setup

Run these commands once to initialize the project and install all workspace members.

```bash
# 1. Create the virtual environment
uv venv

# 2. Sync the workspace (installs all dependencies for all packages)
uv sync

# 3. Activate the environment (optional, but recommended for development)
source .venv/bin/activate
```

## Running Tools with Local .env Files

To ensure that each tool finds its own `.env` file, use the `--directory` (or `-C`) flag to set the working directory to the package folder.

### 1. Local-RAG
```bash
uv run --directory packages/local-rag local-rag ingest /path/to/docs
uv run --directory packages/local-rag local-rag query "My question"
```

### 2. Action Item Extractor
```bash
uv run --directory packages/action-item-extractor action-item-extractor
```

### 3. MCP Repo Context
```bash
uv run --directory packages/mcp-repo-context mcp-repo-context
```

## Common Commands (Workspace-wide)

| Task | Command | Description |
| :--- | :--- | :--- |
| **Lint Code** | `uv run ruff check .` | Finds errors & style issues. |
| **Format Code** | `uv run ruff format .` | Automatically formats all code. |
| **Run Tests** | `uv run pytest` | Runs all tests in the `packages/` directory. |

## How to Add/Update Dependencies

Dependencies belong to individual packages, not the entire workspace.

1.  **Declare:** Add the library to the `dependencies` list in the specific tool's `pyproject.toml`.
2.  **Sync:** Update the root virtual environment: `uv sync`.
