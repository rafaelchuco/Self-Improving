from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """Shared state for the Phase 0/1/2 graph."""

    workspace_path: str
    timestamp_utc: str
    config: dict[str, Any]
    repo_map: dict[str, Any]
    perception_map: dict[str, Any]
    git_summary: dict[str, Any]
    opportunities: list[dict[str, Any]]
    generated_artifacts: dict[str, str]
    notes: list[str]
    errors: list[str]
    runtime: dict[str, Any]
