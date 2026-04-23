from __future__ import annotations

from pathlib import Path

from agent.state import AgentState


def _write_with_backup(path: Path, content: str, timestamp: str) -> str | None:
    backup_path: str | None = None
    if path.exists():
        backup_dir = path.parent / ".agent_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_name = f"{path.stem}.{timestamp}.bak{path.suffix}"
        backup_target = backup_dir / backup_name
        backup_target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        backup_path = str(backup_target)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return backup_path


def _render_readme(state: AgentState) -> str:
    workspace = Path(state["workspace_path"])
    config = state.get("config", {})
    repo_map = state.get("repo_map", {})
    git_summary = state.get("git_summary", {})
    opportunities = state.get("opportunities", [])
    timestamp = state.get("timestamp_utc", "unknown")

    project_name = (
        config.get("project", {}).get("name")
        if isinstance(config, dict)
        else None
    ) or workspace.name
    project_type = config.get("project", {}).get("type", "unknown") if isinstance(config, dict) else "unknown"
    start_command = config.get("app", {}).get("start_command") if isinstance(config, dict) else None

    stack = repo_map.get("stack", [])
    top_level = repo_map.get("top_level_entries", [])
    modules = repo_map.get("modules", [])
    routes = repo_map.get("routes", [])
    test_files = repo_map.get("test_files", [])
    hotspots = repo_map.get("hotspots", {}).get("largest_files", [])

    lines: list[str] = []
    lines.append(f"# {project_name}")
    lines.append("")
    lines.append("README generado automaticamente por Self-Improving Agent (Fase 1).")
    lines.append("")
    lines.append("## Contexto")
    lines.append("")
    lines.append(f"- Tipo de proyecto detectado: **{project_type}**")
    lines.append(f"- Stack detectado: **{', '.join(stack) if stack else 'Unknown'}**")
    lines.append(f"- Branch actual: **{git_summary.get('current_branch', 'unknown')}**")
    lines.append(f"- Analisis generado en UTC: **{timestamp}**")
    lines.append("")
    lines.append("## Ejecucion")
    lines.append("")
    lines.append("```bash")
    lines.append("# Crear entorno")
    lines.append("python3 -m venv .venv")
    lines.append("source .venv/bin/activate")
    lines.append("pip install -r requirements.txt")
    if start_command:
        lines.append("")
        lines.append("# Comando sugerido por AGENT_CONFIG")
        lines.append(start_command)
    lines.append("```")
    lines.append("")
    lines.append("## Estructura principal")
    lines.append("")
    for item in top_level[:20]:
        lines.append(f"- `{item}`")
    if not top_level:
        lines.append("- No se detectaron entradas en el nivel raiz.")
    lines.append("")
    lines.append("## Modulos detectados")
    lines.append("")
    if modules:
        lines.append("| Modulo | Archivos fuente | Lineas aproximadas |")
        lines.append("| --- | ---: | ---: |")
        for module in modules[:12]:
            lines.append(
                f"| {module.get('module')} | {module.get('source_files', 0)} | {module.get('lines', 0)} |"
            )
    else:
        lines.append("No se detectaron modulos de codigo fuente.")
    lines.append("")
    lines.append("## Rutas detectadas")
    lines.append("")
    if routes:
        for route in routes[:30]:
            lines.append(f"- `{route}`")
    else:
        lines.append("- No se detectaron rutas explicitas con las heuristicas actuales.")
    lines.append("")
    lines.append("## Estado de tests")
    lines.append("")
    lines.append(f"- Tests encontrados: **{repo_map.get('tests_found', 0)}**")
    if test_files:
        for test_file in test_files[:20]:
            lines.append(f"- `{test_file}`")
    lines.append("")
    lines.append("## Hotspots tecnicos")
    lines.append("")
    if hotspots:
        for hotspot in hotspots[:8]:
            lines.append(f"- `{hotspot.get('path')}` ({hotspot.get('lines', 0)} lineas)")
    else:
        lines.append("- No se detectaron hotspots por tamano de archivo.")
    lines.append("")
    lines.append("## Oportunidades iniciales")
    lines.append("")
    for opportunity in opportunities[:8]:
        lines.append(
            f"- [{opportunity.get('level', 'L1')}] {opportunity.get('title', 'Sin titulo')} -> {opportunity.get('evidence', 'Sin evidencia')}"
        )
    if not opportunities:
        lines.append("- No se detectaron oportunidades iniciales.")
    lines.append("")
    lines.append("## Trazabilidad")
    lines.append("")
    lines.append("Este documento se genero automaticamente desde el analisis del repositorio (Fase 1).")

    return "\n".join(lines) + "\n"


def _render_architecture(state: AgentState) -> str:
    repo_map = state.get("repo_map", {})
    modules = repo_map.get("modules", [])
    routes = repo_map.get("routes", [])
    stack = repo_map.get("stack", [])

    lines: list[str] = []
    lines.append("# Arquitectura (Generada automaticamente)")
    lines.append("")
    lines.append("## Stack detectado")
    lines.append("")
    lines.append(f"- {', '.join(stack) if stack else 'Unknown'}")
    lines.append("")
    lines.append("## Vista de modulos")
    lines.append("")
    if modules:
        for module in modules[:20]:
            lines.append(
                f"- **{module.get('module')}**: {module.get('source_files', 0)} archivos / {module.get('lines', 0)} lineas"
            )
    else:
        lines.append("- No se detectaron modulos de codigo fuente.")
    lines.append("")
    lines.append("## Rutas/Endpoints detectados")
    lines.append("")
    if routes:
        for route in routes[:40]:
            lines.append(f"- `{route}`")
    else:
        lines.append("- No se detectaron rutas con heuristicas actuales.")

    return "\n".join(lines) + "\n"


def _render_improvements(state: AgentState) -> str:
    opportunities = state.get("opportunities", [])

    lines: list[str] = []
    lines.append("# Oportunidades de mejora (Fase 1)")
    lines.append("")
    lines.append("Estas propuestas se basan en evidencia observada durante discovery.")
    lines.append("")

    grouped: dict[str, list[dict]] = {"L1": [], "L2": [], "L3": []}
    for opportunity in opportunities:
        level = str(opportunity.get("level", "L1"))
        if level not in grouped:
            grouped[level] = []
        grouped[level].append(opportunity)

    for level in ["L1", "L2", "L3"]:
        lines.append(f"## {level}")
        lines.append("")
        items = grouped.get(level, [])
        if not items:
            lines.append("- Sin oportunidades registradas.")
            lines.append("")
            continue

        for item in items:
            lines.append(f"- **{item.get('title', 'Sin titulo')}**")
            lines.append(f"  - Evidencia: {item.get('evidence', 'Sin evidencia')}" )
        lines.append("")

    return "\n".join(lines) + "\n"


def run_generation(state: AgentState) -> AgentState:
    runtime = dict(state.get("runtime", {}))
    phase = str(runtime.get("phase", "phase0"))
    if phase == "phase0":
        return {}

    workspace = Path(state["workspace_path"])
    timestamp = state.get("timestamp_utc", "unknown")

    readme_path = workspace / "README.md"
    architecture_path = workspace / "docs" / "architecture.md"
    improvements_path = workspace / "docs" / "improvements.md"

    readme_content = _render_readme(state)
    architecture_content = _render_architecture(state)
    improvements_content = _render_improvements(state)

    backups: dict[str, str] = {}
    readme_backup = _write_with_backup(readme_path, readme_content, timestamp)
    if readme_backup:
        backups["README.md"] = readme_backup

    architecture_backup = _write_with_backup(architecture_path, architecture_content, timestamp)
    if architecture_backup:
        backups["docs/architecture.md"] = architecture_backup

    improvements_backup = _write_with_backup(improvements_path, improvements_content, timestamp)
    if improvements_backup:
        backups["docs/improvements.md"] = improvements_backup

    generated_artifacts = {
        "readme": str(readme_path),
        "architecture": str(architecture_path),
        "improvements": str(improvements_path),
    }
    if backups:
        generated_artifacts["backups"] = str(backups)

    notes = list(state.get("notes", []))
    notes.append("Phase 1 generation completed: README, docs/architecture.md, docs/improvements.md")

    return {
        "generated_artifacts": generated_artifacts,
        "notes": notes,
    }
