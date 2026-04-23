from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from agent.state import AgentState

HINT_ROUTE_PATTERN = re.compile(r"/[a-zA-Z0-9/_-]+")
HTML_TITLE_PATTERN = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
HTML_H1_PATTERN = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def _normalize_base_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"http://{value}"
    return value.rstrip("/")


def _slugify_route(route: str) -> str:
    if route == "/":
        return "root"
    slug = route.strip("/").replace("/", "_")
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", slug)
    return slug or "screen"


def _strip_html(value: str) -> str:
    text = HTML_TAG_PATTERN.sub("", value)
    return re.sub(r"\s+", " ", text).strip()


def _extract_title(html: str) -> str:
    match = HTML_TITLE_PATTERN.search(html)
    if not match:
        return ""
    return _strip_html(match.group(1))[:120]


def _extract_h1(html: str) -> str:
    match = HTML_H1_PATTERN.search(html)
    if not match:
        return ""
    return _strip_html(match.group(1))[:120]


def _extract_dom_excerpt(html: str) -> str:
    cleaned = _strip_html(html)
    return cleaned[:240]


def _fetch_url(url: str, timeout_sec: int = 6) -> dict[str, Any]:
    request = Request(
        url,
        headers={"User-Agent": "Self-Improving-Agent/phase2"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_sec) as response:
            raw = response.read(250_000)
            html = raw.decode("utf-8", errors="ignore")
            return {
                "reachable": True,
                "status_code": int(getattr(response, "status", 200) or 200),
                "final_url": str(getattr(response, "url", url)),
                "html": html,
                "error": "",
            }
    except HTTPError as exc:
        payload = b""
        try:
            payload = exc.read(80_000)
        except Exception:  # noqa: BLE001
            payload = b""
        return {
            "reachable": False,
            "status_code": int(exc.code),
            "final_url": url,
            "html": payload.decode("utf-8", errors="ignore"),
            "error": f"http_error:{exc.code}",
        }
    except URLError as exc:
        return {
            "reachable": False,
            "status_code": None,
            "final_url": url,
            "html": "",
            "error": f"url_error:{exc.reason}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "reachable": False,
            "status_code": None,
            "final_url": url,
            "html": "",
            "error": f"network_error:{exc}",
        }


def _capture_screenshot(url: str, target_path: Path) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "not_available",
            "error": f"playwright_missing:{exc}",
            "path": None,
            "title": "",
            "h1": "",
        }

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=10_000)
            page.screenshot(path=str(target_path), full_page=True)
            title = page.title() or ""
            h1_text = ""
            try:
                locator = page.locator("h1")
                if locator.count() > 0:
                    h1_text = locator.first.inner_text(timeout=800).strip()
            except Exception:  # noqa: BLE001
                h1_text = ""
            browser.close()

        return {
            "status": "captured",
            "error": "",
            "path": str(target_path),
            "title": title[:120],
            "h1": h1_text[:120],
            "status_code": int(response.status) if response is not None else None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "error": f"playwright_capture_error:{exc}",
            "path": None,
            "title": "",
            "h1": "",
        }


def _extract_hint_routes(hints: list[str]) -> list[str]:
    routes: list[str] = []
    for hint in hints:
        hint_text = str(hint)
        lower = hint_text.lower()

        for route in HINT_ROUTE_PATTERN.findall(hint_text):
            routes.append(route)

        if "login" in lower:
            routes.append("/login")
        if "dashboard" in lower:
            routes.append("/dashboard")
        if "report" in lower:
            routes.append("/reportes")
        if "home" in lower:
            routes.append("/")

    deduped: list[str] = []
    seen: set[str] = set()
    for route in routes:
        if not route.startswith("/"):
            continue
        if route in seen:
            continue
        seen.add(route)
        deduped.append(route)
    return deduped


def _candidate_routes(config: dict[str, Any], repo_map: dict[str, Any]) -> list[str]:
    routes: list[str] = ["/"]

    auth = config.get("auth", {}) if isinstance(config.get("auth", {}), dict) else {}
    login_url = str(auth.get("login_url", "")).strip()
    if login_url.startswith("/"):
        routes.append(login_url)

    for route in repo_map.get("routes", [])[:20]:
        if isinstance(route, str) and route.startswith("/"):
            routes.append(route)

    hints = config.get("navigation_hints", [])
    if isinstance(hints, list):
        routes.extend(_extract_hint_routes([str(item) for item in hints]))

    deduped: list[str] = []
    seen: set[str] = set()
    for route in routes:
        if route in seen:
            continue
        seen.add(route)
        deduped.append(route)

    return deduped[:10]


def run_perception(state: AgentState) -> AgentState:
    runtime = dict(state.get("runtime", {}))
    phase = str(runtime.get("phase", "phase0"))
    if phase != "phase2":
        return {}

    config = state.get("config", {}) if isinstance(state.get("config", {}), dict) else {}
    repo_map = state.get("repo_map", {}) if isinstance(state.get("repo_map", {}), dict) else {}
    workspace = Path(state["workspace_path"]) if "workspace_path" in state else Path(".")

    notes = list(state.get("notes", []))
    errors = list(state.get("errors", []))

    app_config = config.get("app", {}) if isinstance(config.get("app", {}), dict) else {}
    base_url = _normalize_base_url(str(app_config.get("local_url", "")))
    start_command = str(app_config.get("start_command", "")).strip()

    routes_to_visit = _candidate_routes(config, repo_map)
    screens: list[dict[str, Any]] = []
    ui_issues: list[dict[str, str]] = []
    reachable_routes: list[str] = []
    screenshot_errors: list[str] = []

    if not base_url:
        notes.append("Phase 2 perception skipped network checks: app.local_url is empty.")
        ui_issues.append(
            {
                "severity": "high",
                "title": "Configurar app.local_url para exploracion visual",
                "action": "Define una URL local accesible (ej. http://localhost:3000) en AGENT_CONFIG.yaml.",
            }
        )

    for route in routes_to_visit:
        screen_name = _slugify_route(route)
        screen: dict[str, Any] = {
            "name": screen_name,
            "route": route,
            "url": "",
            "status": "skipped",
            "status_code": None,
            "title": "",
            "h1": "",
            "dom_excerpt": "",
            "screenshot": None,
        }

        if not base_url:
            screen["status"] = "skipped_no_base_url"
            screens.append(screen)
            continue

        target_url = urljoin(f"{base_url}/", route.lstrip("/"))
        screen["url"] = target_url

        fetch_data = _fetch_url(target_url)
        screen["status_code"] = fetch_data.get("status_code")

        if fetch_data.get("reachable", False):
            screen["status"] = "reachable"
            html = str(fetch_data.get("html", ""))
            screen["title"] = _extract_title(html)
            screen["h1"] = _extract_h1(html)
            screen["dom_excerpt"] = _extract_dom_excerpt(html)
            reachable_routes.append(route)

            screenshot_path = workspace / "docs" / "perception" / "screens" / f"{screen_name}.png"
            capture = _capture_screenshot(target_url, screenshot_path)
            capture_status = str(capture.get("status", ""))
            if capture_status == "captured":
                try:
                    relative_path = screenshot_path.relative_to(workspace).as_posix()
                except Exception:  # noqa: BLE001
                    relative_path = str(screenshot_path)
                screen["screenshot"] = relative_path

                if not screen["title"] and capture.get("title"):
                    screen["title"] = str(capture.get("title", ""))
                if not screen["h1"] and capture.get("h1"):
                    screen["h1"] = str(capture.get("h1", ""))
            else:
                capture_error = str(capture.get("error", "unknown_screenshot_error"))
                screenshot_errors.append(capture_error)
        else:
            screen["status"] = "unreachable"
            screen["error"] = str(fetch_data.get("error", "unreachable"))
            if start_command:
                screen["hint"] = f"Verifica si la app esta levantada con: {start_command}"

        screens.append(screen)

    if base_url and not reachable_routes:
        ui_issues.append(
            {
                "severity": "high",
                "title": "La app local no responde en las rutas exploradas",
                "action": "Levanta la app con start_command y confirma app.local_url antes de reintentar.",
            }
        )

    if screenshot_errors:
        ui_issues.append(
            {
                "severity": "medium",
                "title": "No se pudo capturar evidencia visual en una o mas pantallas",
                "action": "Instala Playwright y navegadores para habilitar screenshots reales en Fase 2.",
            }
        )

    for screen in screens:
        if screen.get("status") != "reachable":
            continue
        if not screen.get("title") and not screen.get("h1"):
            ui_issues.append(
                {
                    "severity": "low",
                    "title": f"Pantalla con metadatos minimos: {screen.get('route', '/')}",
                    "action": "Agrega title/h1 descriptivos para mejorar observabilidad y UX.",
                }
            )

    flows: list[dict[str, Any]] = []
    if reachable_routes:
        flows.append(
            {
                "name": "flujo_principal_estimado",
                "steps": reachable_routes[:5],
                "confidence": "medium" if len(reachable_routes) >= 2 else "low",
            }
        )

    summary = {
        "screens_total": len(screens),
        "screens_reachable": len([item for item in screens if item.get("status") == "reachable"]),
        "screens_with_screenshot": len([item for item in screens if item.get("screenshot")]),
        "flows_detected": len(flows),
        "ui_issues": len(ui_issues),
    }

    perception_map = {
        "phase": "phase2",
        "base_url": base_url,
        "routes_considered": routes_to_visit,
        "screens": screens,
        "flows": flows,
        "ui_issues": ui_issues[:20],
        "summary": summary,
        "diagnostics": {
            "start_command": start_command,
            "local_url_configured": bool(base_url),
            "screenshots_attempted": bool(base_url and screens),
        },
    }

    runtime["phase"] = "phase2"
    runtime["perception_version"] = "phase2-bootstrap"

    notes.append(
        "Phase 2 perception completed: "
        f"{summary['screens_reachable']}/{summary['screens_total']} reachable screens, "
        f"{summary['screens_with_screenshot']} screenshots."
    )

    return {
        "perception_map": perception_map,
        "notes": notes,
        "errors": errors,
        "runtime": runtime,
    }
