# FADUA BI Assistant

Asistente analitico orientado a BI para responder consultas en lenguaje natural sobre metricas de campanas publicitarias usando datos reales en MySQL.

El proyecto fue construido como una aplicacion full-stack:

- `FastAPI` sirve la API y la UI estatica
- `LangGraph` orquesta el flujo del agente
- `OpenAI` resuelve clasificacion y composicion de respuestas
- `Langfuse` aporta prompt management y observabilidad
- `MySQL` es la fuente de datos para metricas, rankings, breakdowns y forecast

## Objetivo

Resolver el challenge de un chatbot analitico capaz de contestar preguntas como:

- metricas basicas
- analisis temporales
- analisis relacionales
- proyecciones del proximo mes

La prioridad del enfoque es combinar:

- respuestas utiles para demo
- arquitectura mantenible
- tools deterministicas para consultas de negocio
- observabilidad real del flujo
- guardrails para dominio, ambiguedad y seguridad

## Stack

- Python 3.10
- FastAPI
- Uvicorn
- LangGraph
- LangChain Core
- OpenAI SDK
- Langfuse
- PyMySQL
- Pandas
- HTML, CSS y JavaScript vanilla
- Chart.js en frontend para visualizaciones

## Capacidades actuales

El asistente puede responder:

- ventas, leads, ingresos, costo publicitario, clics e impresiones acumuladas
- ratios agregados como ROAS, CTR, CPA, CPL y tasa de conversion
- mejor o peor mes para una metrica soportada
- patrones relacionales como "pocos leads y muchas ventas"
- breakdown por canal
- breakdown por vehiculo, tipo o modelo
- forecast del proximo mes para leads y ventas
- consultas flexibles con varias metricas y agrupacion por mes, tipo o modelo
- filtros por periodo (ej. "en marzo 2026", "en 2025") y por tipo/modelo de vehiculo

Las consultas flexibles se resuelven con un contrato tipado (metricas + dimension +
filtros) que un compilador deterministico traduce a SQL parametrizado sobre una
allowlist. El LLM nunca escribe SQL: es un semantic layer minimalista.

Tambien expone:

- `thread_id` para contexto corto entre preguntas
- metadata util para demo
- enlace directo al trace de Langfuse
- chart payload para ciertos intents

## Arquitectura

La aplicacion corre como un servicio unico:

1. El frontend envia una pregunta a `POST /api/chat`
2. FastAPI delega la ejecucion al assistant
3. LangGraph procesa la consulta en un grafo con estado
4. El planner selecciona una tool deterministica
5. La tool consulta MySQL y devuelve datos estructurados
6. El answer composer genera la respuesta final
7. Langfuse registra prompts, spans, metadata y trace URL

### Flujo del grafo

El grafo principal se define en [app/agent/graph/builder.py](app/agent/graph/builder.py) y sigue este pipeline:

1. `normalize_input`
2. `classify_intent_and_entities`
3. `resolve_context`
4. `plan_tools`
5. `execute_tools`
6. `compose_answer`
7. `build_chart_payload`

Si aparece un error o una condicion bloqueante, el flujo deriva a `error_handler`.

### Criterio de diseno

La orquestacion no usa un agente ReAct libre para decidir cualquier accion. En cambio:

- el LLM se usa para clasificar y redactar
- las tools disponibles son cerradas y tipadas
- el planner mapea intents a tools de forma deterministica

Este enfoque reduce alucinaciones y hace el comportamiento mas auditable para una demo tecnica.

## Guardrails

El proyecto implementa guardrails en capas:

- bloqueo de prompt injection
- bloqueo de pedidos sensibles como `.env`, passwords o tokens
- bloqueo de ejecucion arbitraria o SQL destructivo
- deteccion de consultas ambiguas que requieren reformulacion
- salida estructurada para clasificacion LLM
- planner cerrado a un conjunto fijo de tools

La logica principal vive en:

- [app/agent/guardrails.py](app/agent/guardrails.py)
- [app/agent/graph/nodes/classification.py](app/agent/graph/nodes/classification.py)
- [app/agent/graph/nodes/planning.py](app/agent/graph/nodes/planning.py)

## Prompt Management con Langfuse

Los prompts estan modelados localmente en:

- [app/agent/prompting/catalog.py](app/agent/prompting/catalog.py)

Y se resuelven via Langfuse en:

- [app/agent/prompting/client.py](app/agent/prompting/client.py)

El comportamiento actual es:

- se busca el prompt por `name` y `label`
- se usa `production` como label de runtime
- si Langfuse no esta disponible o no resuelve el prompt, se usa fallback local
- cada respuesta registra que prompt y version participaron del trace

Prompts principales:

- `bi-assistant-intent-classifier`
- `bi-assistant-answer-composer`
- `bi-assistant-fallback`
- `bi-assistant-forecast-explainer`

Para sincronizar los prompts locales hacia Langfuse:

```bash
python scripts/sync_langfuse_prompts.py
```

IMPORTANTE: el runtime resuelve los prompts desde Langfuse usando el label
`production`. Si un prompt existe en Langfuse, esa version tiene prioridad sobre el
catalogo local. Por lo tanto, cualquier cambio en `catalog.py` (por ejemplo, nuevas
capacidades del clasificador) solo se activa en la app desplegada despues de correr
el script de sync, que crea una nueva version y la publica con el label `production`.

## Observabilidad con Langfuse

La integracion de tracing vive en:

- [app/observability/langfuse.py](app/observability/langfuse.py)
- [app/agent/assistant.py](app/agent/assistant.py)

Que se registra:

- trace por request de chat
- spans por nodo del grafo
- tool calls
- prompts y versiones
- modelo utilizado
- razones de clasificacion, planning y errores
- trace URL devuelta al frontend

Esto permite inspeccionar por que una consulta:

- fue aceptada
- quedo fuera de alcance
- fue bloqueada por guardrail
- disparo una tool especifica

## Estructura del proyecto

```text
app/
  agent/
    graph/
    guardrails.py
    llm/
    prompting/
    tools/
  api/
  core/
  domain/
  observability/
  repositories/
  schemas/
  services/
  static/
scripts/
tests/
render.yaml
requirements.txt
```

Resumen por capa:

- `app/api`: rutas HTTP
- `app/agent`: grafo, prompting, LLM y tools
- `app/domain`: logica analitica y forecast
- `app/repositories`: acceso a MySQL
- `app/observability`: integracion con Langfuse
- `app/static`: interfaz web tipo chat

## Endpoints

- `GET /` -> UI web
- `GET /api/health` -> estado general de la app y la DB
- `GET /api/coverage` -> cobertura del dataset
- `GET /api/kpis` -> snapshot basico de KPIs
- `GET /api/forecast` -> forecast deterministico
- `POST /api/chat` -> endpoint principal del asistente

## Setup local

### 1. Crear entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables

Usar [.env.example](.env.example) como base:

```bash
cp .env.example .env
```

Variables criticas (minimo para levantar la app):

- `OPENAI_API_KEY`
- `MYSQL_HOST`
- `MYSQL_DB`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST`

El set completo (25 variables, incluye `OPENAI_MODEL`, timeouts de OpenAI y MySQL,
`MYSQL_TABLE`, `APP_*`, `LANGFUSE_PROMPT_LABEL`, `LANGFUSE_PROMPT_CACHE_TTL_SECONDS`,
etc.) esta documentado con valores por defecto en [.env.example](.env.example). Si el
LLM o Langfuse no estan configurados, la app degrada a fallbacks deterministicos.

### 4. Levantar la app

```bash
uvicorn app.main:app --reload
```

Luego abrir:

```text
http://127.0.0.1:8000
```

## Tests

El proyecto incluye tests focalizados sobre decisiones del agente:

```bash
python -m unittest discover -s tests -v
```

Cobertura actual (22 tests unitarios sobre decisiones del agente):

- guardrails
- razones de clasificacion
- razones de planning
- comportamiento de intents bloqueados
- normalizacion de filtros de fecha
- validacion y ranking del compilador de consultas flexibles

Alcance: los tests apuntan a las decisiones deterministicas del agente (clasificacion
por reglas, planning, guardrails y compilador flexible). Todavia no hay un test
end-to-end del grafo completo ni un harness de evaluaciones (evals) sobre la
clasificacion LLM; ambos figuran en Proximos pasos.

Para un ensayo rapido contra la base real (sin costo de LLM), que valida las
respuestas deterministicas de las consultas clave de la demo:

```bash
python scripts/smoke_queries.py
```

## Deploy en Render

El repo esta preparado para deploy monolitico en Render:

- [render.yaml](render.yaml)
- [.python-version](.python-version)

### Estrategia recomendada

No separar frontend y backend para la primera version.

Ventajas:

- una sola URL
- sin complejidad extra de CORS
- el frontend ya consume `/api/chat` en la misma origin
- despliegue mas simple para demo

### Pasos resumidos

1. Subir el repo a GitHub
2. Entrar a Render
3. `New +` -> `Blueprint`
4. Seleccionar el repositorio
5. Confirmar el `render.yaml`
6. Cargar secretos:
   - `OPENAI_API_KEY`
   - `MYSQL_PASSWORD`
   - `LANGFUSE_PUBLIC_KEY`
   - `LANGFUSE_SECRET_KEY`
7. Deploy
8. Probar:
   - `/api/health`
   - `/`
   - una consulta en el chat

### Start command

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Nota sobre free tier

Render puede dormir el servicio gratuito tras un periodo sin trafico. Para una demo en vivo conviene precalentar el servicio unos minutos antes.

## Consultas de ejemplo

- `Cuantas ventas tenemos al dia de hoy?`
- `Cual fue el mes de mayores ventas?`
- `En que mes tuvimos pocos leads pero muchas ventas?`
- `Cual es la cantidad de leads y ventas proyectadas del proximo mes?`
- `Mostrame el rendimiento por canal`
- `Cual fue el mejor modelo por ventas?`
- `Cual es el ROAS acumulado?`
- `Cuantas ventas hubo en marzo 2026?`
- `Comparame ventas y leads por mes en 2025`
- `Mostrame ingresos y ROAS por tipo de vehiculo`

## Limitaciones actuales

- el dominio es cerrado a las tools implementadas (por diseno de seguridad)
- no hay SQL libre generado por el LLM; las consultas flexibles pasan por un
  compilador deterministico sobre una allowlist
- los filtros temporales aceptan periodos explicitos (ano, mes, fecha); los periodos
  relativos ("ultimo mes") todavia no se resuelven automaticamente
- la dimension `channel` no esta disponible en el tool flexible (se cubre con el
  tool dedicado de canal)
- la memoria es de corto plazo por `thread_id`
- el forecast es deterministico y simple, pensado para demo y explicabilidad
- el checkpointer actual es `InMemorySaver`, no persistente entre reinicios

## Proximos pasos naturales

- persistir memoria y estado en un store real
- ampliar composicion de tools para preguntas mas libres
- agregar filtros por fecha, canal o vehiculo desde lenguaje natural
- incorporar evaluaciones automaticas
- endurecer aun mas guardrails y testing

## Licencia

Uso interno y de evaluacion tecnica para challenge.
