from __future__ import annotations

from collections import Counter
from pathlib import Path


class FilesystemMCPAdapter:
    """Phase 0 local adapter that mimics Filesystem MCP capabilities."""

    KEY_FILES = {
        "package.json": "node",
        "pnpm-lock.yaml": "node",
        "yarn.lock": "node",
        "pom.xml": "java",
        "build.gradle": "java",
        "build.gradle.kts": "java",
        "requirements.txt": "python",
        "pyproject.toml": "python",
        "Pipfile": "python",
        "Dockerfile": "container",
        "docker-compose.yml": "container",
        "docker-compose.yaml": "container",
        "README.md": "docs",
        "README.MD": "docs",
    }

    EXTENSION_HINTS = {
        ".tsx": "react/typescript",
        ".jsx": "react/javascript",
        ".ts": "typescript",
        ".js": "javascript",
        ".py": "python",
        ".java": "java",
        ".kt": "kotlin",
        ".go": "go",
        ".rs": "rust",
    }

    IGNORED_DIRS = {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
    }

    IGNORED_SUFFIXES = {
        ".pyc",
    }

    def list_structure(
        self,
        workspace_path: str,
        *,
        max_depth: int = 4,
        max_entries: int = 1200,
    ) -> list[dict[str, str | int]]:
        root = Path(workspace_path).resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Workspace path does not exist: {workspace_path}")

        entries: list[dict[str, str | int]] = []

        def walk(current: Path, depth: int) -> None:
            if depth > max_depth or len(entries) >= max_entries:
                return

            for child in sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                if len(entries) >= max_entries:
                    return

                rel = child.relative_to(root).as_posix()
                if child.is_dir():
                    if child.name in self.IGNORED_DIRS:
                        continue
                    entries.append({"path": rel, "type": "dir", "depth": depth})
                    walk(child, depth + 1)
                else:
                    if child.suffix.lower() in self.IGNORED_SUFFIXES:
                        continue
                    entries.append({"path": rel, "type": "file", "depth": depth})

        walk(root, 0)
        return entries

    def detect_key_files(self, structure: list[dict[str, str | int]]) -> list[str]:
        key_files: list[str] = []
        for item in structure:
            if item["type"] != "file":
                continue
            path = str(item["path"])
            name = Path(path).name
            if name in self.KEY_FILES:
                key_files.append(path)
        return sorted(set(key_files))

    def detect_stack(self, structure: list[dict[str, str | int]], key_files: list[str]) -> list[str]:
        stacks: set[str] = set()

        for key_file in key_files:
            kind = self.KEY_FILES.get(Path(key_file).name)
            if kind == "node":
                stacks.add("Node.js")
            elif kind == "java":
                stacks.add("Java")
            elif kind == "python":
                stacks.add("Python")
            elif kind == "container":
                stacks.add("Containers")

        extension_counts = self.extension_stats(structure)
        for ext, count in extension_counts.items():
            if count == 0:
                continue
            hint = self.EXTENSION_HINTS.get(ext)
            if hint == "react/typescript":
                stacks.add("React")
                stacks.add("TypeScript")
            elif hint == "react/javascript":
                stacks.add("React")
                stacks.add("JavaScript")
            elif hint == "typescript":
                stacks.add("TypeScript")
            elif hint == "javascript":
                stacks.add("JavaScript")
            elif hint == "python":
                stacks.add("Python")
            elif hint == "java":
                stacks.add("Java")
            elif hint == "kotlin":
                stacks.add("Kotlin")
            elif hint == "go":
                stacks.add("Go")
            elif hint == "rust":
                stacks.add("Rust")

        if not stacks:
            stacks.add("Unknown")

        return sorted(stacks)

    def extension_stats(self, structure: list[dict[str, str | int]]) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for item in structure:
            if item["type"] != "file":
                continue
            path = str(item["path"])
            ext = Path(path).suffix.lower()
            if not ext:
                continue
            counter[ext] += 1

        return dict(sorted(counter.items(), key=lambda pair: pair[0]))

    def top_level_directories(self, structure: list[dict[str, str | int]]) -> list[str]:
        roots: set[str] = set()
        for item in structure:
            path = str(item["path"])
            parts = path.split("/")
            if parts and parts[0]:
                roots.add(parts[0])
        return sorted(roots)
