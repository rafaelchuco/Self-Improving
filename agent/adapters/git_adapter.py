from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path


class GitMCPAdapter:
    """Phase 0 local adapter that mimics Git MCP capabilities."""

    def __init__(self, workspace_path: str) -> None:
        self.workspace_path = str(Path(workspace_path).resolve())

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", self.workspace_path, *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def is_git_repo(self) -> bool:
        result = self._run("rev-parse", "--is-inside-work-tree")
        return result.returncode == 0 and result.stdout.strip() == "true"

    def current_branch(self) -> str:
        result = self._run("branch", "--show-current")
        if result.returncode != 0:
            return "unknown"
        value = result.stdout.strip()
        return value if value else "detached"

    def recent_commits(self, limit: int = 5) -> list[dict[str, str]]:
        result = self._run(
            "log",
            f"--max-count={limit}",
            "--date=iso",
            "--pretty=format:%h|%an|%ad|%s",
        )
        if result.returncode != 0:
            return []

        commits: list[dict[str, str]] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("|", maxsplit=3)
            if len(parts) != 4:
                continue
            commits.append(
                {
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "subject": parts[3],
                }
            )
        return commits

    def most_changed_files(self, limit: int = 10, max_commits: int = 80) -> list[dict[str, int | str]]:
        result = self._run(
            "log",
            f"--max-count={max_commits}",
            "--name-only",
            "--pretty=format:",
        )
        if result.returncode != 0:
            return []

        counter: Counter[str] = Counter()
        for line in result.stdout.splitlines():
            path = line.strip()
            if not path:
                continue
            counter[path] += 1

        return [
            {"path": path, "changes": changes}
            for path, changes in counter.most_common(limit)
        ]
