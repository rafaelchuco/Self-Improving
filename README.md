# My Project

README generado automaticamente por Self-Improving Agent (Fase 2).

## Contexto

- Tipo de proyecto detectado: **backend**
- Stack detectado: **Python**
- Branch actual: **main**
- Analisis generado en UTC: **20260423T051515Z**

## Ejecucion

```bash
# Crear entorno
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Comando sugerido por AGENT_CONFIG
python -m http.server 4173 -d demo_ui
```

## Estructura principal

- `.gitignore`
- `.vscode`
- `README.md`
- `agent`
- `config`
- `demo_ui`
- `docs`
- `logs`
- `requirements.txt`
- `run.py`

## Modulos detectados

| Modulo | Archivos fuente | Lineas aproximadas |
| --- | ---: | ---: |
| agent | 11 | 1909 |
| root | 1 | 6 |

## Rutas detectadas

- No se detectaron rutas explicitas con las heuristicas actuales.

## Estado de tests

- Tests encontrados: **0**

## Percepcion UI

- URL base analizada: **http://127.0.0.1:4173**
- Pantallas evaluadas: **3**
- Pantallas alcanzables: **3**
- Screenshots capturados: **3**
- Flujos detectados: **1**
- Hallazgos UI accionables: **0**

### Pantallas mapeadas

- `/` -> reachable (screenshot: `docs/perception/screens/root.png`) (related: demo_ui/dashboard/index.html, demo_ui/index.html, demo_ui/login/index.html)
- `/login` -> reachable (screenshot: `docs/perception/screens/login.png`) (related: demo_ui/login/index.html)
- `/dashboard` -> reachable (screenshot: `docs/perception/screens/dashboard.png`) (related: demo_ui/dashboard/index.html)

## Consistencia de configuracion

- Sin contradicciones detectadas entre AGENT_CONFIG y evidencia del repo.

## Hotspots tecnicos

- `agent/nodes/perception.py` (698 lineas)
- `agent/nodes/discovery.py` (391 lineas)
- `agent/nodes/generation.py` (377 lineas)
- `agent/adapters/filesystem_adapter.py` (164 lineas)
- `agent/run.py` (110 lineas)
- `agent/adapters/git_adapter.py` (81 lineas)
- `agent/graph.py` (64 lineas)
- `agent/state.py` (18 lineas)

## Oportunidades iniciales

- [L2] Crear base de tests automatizados -> No se detectaron archivos de tests en el repositorio.
- [L3] Refactorizar archivo de alta complejidad -> agent/nodes/perception.py tiene 698 lineas.
- [L2] Agregar cobertura sobre zona de alta rotacion -> agent/run.py aparece como archivo de alta frecuencia de cambios.
- [L1] Documentar rutas y flujos principales -> No se detectaron rutas explicitas con heuristicas actuales.

## Trazabilidad

Este documento se genero automaticamente desde el analisis del repositorio (Fase 2).
