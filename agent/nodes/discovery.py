from __future__ import annotations

from agent.adapters.filesystem_adapter import FilesystemMCPAdapter
from agent.adapters.git_adapter import GitMCPAdapter
from agent.state import AgentState


def run_discovery(state: AgentState) -> AgentState:
    workspace = state["workspace_path"]
    fs = FilesystemMCPAdapter()
    git = GitMCPAdapter(workspace)

    notes: list[str] = []
    errors: list[str] = list(state.get("errors", []))

    try:
        structure = fs.list_structure(workspace_path=workspace)
        key_files = fs.detect_key_files(structure)
        stack = fs.detect_stack(structure, key_files)
        extensions = fs.extension_stats(structure)
        top_level = fs.top_level_directories(structure)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"discovery_filesystem_error: {exc}")
        structure = []
        key_files = []
        stack = ["Unknown"]
        extensions = {}
        top_level = []

    is_repo = git.is_git_repo()
    if is_repo:
        branch = git.current_branch()
        recent_commits = git.recent_commits(limit=5)
        most_changed = git.most_changed_files(limit=10)
        notes.append("Git repository detected.")
    else:
        branch = "not-a-git-repo"
        recent_commits = []
        most_changed = []
        notes.append("Workspace is not a git repository.")

    repo_map = {
        "stack": stack,
        "key_files": key_files,
        "top_level_entries": top_level,
        "extension_stats": extensions,
        "structure_sample": structure[:250],
        "structure_total_entries": len(structure),
    }

    git_summary = {
        "is_git_repo": is_repo,
        "current_branch": branch,
        "recent_commits": recent_commits,
        "most_changed_files": most_changed,
    }

    return {
        "repo_map": repo_map,
        "git_summary": git_summary,
        "notes": list(state.get("notes", [])) + notes,
        "errors": errors,
    }
