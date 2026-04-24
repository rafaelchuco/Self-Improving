from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from agent.state import AgentState

HINT_ROUTE_PATTERN = re.compile(r"/[a-zA-Z0-9/_-]+")
HTML_TITLE_PATTERN = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
HTML_H1_PATTERN = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")

USERNAME_SELECTORS = [
    "input[name='username']",
    "input#username",
    "input[name='email']",
    "input[type='email']",
    "input[type='text']",
]

PASSWORD_SELECTORS = [
    "input[name='password']",
    "input#password",
    "input[type='password']",
]

SUBMIT_SELECTORS = [
    "button[type='submit']",
    "input[type='submit']",
    "button:has-text('Login')",
    "button:has-text('Sign In')",
    "button:has-text('Ingresar')",
]


def _normalize_base_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"http://{value}"
    return value.rstrip("/")


def _normalize_route(route: str) -> str:
    value = route.strip()
    if not value:
        return "/"
    if not value.startswith("/"):
        value = f"/{value}"
    value = re.sub(r"/{2,}", "/", value)
    if value != "/" and value.endswith("/"):
        value = value[:-1]
    return value


def _same_route(left: str, right: str) -> bool:
    return _normalize_route(left) == _normalize_route(right)


def _slugify_route(route: str) -> str:
    normalized = _normalize_route(route)
    if normalized == "/":
        return "root"
    slug = normalized.strip("/").replace("/", "_")
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", slug)
    return slug or "screen"


def _strip_html(value: str) -> str:
    text = HTML_TAG_PATTERN.sub("", value)
    return WHITESPACE_PATTERN.sub(" ", text).strip()


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


def _is_fetch_reachable(fetch_data: dict[str, Any]) -> bool:
    if fetch_data.get("reachable"):
        return True
    status_code = fetch_data.get("status_code")
    if isinstance(status_code, int) and status_code >= 100:
        return True
    return False


def _wait_for_url(base_url: str, timeout_sec: int = 25, interval_sec: float = 1.0) -> tuple[bool, dict[str, Any]]:
    last_probe = {"reachable": False, "status_code": None, "error": "not_probed"}
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        last_probe = _fetch_url(base_url, timeout_sec=4)
        if _is_fetch_reachable(last_probe):
            return True, last_probe
        time.sleep(interval_sec)
    return False, last_probe


def _start_local_app(
    workspace: Path,
    start_command: str,
    timestamp: str,
) -> tuple[subprocess.Popen[str] | None, Any | None, str | None, str | None]:
    if not start_command.strip():
        return None, None, None, "missing_start_command"

    runtime_logs = workspace / "logs" / "phase2_runtime"
    runtime_logs.mkdir(parents=True, exist_ok=True)
    log_path = runtime_logs / f"app_start_{timestamp}.log"

    try:
        log_handle = log_path.open("a", encoding="utf-8")
        process = subprocess.Popen(
            start_command,
            cwd=str(workspace),
            shell=True,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return process, log_handle, str(log_path), None
    except Exception as exc:  # noqa: BLE001
        return None, None, str(log_path), f"start_command_error:{exc}"


def _stop_local_app(process: subprocess.Popen[str] | None, log_handle: Any | None) -> None:
    try:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except Exception:  # noqa: BLE001
                process.kill()
                process.wait(timeout=5)
    except Exception:  # noqa: BLE001
        pass

    try:
        if log_handle is not None:
            log_handle.close()
    except Exception:  # noqa: BLE001
        pass


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
        route = _normalize_route(route)
        if route in seen:
            continue
        seen.add(route)
        deduped.append(route)
    return deduped


def _candidate_routes(config: dict[str, Any], repo_map: dict[str, Any]) -> list[str]:
    routes: list[str] = ["/"]

    auth = config.get("auth", {}) if isinstance(config.get("auth", {}), dict) else {}
    login_url = _normalize_route(str(auth.get("login_url", "")).strip())
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
        route = _normalize_route(route)
        if route in seen:
            continue
        seen.add(route)
        deduped.append(route)

    return deduped[:10]


def _related_files_for_route(route: str, repo_map: dict[str, Any]) -> list[str]:
    normalized = _normalize_route(route)
    tokens = [item for item in normalized.strip("/").split("/") if item]
    if not tokens:
        tokens = ["index", "home", "main"]

    candidates: list[str] = []
    for item in repo_map.get("structure_sample", []):
        if item.get("type") != "file":
            continue
        path = str(item.get("path", ""))
        if path:
            candidates.append(path)

    for item in repo_map.get("hotspots", {}).get("largest_files", []):
        path = str(item.get("path", ""))
        if path and path not in candidates:
            candidates.append(path)

    ranked: list[tuple[int, str]] = []
    for path in candidates:
        lower = path.lower()
        if lower.startswith("docs/perception/"):
            continue
        if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            continue
        if "/.agent_backups/" in lower or lower.startswith(".agent_backups/"):
            continue

        score = 0
        for token in tokens:
            token_lower = token.lower()
            if token_lower in lower:
                score += 2
        if normalized == "/" and ("index" in lower or "home" in lower):
            score += 1
        if score > 0:
            ranked.append((score, path))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [path for _, path in ranked[:5]]


def _fill_first(page: Any, selectors: list[str], value: str) -> str | None:
    for selector in selectors:
        try:
            locator = page.locator(selector)
            if locator.count() <= 0:
                continue
            locator.first.fill(value, timeout=1200)
            return selector
        except Exception:  # noqa: BLE001
            continue
    return None


def _click_first(page: Any, selectors: list[str]) -> str | None:
    for selector in selectors:
        try:
            locator = page.locator(selector)
            if locator.count() <= 0:
                continue
            locator.first.click(timeout=1200)
            return selector
        except Exception:  # noqa: BLE001
            continue
    return None


def _capture_screenshot(
    url: str,
    route: str,
    target_path: Path,
    auth_config: dict[str, Any],
) -> dict[str, Any]:
    route_norm = _normalize_route(route)
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "not_available",
            "error": f"playwright_missing:{exc}",
            "path": None,
            "title": "",
            "h1": "",
            "auth": {
                "attempted": False,
                "success": False,
            },
        }

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        auth_result: dict[str, Any] = {
            "attempted": False,
            "success": False,
            "username_selector": None,
            "password_selector": None,
            "submit_selector": None,
            "post_login_route": None,
        }

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=10_000)

            enabled = bool(auth_config.get("enabled", False))
            login_route = _normalize_route(str(auth_config.get("login_url", "/login")))
            credentials = (
                auth_config.get("credentials", {})
                if isinstance(auth_config.get("credentials", {}), dict)
                else {}
            )
            username = str(credentials.get("username", "")).strip()
            password = str(credentials.get("password", "")).strip()

            if enabled and username and password and _same_route(route_norm, login_route):
                auth_result["attempted"] = True
                auth_result["username_selector"] = _fill_first(page, USERNAME_SELECTORS, username)
                auth_result["password_selector"] = _fill_first(page, PASSWORD_SELECTORS, password)
                auth_result["submit_selector"] = _click_first(page, SUBMIT_SELECTORS)
                if not auth_result["submit_selector"]:
                    try:
                        page.keyboard.press("Enter")
                    except Exception:  # noqa: BLE001
                        pass
                page.wait_for_timeout(1200)

                post_route = _normalize_route(urlparse(page.url).path or "/")
                auth_result["post_login_route"] = post_route
                auth_result["success"] = not _same_route(post_route, login_route)

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
            "auth": auth_result,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "error": f"playwright_capture_error:{exc}",
            "path": None,
            "title": "",
            "h1": "",
            "auth": {
                "attempted": False,
                "success": False,
            },
        }


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
    auth_config = config.get("auth", {}) if isinstance(config.get("auth", {}), dict) else {}
    base_url = _normalize_base_url(str(app_config.get("local_url", "")))
    start_command = str(app_config.get("start_command", "")).strip()
    timestamp = str(state.get("timestamp_utc", "unknown"))

    routes_to_visit = _candidate_routes(config, repo_map)
    screens: list[dict[str, Any]] = []
    ui_issues: list[dict[str, str]] = []
    reachable_routes: list[str] = []
    screenshot_errors: list[str] = []
    auth_attempts: list[dict[str, Any]] = []

    app_status = "not_checked"
    startup_probe: dict[str, Any] = {"reachable": False, "status_code": None, "error": "not_probed"}
    app_process: subprocess.Popen[str] | None = None
    app_log_handle: Any | None = None
    app_log_path: str | None = None
    started_by_agent = False

    if base_url:
        startup_probe = _fetch_url(base_url, timeout_sec=4)
        if _is_fetch_reachable(startup_probe):
            app_status = "already_running"
            notes.append("Phase 2 perception detected app already running at local_url.")
        elif start_command:
            app_process, app_log_handle, app_log_path, start_error = _start_local_app(
                workspace,
                start_command,
                timestamp,
            )
            if start_error:
                app_status = "start_command_failed"
                ui_issues.append(
                    {
                        "severity": "high",
                        "title": "No se pudo iniciar la app local",
                        "action": f"Revisa start_command y entorno local. Detalle: {start_error}",
                    }
                )
            else:
                started_by_agent = True
                ready, probe = _wait_for_url(base_url, timeout_sec=30, interval_sec=1.0)
                startup_probe = probe
                if ready:
                    app_status = "started_by_agent"
                    notes.append("Phase 2 perception started app from AGENT_CONFIG.start_command.")
                else:
                    app_status = "started_but_unreachable"
                    msg = "Levanta la app y valida puerto/URL."
                    if app_log_path:
                        msg = f"Revisa logs de arranque en {app_log_path} y valida puerto/URL."
                    ui_issues.append(
                        {
                            "severity": "high",
                            "title": "La app no quedo disponible tras ejecutar start_command",
                            "action": msg,
                        }
                    )
        else:
            app_status = "missing_start_command"
            ui_issues.append(
                {
                    "severity": "high",
                    "title": "No hay start_command para levantar la app local",
                    "action": "Define app.start_command en AGENT_CONFIG.yaml para habilitar la percepcion de Fase 2.",
                }
            )

    if not base_url:
        notes.append("Phase 2 perception skipped network checks: app.local_url is empty.")
        ui_issues.append(
            {
                "severity": "high",
                "title": "Configurar app.local_url para exploracion visual",
                "action": "Define una URL local accesible (ej. http://localhost:3000) en AGENT_CONFIG.yaml.",
            }
        )
        app_status = "missing_local_url"

    for route in routes_to_visit:
        route = _normalize_route(route)
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
            "related_files": _related_files_for_route(route, repo_map),
        }

        if not base_url:
            screen["status"] = "skipped_no_base_url"
            screens.append(screen)
            continue

        target_url = urljoin(f"{base_url}/", route.lstrip("/"))
        screen["url"] = target_url

        fetch_data = _fetch_url(target_url)
        screen["status_code"] = fetch_data.get("status_code")

        if _is_fetch_reachable(fetch_data):
            screen["status"] = "reachable"
            html = str(fetch_data.get("html", ""))
            screen["title"] = _extract_title(html)
            screen["h1"] = _extract_h1(html)
            screen["dom_excerpt"] = _extract_dom_excerpt(html)
            reachable_routes.append(route)

            screenshot_path = workspace / "docs" / "perception" / "screens" / f"{screen_name}.png"
            capture = _capture_screenshot(target_url, route, screenshot_path, auth_config)
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

                auth_result = capture.get("auth")
                if isinstance(auth_result, dict) and auth_result.get("attempted"):
                    auth_attempts.append(auth_result)
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

    if bool(auth_config.get("enabled", False)) and not auth_attempts and base_url:
        ui_issues.append(
            {
                "severity": "medium",
                "title": "Auth habilitado sin intento de login exitoso",
                "action": "Verifica selectors y credenciales de login del entorno de desarrollo.",
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
    if "/login" in reachable_routes and "/dashboard" in reachable_routes:
        confidence = "high"
        if auth_attempts and not any(item.get("success") for item in auth_attempts):
            confidence = "medium"
        flows.append(
            {
                "name": "login_to_dashboard",
                "steps": ["/", "/login", "/dashboard"],
                "confidence": confidence,
            }
        )
    elif reachable_routes:
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
            "app_status": app_status,
            "app_started_by_agent": started_by_agent,
            "startup_probe": startup_probe,
            "app_start_log": app_log_path,
            "auth_enabled": bool(auth_config.get("enabled", False)),
            "auth_attempts": auth_attempts,
        },
    }

    runtime["phase"] = "phase2"
    runtime["perception_version"] = "phase2"

    notes.append(
        "Phase 2 perception completed: "
        f"{summary['screens_reachable']}/{summary['screens_total']} reachable screens, "
        f"{summary['screens_with_screenshot']} screenshots."
    )

    if started_by_agent:
        _stop_local_app(app_process, app_log_handle)
    elif app_log_handle is not None:
        _stop_local_app(None, app_log_handle)

    return {
        "perception_map": perception_map,
        "notes": notes,
        "errors": errors,
        "runtime": runtime,
    }
