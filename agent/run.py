from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

if __package__ in (None, ""):
    # Allow running this file directly: python agent/run.py ...
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.graph import execute_graph
from agent.state import AgentState


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase runner for Self-Improving Agent")
    parser.add_argument(
        "--workspace",
        required=True,
        help="Absolute or relative path to the workspace that will be analyzed.",
    )
    parser.add_argument(
        "--phase",
        choices=["phase0", "phase1", "phase2"],
        default="phase1",
        help="Execution phase. phase0=discovery only, phase1=discovery+generation, phase2=discovery+perception+generation.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write full JSON output. Default: logs/<phase>_<timestamp>.json",
    )
    return parser.parse_args()


def default_output_path(phase: str, timestamp: str) -> Path:
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / f"{phase}_{timestamp}.json"


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
        "runtime": {"phase": args.phase},
    }

    result = execute_graph(initial_state)

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else default_output_path(args.phase, timestamp)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")

    phase = str(result.get("runtime", {}).get("phase", args.phase))
    print(f"[{phase}] Analysis completed.")
    print(f"[{phase}] Workspace: {workspace}")
    print(f"[{phase}] Engine: {result.get('runtime', {}).get('engine', 'unknown')}")
    print(f"[{phase}] Output: {output_path}")

    stack = result.get("repo_map", {}).get("stack", [])
    key_files = result.get("repo_map", {}).get("key_files", [])
    tests_found = result.get("repo_map", {}).get("tests_found", 0)
    opportunities = result.get("opportunities", [])
    print(f"[{phase}] Stack detected: {', '.join(stack) if stack else 'none'}")
    print(f"[{phase}] Key files found: {len(key_files)}")
    print(f"[{phase}] Tests found: {tests_found}")
    print(f"[{phase}] Opportunities identified: {len(opportunities)}")

    perception = result.get("perception_map", {})
    if perception:
        screens = perception.get("screens", [])
        flows = perception.get("flows", [])
        issues = perception.get("ui_issues", [])
        print(f"[{phase}] Screens mapped: {len(screens)}")
        print(f"[{phase}] Flows detected: {len(flows)}")
        print(f"[{phase}] UI issues detected: {len(issues)}")

    generated = result.get("generated_artifacts", {})
    if generated:
        print(f"[{phase}] Generated artifacts:")
        for key, value in generated.items():
            print(f"  - {key}: {value}")

    errors = result.get("errors", [])
    if errors:
        print(f"[{phase}] Errors:")
        for err in errors:
            print(f"  - {err}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
