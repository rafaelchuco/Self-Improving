# ROADMAP DE IMPLEMENTACION DETALLADO (FASE POR FASE)

## 0. Contexto integrado

Este documento aterriza la seccion de roadmap del informe tecnico y consolida el contexto operativo definido para el proyecto.

Fuentes base usadas:
- `.vscode/Documents/informeTecnico.md` (seccion 11, mas contexto de arquitectura y agentes)
- `.vscode/Documents/contexto.md` (modelo local de instalacion, ciclo cerrado, modulos internos, riesgos y blueprint tecnico)

## 1. Premisas de arquitectura (no negociables)

1. El agente no se conecta remotamente a repositorios arbitrarios.
2. El agente vive como carpeta base reutilizable y se activa sobre un proyecto abierto en VS Code.
3. La entrada humana minima es un `AGENT_CONFIG.yaml` en la raiz del proyecto objetivo.
4. El ciclo es cerrado: observar -> planear -> actuar -> validar -> evaluar -> aprender -> repetir.
5. Se respeta control de riesgo por niveles:
   - Nivel 1: docs y analisis seguro
   - Nivel 2: tests y mejoras controladas
   - Nivel 3: refactor y cambios de mayor impacto
6. Ninguna fase avanza sin criterios de aceptacion cumplidos.
7. Todo cambio de codigo debe ser reversible (branch, rollback, trazabilidad).

## 2. Vista global de fases

Duracion total estimada: 17 semanas.

| Fase | Objetivo | Entregable macro | Duracion |
|---|---|---|---|
| Fase 0 | Setup base: LangGraph + Filesystem MCP + Git MCP | Agente que lee repo e imprime mapa | 1 semana |
| Fase 1 | Discovery Agent completo + README | README generado automaticamente | 2 semanas |
| Fase 2 | Perception Agent + Playwright MCP | Mapa de pantallas con screenshots | 2 semanas |
| Fase 3 | Execution Agent + Test Runner MCP | Agente que genera y ejecuta tests | 3 semanas |
| Fase 4 | Evaluation Agent + memoria long-term | Sistema que aprende entre sesiones | 3 semanas |
| Fase 5 | Code Modifier Nivel 2-3 + rollback | Refactor seguro con validacion | 4 semanas |
| Fase 6 | Adapters multi-stack + config portable | Version reutilizable en cualquier proyecto | 2 semanas |

## 3. Ejecucion fase por fase (uno por uno)

### Fase 0 - Setup base

Objetivo:
Construir la base tecnica minima para que el agente lea un proyecto local y pueda operar con un primer loop muy simple.

Alcance funcional:
- Crear esqueleto del agente (runtime Python 3.11+).
- Definir estado base de LangGraph.
- Integrar Filesystem MCP y Git MCP.
- Implementar comando de arranque contra un workspace local.
- Generar salida de "mapa inicial" del repo.

Entregables:
- CLI de ejecucion del agente (ejemplo: `python agent/run.py --workspace <path>`).
- Primer grafo funcional (discovery basico).
- Adaptador de lectura de archivos y estructura.
- Adaptador de historial git minimo.
- Log de ejecucion por corrida.

Plan sugerido (1 semana):
1. Dia 1: scaffold del repositorio y convenciones de carpetas.
2. Dia 2: estado y nodos minimos de LangGraph.
3. Dia 3: conexion a Filesystem MCP.
4. Dia 4: conexion a Git MCP.
5. Dia 5: comando E2E de prueba con salida JSON del mapa.

Criterios de aceptacion:
- El agente corre desde terminal en local.
- Lista estructura base del proyecto objetivo.
- Identifica archivos clave (`package.json`, `pom.xml`, `requirements.txt`, etc.) si existen.
- Reporta al menos: stack preliminar, carpetas principales y archivos criticos.
- Sin modificar codigo del proyecto objetivo.

Riesgos y mitigacion:
- Riesgo: stack no detectado.
  Mitigacion: fallback a "stack desconocido" + lista de evidencia encontrada.
- Riesgo: rutas de workspace invalidas.
  Mitigacion: validacion temprana del path y error claro.

Definicion de "Done":
Existe una ejecucion repetible que imprime mapa del repo y deja evidencia en logs.

---

### Fase 1 - Discovery completo + README automatico

Objetivo:
Lograr entendimiento profundo del proyecto desde codigo, configuraciones, docs y estructura para generar documentacion util de inmediato.

Alcance funcional:
- Discovery Agent completo con extraccion de contexto real.
- Deteccion de stack por evidencia (dependencias, build files, configuraciones).
- Lectura de codigo y docs existentes.
- Priorizacion de modulos y zonas de riesgo.
- Generation inicial de `README.md` con informacion verificable.

Entregables:
- JSON de discovery enriquecido (stack, rutas, modulos, tests encontrados, hotspots).
- README generado automaticamente y versionado.
- Primer `docs/architecture.md` basico.
- Reporte de oportunidades de mejora L1/L2 (sin ejecutar cambios aun).

Plan sugerido (2 semanas):
1. Semana 1: parser de evidencia de stack y mapeo estructural completo.
2. Semana 1: lectura de docs existentes y alineacion de terminologia.
3. Semana 2: plantilla de README dinamica segun tipo de proyecto.
4. Semana 2: generacion de reporte de oportunidades y gaps.

Criterios de aceptacion:
- README generado describe instalacion, ejecucion, estructura y modulos principales.
- El contenido del README es trazable al analisis real del repo.
- Detecta si hay o no tests existentes.
- Identifica al menos 3 oportunidades de mejora concretas.

Riesgos y mitigacion:
- Riesgo: README muy generico.
  Mitigacion: bloquear contenido no sustentado en evidencia del repo.
- Riesgo: info vieja en docs existentes.
  Mitigacion: marcar contradicciones detectadas en reporte.

Definicion de "Done":
El proyecto obtiene valor demostrable inmediato con README auto-generado y mapa tecnico util.

---

### Fase 2 - Perception Agent + analisis visual

Objetivo:
Agregar percepcion de UI en ejecucion para complementar el analisis de codigo con evidencia visual y de DOM.

Alcance funcional:
- Integrar Playwright MCP en modo de exploracion controlada.
- Levantar app local con `start_command` desde `AGENT_CONFIG.yaml`.
- Navegar por rutas iniciales y hints definidos por usuario.
- Soportar login guiado por credenciales de entorno de desarrollo.
- Capturar screenshots y extraer contexto del DOM.

Entregables:
- Mapa de pantallas (ruta + nombre + screenshot).
- Flujos detectados (por ejemplo: login -> dashboard -> reportes).
- Lista de problemas UX/UI observados.
- Referencias entre pantalla y componentes/codigo relacionado.

Plan sugerido (2 semanas):
1. Semana 1: bootstrap browser + navegacion base + capturas.
2. Semana 1: login opcional por config + manejo de sesion persistente.
3. Semana 2: ejecucion de navigation_hints + exploracion adicional.
4. Semana 2: analisis por pantalla y consolidacion de hallazgos.

Criterios de aceptacion:
- El agente puede levantar la app y detectar disponibilidad de URL local.
- Recorre al menos flujo principal y toma evidencia visual.
- Genera inventario de pantallas con metadata util.
- Reporta hallazgos UI accionables (no solo descripcion).

Riesgos y mitigacion:
- Riesgo: app no levanta en entorno local.
  Mitigacion: diagnostico automatico (comando, puerto, logs) y salida guiada.
- Riesgo: login inestable.
  Mitigacion: retries controlados + selectors configurables.

Definicion de "Done":
Existe mapa visual navegable con screenshots y problemas priorizados.

---

### Fase 3 - Execution Agent + Test Runner MCP

Objetivo:
Permitir que el agente materialice mejoras de riesgo controlado y las valide automaticamente con tests.

Alcance funcional:
- Crear Test Runner MCP personalizado (`run_jest`, `run_pytest`, `run_maven`, cobertura).
- Implementar protocolo de ejecucion segura en branch por iteracion.
- Generar tests basicos desde flujos o gaps detectados.
- Ejecutar tests antes y despues de cada cambio.

Entregables:
- Servidor MCP de test runner funcionando.
- Pipeline de iteracion: plan -> cambio -> test -> decision.
- Commits estructurados por iteracion del agente.
- Registro de fallos y reintentos (maximo 3).

Plan sugerido (3 semanas):
1. Semana 1: Test Runner MCP multi-framework.
2. Semana 1-2: motor de ejecucion segura en branches.
3. Semana 2: generacion de tests iniciales por flujo principal.
4. Semana 3: consolidacion de reportes y politicas de retry.

Criterios de aceptacion:
- Ningun cambio se aplica directo a rama principal.
- Todo cambio tiene evidencia de validacion.
- Si tests fallan, el sistema revierte o stashea y registra causa.
- Al menos un flujo principal queda cubierto por test generado.

Riesgos y mitigacion:
- Riesgo: falsa confianza por tests insuficientes.
  Mitigacion: score minimo de cobertura por area critica.
- Riesgo: loops de error infinitos.
  Mitigacion: limite estricto de retries + escalado a humano.

Definicion de "Done":
El agente ya no solo describe: tambien crea cambios y los valida automaticamente.

---

### Fase 4 - Evaluation Agent + memoria long-term

Objetivo:
Cerrar el loop de aprendizaje para mejorar decisiones futuras y evitar reprocesamiento innecesario.

Alcance funcional:
- Evaluation Agent con metricas funcionales y cualitativas.
- Integrar memoria long-term (Mem0 + Qdrant) para patrones reutilizables.
- Integrar memoria estructural (SQLite) para relaciones del proyecto.
- Persistir lecciones por iteracion y por componente.

Entregables:
- Evaluacion automatica por iteracion (PASS/FAIL + causa).
- Base de conocimiento de patrones efectivos/inefectivos.
- Consulta de memoria para reuso de estrategias.
- Historial estructurado de cambios y resultados.

Plan sugerido (3 semanas):
1. Semana 1: modelo de evaluacion y esquema de metricas.
2. Semana 1-2: persistencia de eventos y lecciones aprendidas.
3. Semana 2: recuperacion de memoria en planning.
4. Semana 3: validacion de mejora entre sesiones.

Criterios de aceptacion:
- El agente consulta memoria antes de planear nuevas acciones.
- Se registran patrones reutilizables por tipo de componente.
- Se puede responder: que funciono, que fallo, y donde.
- Se demuestra ahorro de reprocesamiento entre sesiones.

Riesgos y mitigacion:
- Riesgo: memoria ruidosa o contradictoria.
  Mitigacion: score de confianza por evidencia y fecha.
- Riesgo: costo alto por contexto excesivo.
  Mitigacion: resumen por embeddings + recuperacion selectiva.

Definicion de "Done":
El sistema aprende entre sesiones y mejora la calidad de sus decisiones.

---

### Fase 5 - Code Modifier Nivel 2/3 + rollback avanzado

Objetivo:
Escalar a mejoras de mayor impacto (refactor y cambios estructurales) con guardrails robustos.

Alcance funcional:
- Motor de modificacion de codigo con estrategia incremental.
- Soporte de refactor en componentes grandes y hotspots.
- Politica avanzada de rollback automatico.
- Gate de calidad previo a merge (tests + checks + evidencia visual).

Entregables:
- Libreria de patrones de refactor seguros.
- Flujo de rollback completo y auditable.
- Reporte antes/despues por archivo y por comportamiento.
- Mejora aplicada en al menos 2 hotspots reales del proyecto.

Plan sugerido (4 semanas):
1. Semana 1: framework de refactor incremental y diffs pequenos.
2. Semana 2: ejecucion en casos L2 controlados.
3. Semana 3: ejecucion en casos L3 con guardrails.
4. Semana 4: hardening del rollback y pruebas de regresion.

Criterios de aceptacion:
- Cambios L2/L3 pasan validacion automatica.
- Rollback se ejecuta automaticamente ante regresion.
- Los diffs son explicables y trazables por objetivo.
- No se degrada comportamiento principal del sistema.

Riesgos y mitigacion:
- Riesgo: regresiones silenciosas.
  Mitigacion: comparacion funcional + visual + contract tests.
- Riesgo: diffs demasiado grandes.
  Mitigacion: limite de tamano por iteracion y particion en lotes.

Definicion de "Done":
El agente refactoriza con seguridad real y capacidad de recuperacion inmediata.

---

### Fase 6 - Adapters multi-stack + AGENT_CONFIG portable

Objetivo:
Convertir el sistema en una solucion reutilizable entre proyectos y stacks sin rehacer el core.

Alcance funcional:
- Definir adapters por stack (frontend, backend, fullstack).
- Estandarizar `AGENT_CONFIG.yaml` portable.
- Crear estrategia de autodeteccion + fallback por proyecto.
- Empaquetar distribucion para onboarding rapido.

Entregables:
- Adapters iniciales (ejemplo: React/Vite, Java/Spring, Python/FastAPI).
- Plantillas de config por tipo de proyecto.
- Guia de instalacion de 10-15 minutos.
- Demo end-to-end en al menos 2 proyectos distintos.

Plan sugerido (2 semanas):
1. Semana 1: contrato comun de adapter + implementaciones iniciales.
2. Semana 1: versionado y validacion de schema de config.
3. Semana 2: pruebas cruzadas en multiples proyectos.
4. Semana 2: documentacion final de uso portable.

Criterios de aceptacion:
- El agente se instala y ejecuta con baja friccion en proyectos distintos.
- El mismo core funciona cambiando solo adapter/config.
- Se reduce tiempo de onboarding de nuevo proyecto.
- Se publica guia operativa reproducible.

Riesgos y mitigacion:
- Riesgo: exceso de logica especifica por stack.
  Mitigacion: interfaz de adapter estricta + tests de contrato.
- Riesgo: config compleja para usuario final.
  Mitigacion: defaults inteligentes y validacion guiada.

Definicion de "Done":
El sistema queda realmente portable y reusable, listo para escalar a nuevos repos.

## 4. Reglas de paso entre fases (gating)

Para ejecutar "uno por uno" sin saltos de riesgo:

1. No iniciar Fase N+1 sin cerrar criterios de aceptacion de Fase N.
2. Guardar evidencia de cierre por fase (artefactos + logs + demo).
3. Mantener changelog del agente y decision log tecnico.
4. Si una fase falla en estabilidad, se vuelve a hardening antes de avanzar.

## 5. KPIs minimos por fase

- Fase 0: tasa de corridas exitosas del agente base >= 90%.
- Fase 1: calidad de README (campos clave completos) >= 95%.
- Fase 2: cobertura de rutas criticas exploradas >= 80%.
- Fase 3: cambios con validacion automatica >= 100%.
- Fase 4: reutilizacion de patrones aprendidos en sesiones futuras >= 50%.
- Fase 5: regresiones post-refactor <= 5% por iteracion.
- Fase 6: tiempo de onboarding por proyecto <= 15 minutos.

## 6. Recomendacion de inicio inmediato

Orden de ejecucion sugerido a partir de hoy:

1. Cerrar Fase 0 con un demo funcional en repo local.
2. Ejecutar Fase 1 como primera entrega de valor visible a stakeholders.
3. Preparar Fase 2 solo cuando `AGENT_CONFIG.yaml` ya este estable.

Nota clave:
La Fase 1 es el primer hito de valor demostrable (README automatico + contexto del sistema) y debe usarse como baseline para validar direccion de producto/tesis.