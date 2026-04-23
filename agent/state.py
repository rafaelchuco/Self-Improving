from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """Shared state for the Phase 0 graph."""

    workspace_path: str
    timestamp_utc: str
    repo_map: dict[str, Any]
    git_summary: dict[str, Any]
    notes: list[str]
    errors: list[str]
    runtime: dict[str, Any]
