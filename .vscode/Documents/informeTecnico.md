
# 📋 INFORME TÉCNICO COMPLETO
## Self-Improving Software Agent — Agente Autónomo de Análisis, Documentación y Mejora Continua


# 1. DESCRIPCIÓN GENERAL DEL PROYECTO

Este proyecto consiste en la construcción de un **agente inteligente autónomo** que se instala como capa independiente sobre cualquier proyecto de software abierto en VS Code. Su propósito es actuar como un ingeniero de software asistido por IA que, partiendo de cero conocimiento del proyecto, es capaz de entenderlo en profundidad, documentarlo, detectar problemas y mejorar el código de manera progresiva e iterativa. [eliostruyf](https://www.eliostruyf.com/vcode-workspaces-ai-assistant-context/)

El agente no es un plugin puntual ni una herramienta de autocompletado. Es un **sistema multi-agente de ciclo cerrado (closed-loop)** donde cada acción genera conocimiento que alimenta la siguiente decisión. Cuanto más tiempo opera sobre un proyecto, más preciso y útil se vuelve. [semanticscholar](https://www.semanticscholar.org/paper/Towards-Explainable-Agentic-Intelligence:-A-Hybrid-Panchal-Gole/6d5b9ef43c383884fd5d8d339537ea618351d048)

### ¿Qué problema resuelve?

La mayoría de proyectos de software en el mundo real tienen tres problemas crónicos:

- **Documentación ausente o desactualizada** — el README no refleja el estado real del sistema
- **Tests insuficientes o inexistentes** — el código no tiene cobertura automatizada
- **Deuda técnica acumulada** — código duplicado, naming inconsistente, validaciones faltantes

El agente ataca los tres simultáneamente, de forma autónoma, sin requerir intervención constante del desarrollador.

***

# 2. MODELO DE INSTALACIÓN Y PORTABILIDAD

Una decisión de diseño clave es que el agente **no se conecta remotamente** a repositorios. En cambio, vive como una carpeta independiente en el sistema del desarrollador y se "activa" sobre el workspace de VS Code que tenga abierto.

```
📦 /self-improving-agent/         ← El agente (versión general, reutilizable)
       agent/
       mcp_servers/
       memory/
       config/
          └── AGENT_CONFIG.yaml   ← Template vacío

📁 /mi-proyecto-react/            ← El proyecto del usuario en VS Code
       src/
       public/
       package.json
       AGENT_CONFIG.yaml          ← Se copia aquí, el usuario lo llena UNA sola vez
```

El usuario copia el archivo `AGENT_CONFIG.yaml` a la raíz de su proyecto, lo configura con información básica (URL local, credenciales de prueba, hints de navegación) y el agente toma el control desde ese punto. Esta es la **única intervención manual requerida**. [eliostruyf](https://www.eliostruyf.com/vcode-workspaces-ai-assistant-context/)

### El `AGENT_CONFIG.yaml` — Puerta de Entrada

```yaml
project:
  name: "Mi App React"
  type: "frontend"           # frontend | backend | fullstack
  stack: []                  # Vacío: el agente lo detecta automáticamente

app:
  local_url: "http://localhost:3000"
  start_command: "npm run dev"

auth:
  enabled: true
  login_url: "/login"
  credentials:
    username: "admin@test.com"
    password: "test1234"       # Solo para entorno local/dev

navigation_hints:
  - "Después de login ir a /dashboard"
  - "Explorar la sección de reportes"
  - "Probar el flujo de creación de usuario"

improvement_level: 2           # 1=docs only | 2=docs+tests | 3=refactor
```

Las credenciales se manejan de forma segura mediante el sistema de `secrets` de Playwright MCP, que las inyecta en runtime sin exponerlas en logs ni en pantalla. [playwright](https://playwright.dev/mcp/configuration/options)

***

# 3. ARQUITECTURA GLOBAL DEL SISTEMA

El sistema se organiza en **tres planos** que se comunican exclusivamente a través del protocolo MCP como bus de comunicación estándar: [linkedin](https://www.linkedin.com/pulse/multi-context-prompting-mcp-langgraph-architecting-next-gen-anand-cbjoc)

```
╔══════════════════════════════════════════════════════╗
║              PLANO DE ORQUESTACIÓN                   ║
║         LangGraph (grafo cíclico stateful)           ║
║                                                      ║
║  [Discovery] → [Perception] → [Generation]           ║
║                                    ↓                 ║
║  [Memory]   ← [Evaluation]  ← [Execution]            ║
║      ↑_________________________________↑             ║
║                   LOOP                               ║
╚══════════════════╤═══════════════════════════════════╝
                   │  MCP Bus
╔══════════════════╧═══════════════════════════════════╗
║           PLANO DE HERRAMIENTAS (MCP Servers)        ║
║  [Filesystem]  [Git]  [Playwright]  [AST]            ║
║  [TestRunner]  [DocsWriter]  [Memory]                ║
╚══════════════════╤═══════════════════════════════════╝
                   │
╔══════════════════╧═══════════════════════════════════╗
║         PLANO DEL PROYECTO (workspace VS Code)       ║
║    /src   /tests   /docs   git history   UI live     ║
╚══════════════════════════════════════════════════════╝
```

El orquestador central es **LangGraph**, el framework más adoptado en 2026 para sistemas multi-agente con grafos cíclicos y checkpointing de estado. Cada agente es un nodo del grafo, y los edges condicionales determinan el flujo según el resultado de cada acción. [dev](https://dev.to/ottoaria/langgraph-in-2026-build-multi-agent-ai-systems-that-actually-work-3h5)

***

# 4. LOS AGENTES DEL SISTEMA

## 🔍 Agente 1 — Discovery Agent (*"Entiende el proyecto"*)

### Función
Es el primer agente en activarse. Su trabajo es construir un **mapa mental completo del proyecto** analizando exclusivamente el código fuente y los archivos del repo, sin tocar la aplicación en ejecución.

### ¿Qué hace exactamente?

1. Escanea la estructura completa de carpetas del workspace de VS Code [reddit](https://www.reddit.com/r/ChatGPTCoding/comments/1g6l3sm/made_a_vscode_extension_with_gui_to_map_your/)
2. Detecta el stack tecnológico automáticamente:
   - `package.json` → React, Vue, Angular, versiones, dependencias
   - `pom.xml` → Spring Boot, Java version
   - `requirements.txt` → Python, FastAPI, Django
   - `Dockerfile` → contenedores, servicios
3. Lee todos los archivos relevantes: código fuente, README existente, documentación en `/docs`, configuraciones (`.env.example`, `vite.config`, `tsconfig`), tests existentes
4. Usa **Code AST MCP** (basado en tree-sitter) para parsear el código y extraer: funciones, clases, componentes, hooks, dependencias entre módulos — funciona con más de 20 lenguajes sin configuración adicional [dev](https://dev.to/badmonster0/i-built-a-code-ast-mcp-that-saves-70-tokens-and-went-viral-54k-views-4c6a)
5. Analiza el historial de git para identificar: archivos más modificados, áreas más conflictivas, patrones de desarrollo

### Output que produce
```json
{
  "stack": ["React 18", "TypeScript", "Vite", "Tailwind CSS"],
  "components": 47,
  "routes": ["/login", "/dashboard", "/reportes", "/usuarios"],
  "tests_found": 0,
  "most_modified_files": ["UserTable.tsx", "AuthContext.tsx"],
  "opportunities": [
    "0 tests en el proyecto",
    "UserTable.tsx tiene 320 líneas (candidato a refactor)",
    "AuthContext sin manejo de errores"
  ]
}
```

### MCP Servers que usa

| MCP Server | Herramientas usadas | Para qué |
|---|---|---|
| Filesystem MCP | `read_file`, `list_dir` | Leer código y estructura |
| Git MCP | `git_log`, `git_diff` | Historial y frecuencia de cambios |
| Code AST MCP | `parse_ast`, `extract_symbols` | Análisis sintáctico profundo  [dev](https://dev.to/badmonster0/i-built-a-code-ast-mcp-that-saves-70-tokens-and-went-viral-54k-views-4c6a) |

***

## 👁️ Agente 2 — Perception Agent (*"Ve la UI"*)

### Función
Es el agente más diferenciador del sistema. Percibe la aplicación **exactamente como lo haría un usuario real**: la ve, hace clic, navega, llena formularios. Combina tres fuentes de información simultáneamente: imagen (screenshot), estructura (DOM) y contexto (lo que el Discovery Agent ya conoce del código).

### ¿Por qué es el corazón del proyecto?

La mayoría de herramientas de IA analizan código. Pocas analizan el sistema en ejecución. Ninguna combina análisis de código + percepción visual + memoria en un loop cerrado. Esta combinación es lo que acerca el sistema al comportamiento de un ingeniero humano real.

### Flujo completo de exploración

```
 [eliostruyf](https://www.eliostruyf.com/vcode-workspaces-ai-assistant-context/) Leer AGENT_CONFIG.yaml
       ↓
 [semanticscholar](https://www.semanticscholar.org/paper/Towards-Explainable-Agentic-Intelligence:-A-Hybrid-Panchal-Gole/6d5b9ef43c383884fd5d8d339537ea618351d048) Ejecutar start_command → npm run dev
    Esperar hasta que localhost:3000 responda
       ↓
 [playwright](https://playwright.dev/mcp/configuration/options) Playwright MCP abre el navegador
    (modo headed — el usuario puede verlo si quiere)
       ↓
 [linkedin](https://www.linkedin.com/pulse/multi-context-prompting-mcp-langgraph-architecting-next-gen-anand-cbjoc) Navegar a login_url → /login
       ↓
 [dev](https://dev.to/ottoaria/langgraph-in-2026-build-multi-agent-ai-systems-that-actually-work-3h5) Capturar screenshot + leer DOM completo
    LLM analiza imagen + estructura:
    → "Esto es una pantalla de login con email y password"
       ↓
 [pooya](https://pooya.blog/blog/ai-agents-frameworks-local-llm-2026/) Inyectar credenciales del AGENT_CONFIG.yaml
    email: admin@test.com
    password: ████████ (oculto en logs)
       ↓
 [reddit](https://www.reddit.com/r/ChatGPTCoding/comments/1g6l3sm/made_a_vscode_extension_with_gui_to_map_your/) Hacer clic en "Iniciar sesión"
    Esperar redirección
       ↓
 [dev](https://dev.to/badmonster0/i-built-a-code-ast-mcp-that-saves-70-tokens-and-went-viral-54k-views-4c6a) Capturar nueva pantalla → /dashboard
    LLM analiza: "Dashboard con 4 métricas principales y sidebar"
       ↓
 [playwright](https://playwright.dev/docs/getting-started-mcp) Seguir navigation_hints del usuario:
    → "Explorar reportes" → click en menú → screenshot → análisis
    → "Probar creación de usuario" → flujo completo → screenshots
       ↓
 [github](https://github.com/microsoft/playwright-mcp) Explorar autónomamente el resto de rutas
     detectadas por el Discovery Agent
       ↓
 [infoworld](https://www.infoworld.com/article/4154570/best-practices-for-building-agentic-systems.html) Construir grafo de navegación completo
```

### Capacidades técnicas detalladas

El agente usa **Playwright MCP** (oficial de Microsoft, production-ready desde 2025) que expone las siguientes herramientas: [playwright](https://playwright.dev/docs/getting-started-mcp)

| Tool MCP | Acción | Uso en el agente |
|---|---|---|
| `browser_navigate` | Navega a una URL | Explorar cada ruta del sistema |
| `browser_screenshot` | Captura pantalla completa | Documentar y analizar visualmente |
| `browser_click` | Hace clic en elemento | Navegar menus, botones, links |
| `browser_type` | Escribe en un campo | Llenar formularios con datos de prueba |
| `browser_get_visible_text` | Extrae texto visible | Entender contenido de la pantalla |
| `browser_evaluate` | Ejecuta JS en la página | Extraer estado interno del DOM |
| `browser_wait_for` | Espera un elemento | Manejar loading states y animaciones |

La sesión del navegador es **persistente** — el login se hace una sola vez y se mantiene durante toda la exploración. [playwright](https://playwright.dev/docs/getting-started-mcp)

### Análisis por cada pantalla

Para cada pantalla capturada, el LLM con visión (Claude o GPT-4o) recibe:
- El screenshot como imagen
- El DOM simplificado (estructura de elementos)
- El contexto del Discovery Agent (qué sabe del código de esa ruta)

Y produce:

```
ANÁLISIS: /dashboard

Tipo de pantalla: Dashboard principal
Componentes detectados:
  - Sidebar de navegación (5 items)
  - 4 tarjetas de métricas (Usuarios, Ventas, Reportes, Tareas)
  - Tabla de actividad reciente
  - Header con avatar de usuario

Problemas detectados:
  ⚠️  Botón "Exportar" no tiene estado de carga (puede confundir al usuario)
  ⚠️  Tabla sin paginación (riesgo con muchos datos)
  ⚠️  Sin mensaje cuando la tabla está vacía (empty state faltante)

Código relacionado (del Discovery):
  → DashboardPage.tsx, MetricCard.tsx, ActivityTable.tsx
```

### Output completo del Perception Agent

```
MAPA DE PANTALLAS:
  /login      → Login Screen (email + password)
  /dashboard  → Dashboard con métricas
  /reportes   → Lista de reportes con filtros
  /usuarios   → CRUD de usuarios con tabla paginada
  /perfil     → Formulario de edición de perfil

FLUJOS DE USUARIO DETECTADOS:
  Login → Dashboard → Reportes → Detalle Reporte
  Login → Dashboard → Usuarios → Crear Usuario
  Login → Perfil → Editar → Guardar

PROBLEMAS VISUALES DETECTADOS:
  [MEDIA]  Botón "Guardar" sin spinner de carga (3 pantallas)
  [MEDIA]  Formulario login sin mensaje de error visible
  [BAJA]   Empty state faltante en tabla de reportes
  [BAJA]   Inconsistencia en estilos de botones secundarios

COMPONENTES UI IDENTIFICADOS:
  - 6 formularios
  - 4 tablas de datos
  - 12 botones de acción
  - 3 gráficos/charts
  - 1 sidebar de navegación
```

***

## ✍️ Agente 3 — Generation Agent (*"Produce artefactos"*)

### Función
Toma toda la información producida por Discovery y Perception y genera documentación real y propuestas de mejora concretas y priorizadas. Es el agente que convierte conocimiento en valor tangible.

### ¿Qué genera?

**Nivel 1 — Documentación (siempre, sin riesgo):**
- `README.md` completo: stack, instalación, estructura, descripción de módulos, flujos de usuario con screenshots referenciados
- `docs/architecture.md`: diagrama de componentes y sus relaciones
- `docs/ui-flows.md`: flujos de usuario documentados visualmente
- `docs/improvements.md`: lista priorizada de mejoras detectadas
- Comentarios JSDoc/Javadoc en funciones sin documentar

**Nivel 2 — Tests y validaciones (controlado, en branch separado):**
- Tests automatizados con Playwright para cada flujo de usuario identificado
- Validaciones de inputs en formularios detectados como incompletos
- Tests unitarios para funciones críticas sin cobertura

**Nivel 3 — Refactoring (avanzado, requiere validación explícita):**
- División de componentes grandes (ej: UserTable.tsx de 320 líneas → 3 componentes)
- Corrección de naming inconsistente
- Reestructuración de módulos con alto acoplamiento

### Regla de niveles

> El agente **nunca salta de nivel** sin haber ejecutado, validado y registrado el nivel anterior. Esta restricción es el mecanismo de seguridad más importante del sistema. [infoworld](https://www.infoworld.com/article/4154570/best-practices-for-building-agentic-systems.html)

### Propuestas de mejora que produce

```
PROPUESTAS PRIORIZADAS:

[L1 - SEGURO] Generar README.md completo
[L1 - SEGURO] Agregar JSDoc a 12 funciones sin documentar
[L1 - SEGURO] Crear docs/ui-flows.md con screenshots

[L2 - CONTROLADO] Crear test para flujo de login (Playwright)
[L2 - CONTROLADO] Crear test para flujo de creación de usuario
[L2 - CONTROLADO] Agregar mensaje de error en formulario de login
[L2 - CONTROLADO] Agregar loading state en botones de submit

[L3 - AVANZADO] Refactorizar UserTable.tsx (320 líneas → 3 componentes)
[L3 - AVANZADO] Extraer lógica de AuthContext a custom hook
```

***

## 🔧 Agente 4 — Execution Agent (*"Aplica los cambios"*)

### Función
Materializa las propuestas del Generation Agent en código real. Es el agente que "toca" el proyecto, siempre dentro de un entorno controlado y reversible.

### Protocolo de seguridad obligatorio

Antes de cualquier modificación, el agente ejecuta este protocolo sin excepción: [infoworld](https://www.infoworld.com/article/4154570/best-practices-for-building-agentic-systems.html)

```
1. git checkout -b agent/iteration-{N}
   (rama separada para cada cambio)

2. Aplica la modificación vía Filesystem MCP:
   write_file(path, new_content)

3. Ejecuta los tests:
   Test Runner MCP → run_jest() / run_maven_test()

4. ¿Tests pasan?
   ✅ SÍ → git commit con mensaje estructurado
   ❌ NO → git stash + registra error + reintenta (máx. 3 veces)
            Si sigue fallando → anota en memoria + pasa a siguiente mejora

5. Documentación:
   Actualiza changelog.md con el cambio realizado
```

### Formato de commits del agente
```
agent(iteration-003): add loading state to SaveButton component

- Added isLoading prop to SaveButton.tsx
- Added spinner icon from lucide-react
- Tested via Playwright: loading state visible on click
- All 15 existing tests pass
```

***

## 📊 Agente 5 — Evaluation Agent (*"Aprende del resultado"*)

### Función
Determina si el ciclo fue exitoso y alimenta la memoria del sistema. Es el agente que cierra el loop y hace que el sistema mejore con el tiempo.

### ¿Cómo evalúa?

Evalúa en **dos dimensiones simultáneas**:

**Dimensión funcional:**
- ¿Pasaron todos los tests existentes?
- ¿La app sigue levantando sin errores?
- Playwright toma screenshot post-cambio y lo compara con el estado anterior

**Dimensión cualitativa:**
- ¿El código es más legible después del cambio?
- ¿La UI mejoró visualmente? (comparación de screenshots antes/después)
- ¿El cambio genera nuevas oportunidades de mejora?

### Comparación visual antes/después

```
ITERACIÓN 003 — Botón SaveButton

ANTES:                          DESPUÉS:
[Guardar]                       [⟳ Guardando...]
(sin feedback)                  (con spinner visible)

Screenshot: iteration_002.png   Screenshot: iteration_003.png
Resultado: ✅ MEJORA CONFIRMADA
```

### Registro en memoria
```json
{
  "project": "mi-proyecto-react",
  "iteration": 3,
  "action": "add_loading_state_button",
  "component": "SaveButton.tsx",
  "result": "SUCCESS",
  "tests_before": 15,
  "tests_after": 15,
  "visual_validation": "playwright_screenshot_match",
  "lesson": "Botones submit en este proyecto usan patrón isLoading con lucide-react spinner",
  "pattern_reusable": true,
  "applies_to": ["CreateUserButton.tsx", "EditProfileButton.tsx"]
}
```

La última línea es clave: el agente aprende que ese patrón aplica a **otros componentes similares** y los incluye en la lista de mejoras siguientes, sin que nadie se lo diga.

***

# 5. EL SISTEMA DE MEMORIA

La memoria es lo que transforma este sistema de una herramienta de ejecución a un sistema que genuinamente **aprende**. Se implementan tres capas con responsabilidades distintas: [dev](https://dev.to/sreeni5018/the-architecture-of-agent-memory-how-langgraph-really-works-59ne)

## Memoria de Corto Plazo (sesión actual)

- **Tecnología:** Estado interno del grafo LangGraph (en RAM)
- **Contenido:** Iteración en curso, archivo siendo procesado, error detectado, plan vigente
- **Vida útil:** Se descarta al finalizar el ciclo de sesión
- **Para qué:** Permite que el agente no "olvide" qué estaba haciendo si un paso falla y necesita reintentar

## Memoria de Largo Plazo (cross-sesiones)

- **Tecnología:** Mem0 + Qdrant (vector database local)
- **Contenido:** Embeddings del código analizado, patrones aprendidos, decisiones históricas, lecciones de errores
- **Para qué:** En la Sesión 2, el agente no re-analiza lo que ya conoce — lee la memoria y continúa donde se quedó [mem0](https://mem0.ai/blog/langgraph-tutorial-build-advanced-ai-agents)
- **Ejemplo de consulta:** *"¿Cómo manejé botones de submit en este proyecto antes?"* → recupera el patrón aprendido en iteración 3

## Memoria Estructural (grafo del proyecto)

- **Tecnología:** SQLite con esquema relacional (liviano, portable, sin servidor)
- **Contenido:** Relaciones entre módulos, componentes, funciones, pantallas, flujos y el historial de iteraciones

```
Proyecto
   └── Módulos (Dashboard, Auth, Reportes)
         └── Componentes (DashboardPage, MetricCard, SaveButton)
               └── Funciones (handleSave, validateForm)
               └── Pantallas detectadas (/dashboard)
               └── Iteraciones aplicadas (iter-003: loading state)
                     └── Resultado (SUCCESS)
                     └── Lección aprendida
```

- **Para qué:** Permite responder preguntas estratégicas como *"¿Qué áreas del proyecto han tenido más fallos?"* o *"¿Qué componentes aún no han sido revisados?"*

***

# 6. EL PROTOCOLO MCP — POR QUÉ Y PARA QUÉ

MCP (Model Context Protocol) es el estándar abierto de Anthropic que actúa como bus universal de comunicación entre el agente y las herramientas. Sin MCP, cada integración requeriría código personalizado. Con MCP, el agente puede usar cualquier herramienta que implemente el protocolo de forma transparente. [ibm](https://www.ibm.com/es-es/think/topics/model-context-protocol)

## Servidores MCP del Sistema

| MCP Server | Origen | Herramientas expuestas | Para qué se usa |
|---|---|---|---|
| **Filesystem MCP** | Oficial (Anthropic) | `read_file`, `write_file`, `list_dir` | Leer y modificar código fuente |
| **Git MCP** | Oficial (GitHub) | `create_branch`, `commit`, `git_log`, `diff` | Ramas seguras + historial |
| **Playwright MCP** | Oficial (Microsoft) | `navigate`, `screenshot`, `click`, `type`, `dom` | Percepción visual completa  [playwright](https://playwright.dev/docs/getting-started-mcp) |
| **Code AST MCP** | Open source | `parse_ast`, `extract_symbols`, `search_semantic` | Análisis profundo de código  [dev](https://dev.to/badmonster0/i-built-a-code-ast-mcp-that-saves-70-tokens-and-went-viral-54k-views-4c6a) |
| **Test Runner MCP** | ⚙️ **Personalizado** | `run_jest`, `run_maven`, `run_pytest`, `get_coverage` | Ejecutar y leer resultados de tests |
| **Docs MCP** | ⚙️ **Personalizado** | `write_readme`, `update_changelog`, `generate_jsdoc` | Escribir documentación estructurada |

Los dos servidores marcados como **Personalizados** son los que el proyecto debe construir. Son wrappers de comandos de terminal expuestos como herramientas MCP — relativamente simples de implementar pero críticos para el diferenciador del sistema. [linkedin](https://www.linkedin.com/pulse/multi-context-prompting-mcp-langgraph-architecting-next-gen-anand-cbjoc)

## Por qué MCP y no llamadas directas

La ventaja arquitectónica es la **intercambiabilidad**: si mañana aparece una herramienta de análisis de código mejor que tree-sitter, basta con reemplazar el Code AST MCP Server sin tocar ningún agente. Los agentes nunca saben qué herramienta están usando — solo saben qué tool invocar y qué resultado esperan. Esto hace al sistema mantenible y extensible. [marvik](https://www.marvik.ai/es/blog/model-context-protocol-supercharge-your-agents-with-mcp)

***

# 7. EL GRAFO LANGGRAPH — EL CICLO CERRADO

LangGraph implementa el ciclo cerrado como un **grafo dirigido con nodos condicionales**. Cada nodo es un agente, y los edges deciden el camino según el resultado: [dev](https://dev.to/ottoaria/langgraph-in-2026-build-multi-agent-ai-systems-that-actually-work-3h5)

```
          START
            ↓
    ┌─────────────────┐
    │  DISCOVERY NODE │  ← Lee código, detecta stack, mapea estructura
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │ PERCEPTION NODE │  ← Levanta app, navega, screenshots, DOM
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │ GENERATION NODE │  ← Genera docs + lista de mejoras priorizadas
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │  PLANNING NODE  │  ← LLM decide qué mejora aplicar en esta iteración
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │ EXECUTION NODE  │  ← Aplica cambio en git branch separado
    └────────┬────────┘
             ↓
    ┌─────────────────┐
    │VALIDATION NODE  │  ← Corre tests + Playwright verifica UI
    └────────┬────────┘
             ↓
         ¿Resultado?
        /            \
      PASS           FAIL
       ↓               ↓
  ┌─────────┐    ┌──────────────┐
  │ COMMIT  │    │ ANALYZE ERROR│
  │ MEMORY  │    │   ROLLBACK   │
  │  DOCS   │    └──────┬───────┘
  └────┬────┘           │
       ↓         ¿Intentos < 3?
  ¿Más mejoras?    /         \
   /        \   SÍ           NO
 SÍ         NO   └→ PLANNING  └→ SKIP + MEMORY
  └→ PLANNING  ↓
               END
```

LangGraph mantiene el **estado completo del grafo** entre iteraciones mediante checkpointing. Si el proceso se interrumpe (apagan el PC, falla la red), al reiniciar el agente retoma exactamente donde se quedó. [generect](https://generect.com/blog/langgraph-mcp/)

***

# 8. FLUJO COMPLETO DE UNA SESIÓN REAL

Así se ve el agente trabajando desde cero en un proyecto React real:

### Minuto 0 — Arranque
```
Usuario ejecuta: python agent/run.py --workspace ./mi-proyecto-react
Agente lee AGENT_CONFIG.yaml
Lanza MCP Servers en background
Inicia grafo LangGraph
```

### Minutos 1-5 — Discovery
```
✅ Stack detectado: React 18 + TypeScript + Vite + Tailwind
✅ 47 componentes mapeados via AST
✅ 4 rutas identificadas: /login, /dashboard, /reportes, /usuarios
⚠️  0 tests encontrados — oportunidad crítica detectada
⚠️  UserTable.tsx: 320 líneas — candidato a refactor
```

### Minutos 6-15 — Perception
```
🚀 Ejecutando: npm run dev → localhost:3000 listo
🌐 Playwright abre navegador...
  → Login con credenciales → ✅ Success
  → /dashboard capturado → analizado → "Dashboard con 4 métricas"
  → /reportes capturado → "Lista con filtros y tabla sin paginación"
  → /usuarios capturado → "CRUD completo con tabla"
  → Flujo creación usuario → 4 screenshots del flujo completo

⚠️  Problemas visuales detectados: 3 botones sin loading state
⚠️  Formulario login sin feedback de error visible
```

### Minutos 16-20 — Generation
```
📄 Generando README.md... ✅
📄 Generando docs/architecture.md... ✅
📄 Generando docs/ui-flows.md... ✅
📋 Lista de mejoras generada: 9 propuestas (3 L1, 4 L2, 2 L3)
```

### Minutos 21-45 — Execution Loop (Iteraciones)

```
ITERACIÓN 001:
  → Aplica: Agrega JSDoc a 12 funciones
  → Tests: ✅ 0 tests (no hay nada que romper)
  → Commit: agent(iter-001): add JSDoc to undocumented functions
  → Memory: "patrón de JSDoc preferido en este proyecto"

ITERACIÓN 002:
  → Aplica: Crea test Playwright para flujo de login
  → Tests: ✅ 1 nuevo test pasa
  → Commit: agent(iter-002): add login flow e2e test
  → Memory: "selector preferido para el botón login: data-testid"

ITERACIÓN 003:
  → Aplica: Agrega loading state a SaveButton
  → Tests: ✅ 1 test nuevo + 1 existente pasan
  → Playwright verifica UI: spinner visible ✅
  → Commit: agent(iter-003): add loading state to SaveButton
  → Memory: "patrón isLoading con lucide-react, reutilizable en 2 componentes más"
```

### Resultado al finalizar
```
📊 RESUMEN DE SESIÓN:
  Componentes documentados: 47
  Tests creados: 3
  Mejoras aplicadas: 3/9 (continúa en próxima sesión)
  Problemas resueltos: 2 (loading states, JSDoc)
  Problemas pendientes: 4 (L2) + 2 (L3)
  Documentación generada: README + 3 archivos en /docs + changelog

🔁 Próxima sesión: el agente retoma desde mejora #4
   (sin re-analizar — usa memoria persistente)
```

***

# 9. EL DIFERENCIADOR REAL

Existen herramientas parciales en el mercado. Ninguna combina todas las capacidades simultáneamente: [arxiv](https://arxiv.org/html/2604.04990v1)

| Capacidad | GitHub Copilot | Devin | SWE-Agent | **Este sistema** |
|---|---|---|---|---|
| Análisis de código (AST) | Parcial | ✅ | ✅ | ✅ |
| Percepción visual DOM/UI | ❌ | Parcial | ❌ | ✅ |
| Memoria cross-sesión | ❌ | ❌ | ❌ | ✅ |
| Documentación viva automática | ❌ | ❌ | ❌ | ✅ |
| Ciclo cerrado autónomo | ❌ | ✅ | ✅ | ✅ |
| Portabilidad (cualquier proyecto) | N/A | ❌ | ❌ | ✅ |
| Control de riesgo por niveles | N/A | Parcial | ❌ | ✅ |

La combinación de **percepción visual + memoria persistente + documentación viva + ciclo cerrado + portabilidad** es lo que hace a este proyecto genuinamente original.

***

# 10. STACK TECNOLÓGICO COMPLETO

| Capa | Tecnología | Versión | Función |
|---|---|---|---|
| **Orquestador** | LangGraph | 0.3+ | Grafo cíclico + checkpointing  [dev](https://dev.to/ottoaria/langgraph-in-2026-build-multi-agent-ai-systems-that-actually-work-3h5) |
| **Protocolo** | MCP (Anthropic) | 1.x | Bus de comunicación universal  [ibm](https://www.ibm.com/es-es/think/topics/model-context-protocol) |
| **LLM principal** | Claude 3.7 Sonnet | Latest | Razonamiento + visión + MCP nativo |
| **LLM visión** | GPT-4o / Claude 3.7 | Latest | Análisis de screenshots |
| **Análisis código** | Code AST MCP (tree-sitter) | 0.24+ | Parsing multi-lenguaje  [dev](https://dev.to/badmonster0/i-built-a-code-ast-mcp-that-saves-70-tokens-and-went-viral-54k-views-4c6a) |
| **Navegador** | Playwright MCP | 1.x | Percepción visual y navegación  [playwright](https://playwright.dev/docs/getting-started-mcp) |
| **Memoria ST** | LangGraph Checkpointer | Built-in | Estado de sesión |
| **Memoria LT** | Mem0 + Qdrant | Latest | Persistencia cross-sesión  [mem0](https://mem0.ai/blog/langgraph-tutorial-build-advanced-ai-agents) |
| **Memoria estructural** | SQLite | 3.x | Grafo de conocimiento del proyecto |
| **Control versiones** | Git MCP | Oficial | Ramas seguras + commits |
| **Runtime** | Python | 3.11+ | Lenguaje base del agente |

***

# 11. ROADMAP DE IMPLEMENTACIÓN

| Fase | Objetivo | Entregable | Duración |
|---|---|---|---|
| **Fase 0** | Setup base: LangGraph + Filesystem MCP + Git MCP | Agente que lee el repo e imprime el mapa | 1 semana |
| **Fase 1** | Discovery Agent completo + Generation de README | README generado automáticamente | 2 semanas |
| **Fase 2** | Perception Agent + Playwright MCP + análisis visual | Mapa de pantallas con screenshots | 2 semanas |
| **Fase 3** | Execution Agent + Test Runner MCP personalizado | Agente que genera y ejecuta tests | 3 semanas |
| **Fase 4** | Evaluation Agent + Memoria long-term (Mem0) | Sistema que aprende entre sesiones | 3 semanas |
| **Fase 5** | Code Modifier Nivel 2-3 + Rollback automático | Agente que refactoriza con seguridad | 4 semanas |
| **Fase 6** | Adapters multi-stack + AGENT_CONFIG portable | Versión reutilizable en cualquier proyecto | 2 semanas |

> **Recomendación:** La Fase 1 ya produce valor demostrable. Un README generado de forma autónoma es suficiente para validar el concepto con stakeholders, presentarlo en una demo o usarlo como base de una tesis.

***

# 12. CONCLUSIÓN

Este proyecto materializa el concepto de un **ingeniero de software autónomo asistido por IA**: no solo genera texto sobre el código, sino que lo entiende a nivel sintáctico (AST), lo percibe a nivel visual (Playwright), aprende de sus propias acciones (memoria persistente) y mejora progresivamente sin intervención humana constante.

El `AGENT_CONFIG.yaml` como punto de entrada único, el sistema de niveles de mejora como mecanismo de seguridad, y la memoria cross-sesión como motor de aprendizaje son las tres decisiones de diseño que le dan solidez, escalabilidad y diferenciación real al sistema.

La implementación progresiva por fases garantiza que cada etapa entrega valor real e independiente, minimizando el riesgo de un proyecto que "nunca termina". Y la arquitectura basada en MCP asegura que cada componente sea reemplazable sin afectar al resto del sistema.

> *"Un agente que no solo entiende el software, sino que lo mejora activamente y aprende de cada iteración."*
