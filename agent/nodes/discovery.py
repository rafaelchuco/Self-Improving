from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from agent.adapters.filesystem_adapter import FilesystemMCPAdapter
from agent.adapters.git_adapter import GitMCPAdapter
from agent.state import AgentState

SOURCE_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".go",
    ".rs",
}

TEST_NAME_PATTERN = re.compile(r"(test|spec)\.")
DOC_SUFFIXES = {".md", ".rst", ".txt"}

ROUTE_PATTERNS = [
    re.compile(r"path\s*=\s*[\"'](/[^\"']*)[\"']"),
    re.compile(r"path\s*:\s*[\"'](/[^\"']*)[\"']"),
    re.compile(r"(?:app|router)\.(?:get|post|put|patch|delete)\(\s*[\"'](/[^\"']*)[\"']"),
    re.compile(r"@(?:Get|Post|Put|Patch|Delete)Mapping\(\s*[\"'](/[^\"']*)[\"']"),
]


def _load_agent_config(workspace: Path) -> tuple[dict, str | None]:
    candidates = [
        workspace / "AGENT_CONFIG.yaml",
        workspace / "AGENT_CONFIG.yml",
        workspace / "config" / "AGENT_CONFIG.yaml",
        workspace / "config" / "AGENT_CONFIG.yml",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                return parsed, str(path)
        except Exception:  # noqa: BLE001
            continue
    return {}, None


def _read_text(path: Path, max_chars: int = 200_000) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")
    return content[:max_chars]


def _extract_routes(text: str) -> set[str]:
    routes: set[str] = set()
    for pattern in ROUTE_PATTERNS:
        for match in pattern.findall(text):
            candidate = match.strip()
            if not candidate.startswith("/"):
                continue
            if len(candidate) > 120:
                continue
            routes.add(candidate)
    return routes


def _relative_module(path: str) -> str:
    parts = path.split("/")
    if len(parts) <= 1:
        return "root"
    return parts[0]


def _build_opportunities(repo_map: dict, git_summary: dict) -> list[dict[str, str]]:
    opportunities: list[dict[str, str]] = []

    tests_found = int(repo_map.get("tests_found", 0))
    if tests_found == 0:
        opportunities.append(
            {
                "level": "L2",
                "title": "Crear base de tests automatizados",
                "evidence": "No se detectaron archivos de tests en el repositorio.",
            }
        )

    largest_files = repo_map.get("hotspots", {}).get("largest_files", [])
    if largest_files:
        top_file = largest_files[0]
        lines = int(top_file.get("lines", 0))
        if lines >= 250:
            opportunities.append(
                {
                    "level": "L3",
                    "title": "Refactorizar archivo de alta complejidad",
                    "evidence": f"{top_file.get('path')} tiene {lines} lineas.",
                }
            )

    docs_summary = repo_map.get("docs", {})
    if not docs_summary.get("has_root_readme", False):
        opportunities.append(
            {
                "level": "L1",
                "title": "Generar README base del proyecto",
                "evidence": "No existe README.md en la raiz del workspace.",
            }
        )

    most_changed = git_summary.get("most_changed_files", [])
    if most_changed:
        hot = most_changed[0]
        opportunities.append(
            {
                "level": "L2",
                "title": "Agregar cobertura sobre zona de alta rotacion",
                "evidence": f"{hot.get('path')} aparece como archivo de alta frecuencia de cambios.",
            }
        )

    if not repo_map.get("routes"):
        opportunities.append(
            {
                "level": "L1",
                "title": "Documentar rutas y flujos principales",
                "evidence": "No se detectaron rutas explicitas con heuristicas actuales.",
            }
        )

    for contradiction in repo_map.get("contradictions", []):
        opportunities.append(
            {
                "level": "L1",
                "title": "Alinear AGENT_CONFIG con evidencia del repositorio",
                "evidence": str(contradiction),
            }
        )

    present_levels = {str(item.get("level", "")) for item in opportunities}
    if "L1" not in present_levels:
        opportunities.append(
            {
                "level": "L1",
                "title": "Documentar convenciones base del proyecto",
                "evidence": "No se detectaron oportunidades L1 explicitas con heuristicas actuales.",
            }
        )
    if "L2" not in present_levels:
        opportunities.append(
            {
                "level": "L2",
                "title": "Agregar validacion automatizada de regresion",
                "evidence": "No se detectaron oportunidades L2 explicitas con heuristicas actuales.",
            }
        )

    while len(opportunities) < 3:
        opportunities.append(
            {
                "level": "L1",
                "title": "Revisar estandar de documentacion interna",
                "evidence": "Se recomienda normalizar convenciones para acelerar mejoras futuras.",
            }
        )

    return opportunities[:6]


def _detect_config_contradictions(config: dict, repo_map: dict) -> list[str]:
    if not isinstance(config, dict):
        return []

    project_cfg = config.get("project", {}) if isinstance(config.get("project", {}), dict) else {}
    app_cfg = config.get("app", {}) if isinstance(config.get("app", {}), dict) else {}

    project_type = str(project_cfg.get("type", "")).strip().lower()
    start_command = str(app_cfg.get("start_command", "")).strip().lower()

    detected_stack = {str(item).strip().lower() for item in repo_map.get("stack", [])}
    key_file_names = {Path(str(path)).name.lower() for path in repo_map.get("key_files", [])}

    node_evidence = bool(
        {"node.js", "javascript", "typescript", "react"} & detected_stack
        or "package.json" in key_file_names
    )
    python_evidence = bool(
        "python" in detected_stack
        or "requirements.txt" in key_file_names
        or "pyproject.toml" in key_file_names
    )

    contradictions: list[str] = []
    if project_type == "frontend" and not node_evidence:
        contradictions.append(
            "project.type=frontend, pero no se encontro evidencia Node/JavaScript en el repositorio."
        )

    if start_command.startswith(("npm ", "pnpm ", "yarn ")) and not node_evidence:
        contradictions.append(
            "app.start_command usa npm/pnpm/yarn, pero no se detecto package.json ni stack Node.js."
        )

    if start_command.startswith(("python ", "python3 ")) and not python_evidence:
        contradictions.append(
            "app.start_command usa Python, pero no se detecto evidencia de stack Python."
        )

    return contradictions


def run_discovery(state: AgentState) -> AgentState:
    workspace = state["workspace_path"]
    fs = FilesystemMCPAdapter()
    git = GitMCPAdapter(workspace)
    workspace_path = Path(workspace)

    notes: list[str] = []
    errors: list[str] = list(state.get("errors", []))
    runtime = dict(state.get("runtime", {}))

    try:
        structure = fs.list_structure(workspace_path=workspace)
        key_files = fs.detect_key_files(structure)
        stack = fs.detect_stack(structure, key_files)
        extensions = fs.extension_stats(structure)
        top_level = fs.top_level_directories(structure)

        source_files = [
            str(item["path"])
            for item in structure
            if item["type"] == "file" and Path(str(item["path"])).suffix.lower() in SOURCE_SUFFIXES
        ]
        test_files = [
            path
            for path in source_files
            if TEST_NAME_PATTERN.search(Path(path).name.lower()) or "/tests/" in f"/{path}/" or path.startswith("tests/")
        ]

        docs_files = [
            str(item["path"])
            for item in structure
            if item["type"] == "file" and Path(str(item["path"])).suffix.lower() in DOC_SUFFIXES
        ]

        route_set: set[str] = set()
        largest_files: list[dict[str, int | str]] = []
        module_stats: dict[str, dict[str, int]] = {}

        max_scan_files = 800
        scanned_paths = source_files[:max_scan_files]
        if len(source_files) > max_scan_files:
            notes.append(f"Source scan truncated to first {max_scan_files} files.")

        for rel_path in scanned_paths:
            abs_path = workspace_path / rel_path
            try:
                content = _read_text(abs_path)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"discovery_read_error:{rel_path}:{exc}")
                continue

            lines = content.count("\n") + 1 if content else 0
            module_name = _relative_module(rel_path)
            stats = module_stats.setdefault(module_name, {"source_files": 0, "lines": 0})
            stats["source_files"] += 1
            stats["lines"] += lines

            largest_files.append({"path": rel_path, "lines": lines})
            route_set.update(_extract_routes(content))

        modules = [
            {
                "module": module,
                "source_files": values["source_files"],
                "lines": values["lines"],
            }
            for module, values in module_stats.items()
        ]
        modules.sort(key=lambda item: (-int(item["source_files"]), str(item["module"])))

        largest_files.sort(key=lambda item: int(item["lines"]), reverse=True)

        docs_summary = {
            "has_root_readme": (workspace_path / "README.md").exists(),
            "docs_files": docs_files[:80],
            "docs_file_count": len(docs_files),
        }
    except Exception as exc:  # noqa: BLE001
        errors.append(f"discovery_filesystem_error: {exc}")
        structure = []
        key_files = []
        stack = ["Unknown"]
        extensions = {}
        top_level = []
        source_files = []
        test_files = []
        docs_summary = {"has_root_readme": False, "docs_files": [], "docs_file_count": 0}
        modules = []
        route_set = set()
        largest_files = []

    config, config_path = _load_agent_config(workspace_path)
    if config_path:
        notes.append(f"Agent config detected at {config_path}.")
    else:
        notes.append("No AGENT_CONFIG found in workspace.")

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

    hotspots = {
        "largest_files": largest_files[:8],
        "most_changed_files": most_changed[:8],
    }

    routes = sorted(route_set)[:150]

    repo_map = {
        "stack": stack,
        "key_files": key_files,
        "top_level_entries": top_level,
        "extension_stats": extensions,
        "source_files": len(source_files),
        "tests_found": len(test_files),
        "test_files": test_files[:100],
        "routes": routes,
        "modules": modules,
        "docs": docs_summary,
        "hotspots": hotspots,
        "structure_sample": structure[:250],
        "structure_total_entries": len(structure),
    }

    contradictions = _detect_config_contradictions(config, repo_map)
    if contradictions:
        repo_map["contradictions"] = contradictions
        notes.append(f"Config contradictions detected: {len(contradictions)}")
        for contradiction in contradictions[:5]:
            notes.append(f"config_contradiction: {contradiction}")

    opportunities = _build_opportunities(repo_map=repo_map, git_summary={"most_changed_files": most_changed})

    git_summary = {
        "is_git_repo": is_repo,
        "current_branch": branch,
        "recent_commits": recent_commits,
        "most_changed_files": most_changed,
    }

    current_phase = str(runtime.get("phase", "phase0"))
    runtime["phase"] = current_phase
    runtime["discovery_version"] = current_phase

    if config:
        config_preview = {
            "project": config.get("project", {}),
            "app": {
                "local_url": config.get("app", {}).get("local_url"),
                "start_command": config.get("app", {}).get("start_command"),
            },
        }
        notes.append(f"Config preview: {json.dumps(config_preview, ensure_ascii=True)}")

    return {
        "config": config,
        "repo_map": repo_map,
        "git_summary": git_summary,
        "opportunities": opportunities,
        "notes": list(state.get("notes", [])) + notes,
        "errors": errors,
        "runtime": runtime,
    }
