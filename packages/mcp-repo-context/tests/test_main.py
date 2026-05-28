import os
import pytest
from mcp_repo_context.main import list_repo_structure, get_recent_commits, get_todos

def test_list_repo_structure():
    # Test that it returns something and contains the current package
    structure = list_repo_structure(depth=2)
    assert "Repository Root:" in structure
    assert "packages/" in structure
    assert "mcp-repo-context/" in structure

def test_get_recent_commits():
    # Test that it can fetch at least one commit from this repo
    commits = get_recent_commits(count=1)
    assert "Last 1 commits:" in commits
    # Check for typical git hash pattern or message
    assert "[" in commits and "]" in commits

def test_get_todos():
    # We know we don't have many TODOs, but let's check it doesn't crash
    # and returns a string
    todos = get_todos()
    assert isinstance(todos, str)
    # If there are no TODOs, it should say so
    if "Found" not in todos:
        assert "No TODOs or FIXMEs found." in todos
