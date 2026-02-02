# Python Utilities

A workspace for Python utility scripts, managed with `uv`.

## One-Time Setup

Run these commands once to initialize the project.

```bash
# 1. Create the virtual environment
uv venv

# 2. Activate the environment (do this for every new shell session)
source .venv/bin/activate

# 3. Install dev tools and prepare the workspace
uv pip install -e ".[dev]"
```

## Common Commands

First, ensure your environment is active: `source .venv/bin/activate`

| Task | Command | Description |
| :--- | :--- | :--- |
| **Lint Code** | `ruff check .` | Finds errors & style issues. |
| **Format Code** | `ruff format .` | Automatically formats all code. |
| **Run Tests** | `pytest` | Runs all tests in the `packages/` directory. |
| **Run a Script** | `python -m my_tool.main` | Runs the `main.py` of a tool named `my_tool`. |

## How to Add/Update Dependencies

Dependencies belong to individual packages, not the entire workspace.

1.  **Declare:** Add the library (e.g., `"requests"`) to the `dependencies` list in the specific tool's `pyproject.toml` file (e.g., `packages/my-tool/pyproject.toml`).
2.  **Sync:** Update the virtual environment to match the new requirements.
    ```bash
    uv pip sync
    ```
This completes the project setup. You are ready to add your first tool to the `packages/` directory.
