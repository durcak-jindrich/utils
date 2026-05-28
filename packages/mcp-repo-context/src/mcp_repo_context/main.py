import os
import subprocess
from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from git import Repo, exc

# Initialize FastMCP server
# The name "Repo Context" will be displayed in MCP-compatible clients like Claude Desktop
mcp = FastMCP("Repo Context")

def get_repo_root() -> str:
    """Find the root of the git repository."""
    try:
        repo = Repo(os.getcwd(), search_parent_directories=True)
        return repo.working_tree_dir
    except exc.InvalidGitRepositoryError:
        return os.getcwd()

@mcp.tool()
def list_repo_structure(depth: int = 2, exclude_dirs: Optional[List[str]] = None) -> str:
    """
    Returns the file structure of the local repository.
    
    Args:
        depth: How deep to traverse the directory tree (default: 2).
        exclude_dirs: List of directory names to exclude (e.g., .git, .venv, node_modules).
    """
    root = get_repo_root()
    if exclude_dirs is None:
        exclude_dirs = [".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist", "node_modules"]
    
    output = []
    
    def traverse(current_path: str, current_depth: int):
        if current_depth > depth:
            return
        
        try:
            entries = sorted(os.listdir(current_path))
        except PermissionError:
            return

        for entry in entries:
            if entry in exclude_dirs:
                continue
            
            full_path = os.path.join(current_path, entry)
            rel_path = os.path.relpath(full_path, root)
            indent = "  " * (current_depth - 1)
            
            if os.path.isdir(full_path):
                output.append(f"{indent}├── {entry}/")
                traverse(full_path, current_depth + 1)
            else:
                output.append(f"{indent}└── {entry}")

    output.append(f"Repository Root: {root}")
    traverse(root, 1)
    return "\n".join(output)

@mcp.tool()
def get_recent_commits(count: int = 5) -> str:
    """
    Returns the most recent git commits in the repository.
    
    Args:
        count: Number of commits to retrieve (default: 5).
    """
    try:
        repo = Repo(get_repo_root())
        commits = list(repo.iter_commits(max_count=count))
        
        result = [f"Last {len(commits)} commits:"]
        for commit in commits:
            short_sha = commit.hexsha[:7]
            summary = commit.summary
            author = commit.author.name
            date = commit.authored_datetime.strftime("%Y-%m-%d %H:%M:%S")
            result.append(f"[{short_sha}] {summary} ({author}, {date})")
            
        return "\n".join(result)
    except Exception as e:
        return f"Error retrieving commits: {str(e)}"

@mcp.tool()
def get_todos() -> str:
    """
    Scans the repository for TODO and FIXME comments.
    """
    root = get_repo_root()
    # Using grep-like search via subprocess for efficiency
    try:
        # Search for TODO or FIXME (case-insensitive)
        # -r: recursive, -i: ignore case, -n: line number, -E: regex
        # Exclude common directories to avoid noise
        cmd = [
            "grep", "-r", "-i", "-n", "-E", "TODO|FIXME",
            "--exclude-dir=.git", "--exclude-dir=.venv", 
            "--exclude-dir=node_modules", "--exclude-dir=build",
            root
        ]
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            lines = process.stdout.splitlines()
            result = [f"Found {len(lines)} TODOs/FIXMEs:"]
            for line in lines:
                # Clean up the path to be relative to root
                rel_line = line.replace(root + "/", "")
                result.append(rel_line)
            return "\n".join(result)
        elif process.returncode == 1:
            return "No TODOs or FIXMEs found."
        else:
            return f"Error searching for TODOs: {process.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.resource("repo://summary")
def get_repo_summary() -> str:
    """
    Provides a high-level summary of the repository.
    """
    root = get_repo_root()
    structure = list_repo_structure(depth=1)
    commits = get_recent_commits(count=3)
    
    return f"""Repository Summary
Location: {root}

--- Structure ---
{structure}

--- Recent Activity ---
{commits}

--- MCP Concept ---
This Model Context Protocol (MCP) server allows your AI assistant to directly 
inspect your local repository. Instead of you copy-pasting file structures 
or commit histories, the AI can call these tools itself to gain context 
on-demand.
"""

@mcp.prompt()
def analyze_repo() -> str:
    """
    Creates a prompt for the AI to analyze the current repository status.
    """
    return "Please analyze the current state of this repository. Look at the file structure, recent commits, and any outstanding TODOs to give me a status report and suggest next steps."

def main():
    mcp.run()

if __name__ == "__main__":
    main()
