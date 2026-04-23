from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from agent.graph import execute_graph
from agent.state import AgentState


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 0 runner for Self-Improving Agent")
    parser.add_argument(
        "--workspace",
        required=True,
        help="Absolute or relative path to the workspace that will be analyzed.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write full JSON output. Default: logs/phase0_<timestamp>.json",
    )
    return parser.parse_args()


def default_output_path(timestamp: str) -> Path:
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / f"phase0_{timestamp}.json"


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        print(f"[error] Workspace path does not exist or is not a directory: {workspace}")
        return 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    initial_state: AgentState = {
        "workspace_path": str(workspace),
        "timestamp_utc": timestamp,
        "notes": [],
        "errors": [],
        "runtime": {"phase": "phase0"},
    }

    result = execute_graph(initial_state)

    output_path = Path(args.output).expanduser().resolve() if args.output else default_output_path(timestamp)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")

    print("[phase0] Analysis completed.")
    print(f"[phase0] Workspace: {workspace}")
    print(f"[phase0] Engine: {result.get('runtime', {}).get('engine', 'unknown')}")
    print(f"[phase0] Output: {output_path}")

    stack = result.get("repo_map", {}).get("stack", [])
    key_files = result.get("repo_map", {}).get("key_files", [])
    print(f"[phase0] Stack detected: {', '.join(stack) if stack else 'none'}")
    print(f"[phase0] Key files found: {len(key_files)}")

    errors = result.get("errors", [])
    if errors:
        print("[phase0] Errors:")
        for err in errors:
            print(f"  - {err}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
