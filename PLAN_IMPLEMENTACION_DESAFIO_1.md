# Plan de Implementacion - Challenge 1 - BI Assistant

## 1. Objetivo del plan

Este documento define un plan de implementacion detallado, incremental y verificable para construir el BI Assistant del challenge.

El objetivo es avanzar por fases, con entregables claros y siguiendo buenas practicas en:

- arquitectura de software;
- FastAPI;
- LangGraph;
- observabilidad con Langfuse;
- prompt management;
- seguridad;
- guardrails;
- testing;
- manejo de errores;
- calidad de codigo;
- preparacion para demo y defensa tecnica.

Este plan esta pensado para que podamos:

- implementar de forma ordenada;
- reducir riesgo temprano;
- validar rapido cada capa;
- marcar progreso real con checkboxes.

---

## 2. Principios de implementacion

Antes de ejecutar cualquier fase, estas reglas guian toda la implementacion:

- [x] Mantener el frontend libre de secretos.
- [x] Centralizar configuracion en variables de entorno.
- [x] Usar el backend como unico punto de acceso a MySQL y al proveedor LLM.
- [ ] Tratar el LLM como capa de interpretacion y redaccion, no como motor de calculo principal.
- [x] Implementar tools tipadas y auditables en lugar de SQL libre generado sin control.
- [ ] Diseñar el agente con flujos controlados, no con autonomia ilimitada.
- [ ] Instrumentar observabilidad desde el inicio para no agregarla tarde.
- [ ] Mantener prompts versionados y desacoplados del codigo mediante Langfuse.
- [x] Diseñar degradacion elegante ante fallos de BD, LLM u observabilidad.
- [x] Priorizar respuestas correctas y explicables por sobre complejidad innecesaria.
- [x] Implementar validacion fuerte de inputs y outputs.
- [x] Asegurar codigo modular, testeable y facil de explicar en entrevista.

---

## 3. Criterios de terminado global

El proyecto se considerara listo cuando cumpla todos estos criterios:

- [ ] El sistema responde preguntas analiticas basicas sobre la base real.
- [ ] El sistema soporta analisis temporal.
- [ ] El sistema soporta analisis relacional.
- [ ] El sistema soporta proyeccion del proximo mes.
- [ ] El sistema mantiene contexto conversacional basico por `thread_id`.
- [ ] Las respuestas incluyen contexto de periodo y ultimo dato disponible cuando aplica.
- [ ] El frontend funciona como interfaz de chat util para demo.
- [ ] Langfuse registra trazas, nodos, tools, errores y prompts usados.
- [ ] Los prompts viven en Langfuse con versionado y labels.
- [ ] El sistema maneja errores sin romper la demo.
- [ ] La arquitectura puede explicarse con claridad tecnica en una entrevista.

---

## 4. Fase 0 - Preparacion inicial y definicion de base

### Objetivo

Preparar el entorno, cerrar decisiones tecnicas y dejar una base limpia y consistente para trabajar.

### Alcance

- definir stack final;
- preparar estructura del repo;
- configurar dependencias iniciales;
- establecer convenciones y criterios de calidad.

### Tareas

- [x] Confirmar stack principal:
  - `Python`
  - `FastAPI`
  - `LangGraph`
  - `LangChain`
  - `Langfuse`
  - `PyMySQL` o driver equivalente
  - `pandas`
  - `Chart.js`
- [x] Definir proveedor LLM para desarrollo y demo.
- [x] Crear entorno virtual del proyecto.
- [x] Crear `requirements.txt` o estrategia de dependencias equivalente.
- [x] Crear estructura base de carpetas del proyecto.
- [x] Crear `.env.example` con todas las variables necesarias.
- [x] Definir convenciones de nombres, logs y manejo de errores.
- [x] Definir formato de respuesta de la API desde el inicio.
- [x] Definir criterio de sesiones mediante `thread_id`.
- [x] Crear documento corto de arquitectura resumida para referencia rapida.

### Buenas practicas de esta fase

- [x] No hardcodear secretos.
- [x] No mezclar logica de negocio con logica de infraestructura.
- [x] Preparar el proyecto pensando en escalabilidad aunque el challenge sea pequeno.
- [x] Mantener el arbol de archivos ordenado desde el primer dia.

### Entregables

- [x] Estructura inicial del repo creada.
- [x] Dependencias definidas.
- [x] Variables de entorno documentadas.
- [x] Base lista para empezar a codificar.

---

## 5. Fase 1 - Esqueleto de FastAPI y base web

### Objetivo

Levantar la aplicacion web y dejar lista la capa HTTP sobre la que se montara el agente.

### Alcance

- app FastAPI;
- rutas iniciales;
- healthcheck;
- servicio de archivos estaticos;
- frontend HTML base.

### Tareas

- [x] Crear `app/main.py`.
- [x] Inicializar `FastAPI` con metadata basica del proyecto.
- [x] Configurar middleware necesario.
- [x] Crear endpoint `GET /api/health`.
- [x] Crear endpoint `GET /api/coverage` placeholder o base.
- [x] Configurar servicio de archivos estaticos.
- [x] Crear `index.html` inicial del chat.
- [x] Crear `styles.css` base.
- [x] Crear `app.js` base con envio de requests.
- [x] Conectar `POST /api/chat` con una respuesta mock temporal.
- [x] Definir esquemas Pydantic para request y response.

### Buenas practicas FastAPI

- [x] Usar tipado en endpoints y modelos.
- [x] Separar `routes`, `schemas`, `services` y `config`.
- [x] Mantener validacion en Pydantic, no dispersa en el codigo.
- [x] Preparar respuestas estructuradas desde el inicio.
- [x] No mezclar HTML inline con la logica del backend.
- [x] Mantener endpoints pequenos y orquestadores, no con logica pesada.

### Manejo de errores

- [x] Definir manejador global de excepciones HTTP.
- [x] Definir respuesta consistente para errores controlados.
- [x] Evitar exponer stack traces al cliente.

### Entregables

- [x] Aplicacion FastAPI arrancando localmente.
- [x] Frontend base accesible.
- [x] Endpoint `/api/chat` disponible con contrato definido.

---

## 6. Fase 2 - Conexion a MySQL y capa de acceso a datos

### Objetivo

Conectar la base real y encapsular acceso a datos de forma segura, reutilizable y mantenible.

### Alcance

- conexion a MySQL;
- health basico de BD;
- funciones de acceso;
- coverage de datos;
- primeras consultas estructuradas.

### Tareas

- [x] Crear modulo de configuracion de BD.
- [x] Implementar fabrica o helper de conexion.
- [x] Configurar timeouts razonables.
- [x] Implementar funcion de test de conexion.
- [x] Crear `get_data_coverage`.
- [x] Crear primeras consultas de KPI agregados.
- [x] Encapsular queries en una capa `database.py` o equivalente.
- [x] Usar SQL parametrizado.
- [x] Agregar logs de consultas de alto nivel sin filtrar secretos.
- [x] Definir errores especificos de acceso a datos.

### Buenas practicas de acceso a datos

- [x] Evitar SQL concatenado con input del usuario.
- [x] Mantener queries auditables y faciles de leer.
- [x] Separar SQL de la interpretacion del lenguaje natural.
- [x] Devolver estructuras limpias y consistentes hacia capas superiores.
- [x] Documentar el rango de datos disponible.

### Guardrails

- [x] No permitir escrituras en la base.
- [x] Limitar el acceso a la tabla necesaria.
- [x] Preparar el sistema para funcionar idealmente con usuario read-only.

### Entregables

- [x] Conexion estable a MySQL.
- [x] Cobertura del dataset disponible desde la API.
- [x] Capa de datos base funcionando.

---

## 7. Fase 3 - Implementacion de tools analiticas deterministicas

### Objetivo

Crear las herramientas analiticas que seran la base real de las respuestas del agente.

### Alcance

- KPIs basicos;
- agregaciones temporales;
- comparativas;
- patrones relacionales;
- salidas estructuradas.

### Tareas

- [x] Implementar `get_basic_kpis`.
- [x] Implementar `get_monthly_aggregates`.
- [x] Implementar `get_channel_breakdown`.
- [x] Implementar `get_vehicle_breakdown`.
- [x] Implementar `find_best_or_worst_period`.
- [x] Implementar `find_relational_pattern`.
- [x] Crear helpers para calculos derivados:
  - `ctr`
  - `cpl`
  - `cpa`
  - `roas`
  - `conversion_rate`
- [x] Estandarizar el formato de salida de todas las tools.
- [x] Agregar metadata util:
  - periodo
  - filtros aplicados
  - advertencias
  - unidad de medida

### Buenas practicas de tools

- [x] Hacer tools pequenas, enfocadas y tipadas.
- [x] Evitar herramientas demasiado genericas.
- [x] No mezclar redaccion de respuesta con calculo analitico.
- [x] Devolver datos estructurados y faciles de testear.
- [x] Documentar supuestos de cada tool.

### Manejo de errores

- [x] Si no hay datos, devolver respuesta controlada, no excepcion generica.
- [x] Si una consulta da valores nulos o inesperados, reportarlo como warning.
- [x] Validar rangos temporales antes de ejecutar.

### Entregables

- [x] Tools analiticas listas para ser llamadas por LangGraph.
- [x] Casos basicos del challenge resolubles sin LLM.

---

## 8. Fase 4 - Modulo predictivo

### Objetivo

Agregar la capacidad de proyectar leads y ventas del proximo mes con una metodologia defendible.

### Alcance

- agregacion mensual;
- deteccion de outliers;
- forecast base;
- explicacion metodologica;
- salida estructurada.

### Tareas

- [x] Crear modulo `forecast.py`.
- [x] Implementar agregacion mensual para series de leads y ventas.
- [x] Implementar deteccion de outliers.
- [x] Definir estrategia de atenuacion de outliers.
- [x] Implementar promedio movil ponderado.
- [x] Implementar ajuste estacional suave usando referencia anual cuando exista.
- [x] Generar salida del forecast con:
  - valor proyectado
  - periodo objetivo
  - metodo utilizado
  - warnings
- [x] Validar comportamiento con meses atipicos.
- [x] Preparar texto tecnico resumido para explicar la metodologia.

### Buenas practicas

- [x] Mantener el forecast deterministicamente reproducible.
- [x] No delegar el calculo del forecast al LLM.
- [x] Documentar limitaciones e incertidumbre.
- [x] Evitar sobreprometer precision estadistica.

### Entregables

- [x] Forecast funcional para leads y ventas.
- [x] Respuesta explicable para el requisito predictivo.

---

## 9. Fase 5 - Diseno del estado y del flujo del agente en LangGraph

### Objetivo

Definir el grafo del agente, su estado, sus nodos y su flujo de control.

### Alcance

- estado del agente;
- nodos principales;
- edges;
- memoria corta por sesion;
- compilacion del grafo.

### Tareas

- [x] Crear `graph/state.py`.
- [x] Definir schema del estado del agente.
- [x] Crear `graph/nodes.py`.
- [x] Crear `graph/builder.py`.
- [x] Implementar nodo `normalize_input`.
- [x] Implementar nodo `classify_intent_and_entities`.
- [x] Implementar nodo `resolve_context`.
- [x] Implementar nodo `plan_tools`.
- [x] Implementar nodo `execute_tools`.
- [x] Implementar nodo `compose_answer`.
- [x] Implementar nodo `build_chart_payload`.
- [x] Implementar nodo `error_handler`.
- [x] Conectar edges del flujo principal.
- [x] Compilar el grafo.
- [x] Integrar checkpointer para memoria corta por `thread_id`.

### Buenas practicas LangGraph

- [x] Mantener nodos con una responsabilidad clara.
- [x] Evitar nodos gigantes con demasiada logica.
- [x] Usar estado explicito y tipado.
- [x] Diseñar rutas de error y fallback.
- [x] Preparar el grafo para seguirse facilmente en trazas.
- [x] No depender solo de prompt para controlar el comportamiento.

### Guardrails de flujo

- [x] El nodo de clasificacion no debe ejecutar tools.
- [x] El nodo de planificacion no debe inventar herramientas inexistentes.
- [x] El nodo de ejecucion solo puede llamar tools permitidas.
- [x] El nodo de respuesta solo debe sintetizar resultados reales.

### Entregables

- [x] Grafo base funcionando end-to-end.
- [x] El backend ya puede pasar de pregunta a respuesta mediante LangGraph.

---

## 10. Fase 6 - Integracion del proveedor LLM y salidas estructuradas

### Objetivo

Integrar el modelo de lenguaje con foco en clasificacion, extraccion y redaccion, usando outputs confiables.

### Alcance

- proveedor LLM;
- structured outputs;
- prompts iniciales;
- control de temperatura y estilo.

### Tareas

- [ ] Crear modulo `services/llm.py`.
- [ ] Configurar cliente del proveedor LLM.
- [ ] Definir estrategia de modelo para:
  - clasificacion
  - respuesta final
- [ ] Implementar salida estructurada para clasificacion de intent.
- [ ] Implementar validacion del output del modelo.
- [ ] Configurar temperatura baja.
- [ ] Limitar longitud y ambiguedad de la respuesta.
- [ ] Definir formato comun de mensajes del agente.

### Buenas practicas LLM

- [ ] Usar prompts orientados a datos y no a creatividad.
- [ ] Pedir estructuras claras, no texto libre cuando se necesite control.
- [ ] Validar outputs antes de usarlos.
- [ ] Preparar fallback si el modelo devuelve algo invalido.
- [ ] Mantener trazabilidad del modelo y parametros usados.

### Guardrails

- [ ] El LLM no decide metricas fuera del dominio.
- [ ] El LLM no accede directamente a secretos ni a la base.
- [ ] El LLM no ejecuta SQL libre como camino por defecto.
- [ ] El LLM no responde con numeros no respaldados por tools.

### Entregables

- [ ] Clasificacion y redaccion funcionando con proveedor real.
- [ ] Salidas estructuradas validadas.

---

## 11. Fase 7 - Prompt management con Langfuse

### Objetivo

Mover los prompts relevantes a Langfuse y tratarlos como activos versionados.

### Alcance

- alta de prompts;
- labels;
- retrieval desde la app;
- fallback local;
- vinculacion con trazas.

### Tareas

- [ ] Configurar proyecto de Langfuse.
- [ ] Crear prompt `bi-assistant-intent-classifier`.
- [ ] Crear prompt `bi-assistant-answer-composer`.
- [ ] Crear prompt `bi-assistant-fallback`.
- [ ] Crear prompt `bi-assistant-forecast-explainer`.
- [ ] Definir variables de entrada por prompt.
- [ ] Definir labels como `development`, `staging`, `production`.
- [ ] Implementar cliente de Langfuse para obtener prompts.
- [ ] Agregar fallback local para prompts criticos.
- [ ] Registrar version del prompt usado en cada respuesta.

### Buenas practicas de prompt management

- [ ] No dejar prompts criticos hardcodeados como unica fuente.
- [ ] Versionar cambios de prompt con criterio.
- [ ] Mantener cada prompt con un objetivo claro.
- [ ] Documentar que schema o salida espera cada prompt.
- [ ] Separar prompts de clasificacion de prompts de redaccion.

### Entregables

- [ ] Prompts productivos administrados desde Langfuse.
- [ ] Aplicacion consumiendo prompts versionados.

---

## 12. Fase 8 - Observabilidad end-to-end con Langfuse

### Objetivo

Instrumentar el sistema para poder rastrear todo el ciclo de una consulta.

### Alcance

- traces;
- spans;
- tool calls;
- errores;
- metadata;
- tags.

### Tareas

- [ ] Configurar SDK de Langfuse.
- [ ] Instrumentar request principal del chat.
- [ ] Instrumentar ejecucion del grafo.
- [ ] Instrumentar nodos principales.
- [ ] Instrumentar tools analiticas.
- [ ] Instrumentar modulo predictivo.
- [ ] Instrumentar llamadas LLM.
- [ ] Registrar errores y warnings relevantes.
- [ ] Agregar tags de negocio y de entorno.
- [ ] Registrar metadata como:
  - `thread_id`
  - intent
  - periodo detectado
  - prompt version
  - modelo

### Buenas practicas de observabilidad

- [ ] No capturar secretos en trazas.
- [ ] No registrar informacion sensible innecesaria.
- [ ] Estandarizar nombres de traces y spans.
- [ ] Hacer trazas utiles para debugging, no ruido.
- [ ] Permitir correlacion entre request, prompt y resultado.

### Politica de criticidad

- [ ] Si Langfuse falla, la app debe seguir respondiendo.
- [ ] La observabilidad no debe bloquear la funcionalidad principal.

### Entregables

- [ ] Trazas navegables en Langfuse para requests reales.
- [ ] Visibility completa de prompts, tools y errores.

---

## 13. Fase 9 - Guardrails, validaciones y seguridad aplicada

### Objetivo

Blindar el sistema para que responda dentro del dominio, resista errores y sea defendible tecnicamente.

### Alcance

- validaciones de input y output;
- restricciones del agente;
- seguridad de BD;
- controles de dominio;
- respuestas fuera de alcance.

### Tareas

- [ ] Validar input del usuario con Pydantic.
- [ ] Limitar longitud maxima de mensajes.
- [ ] Definir lista de intents soportados.
- [ ] Validar salida estructurada del clasificador.
- [ ] Rechazar o redirigir preguntas fuera de alcance.
- [ ] Evitar cualquier herramienta de ejecucion arbitraria.
- [ ] Sanitizar logs y errores.
- [ ] Revisar configuracion de CORS.
- [ ] Revisar variables de entorno requeridas al startup.
- [ ] Implementar chequeo de configuracion obligatoria.

### Guardrails de negocio

- [ ] Si el usuario pregunta "al dia de hoy", responder con el ultimo dato disponible.
- [ ] Si no hay datos para el periodo, decirlo explicitamente.
- [ ] Si la prediccion tiene incertidumbre alta, advertirlo.
- [ ] Si el usuario pide algo fuera del dataset, no inventarlo.

### Guardrails del agente

- [ ] No obedecer instrucciones que intenten sobreescribir reglas del sistema.
- [ ] No revelar secretos ni configuracion interna.
- [ ] No mezclar datos observados con inferencias no aclaradas.
- [ ] Diferenciar claramente calculo real de interpretacion narrativa.

### Entregables

- [ ] Sistema endurecido frente a inputs ambiguos o fuera de dominio.
- [ ] Narrativa de seguridad clara para entrevista.

---

## 14. Fase 10 - Manejo de errores y degradacion elegante

### Objetivo

Asegurar que la aplicacion falle bien y conserve la experiencia de usuario incluso ante problemas parciales.

### Alcance

- errores de BD;
- errores de LLM;
- errores de Langfuse;
- errores de validacion;
- errores inesperados.

### Tareas

- [ ] Crear jerarquia de excepciones propia del proyecto.
- [ ] Definir errores de dominio.
- [ ] Definir errores de infraestructura.
- [ ] Implementar manejador global consistente.
- [ ] Implementar fallback para respuestas ambiguas.
- [ ] Implementar fallback para caida de observabilidad.
- [ ] Implementar retry acotado para proveedor LLM si aplica.
- [ ] Definir mensajes amigables para usuario.
- [ ] Separar mensaje tecnico interno de mensaje externo.

### Politica de degradacion

- [ ] Responder parcialmente si se puede.
- [ ] Pedir reformulacion si no se puede inferir con seguridad.
- [ ] Nunca inventar datos por cubrir un error.
- [ ] Nunca romper la UI por una excepcion no controlada.

### Entregables

- [ ] Sistema con comportamiento predecible ante fallos.
- [ ] Flujo de error util y profesional.

---

## 15. Fase 11 - Frontend final para demo

### Objetivo

Construir una interfaz de chat clara, profesional y apta para una demo en vivo.

### Alcance

- chat visual;
- historial;
- preguntas sugeridas;
- indicadores;
- visualizacion de graficos;
- estados de carga y error.

### Tareas

- [ ] Mejorar layout del chat.
- [ ] Agregar mensajes de usuario y asistente bien diferenciados.
- [ ] Agregar loading state.
- [ ] Agregar preguntas sugeridas clickeables.
- [ ] Agregar bloque de metadata:
  - ultimo dato disponible
  - periodo analizado
  - warnings
- [ ] Integrar `Chart.js`.
- [ ] Mostrar graficos cuando el backend los devuelva.
- [ ] Manejar errores visibles en UI de forma clara.
- [ ] Asegurar buena experiencia en desktop y mobile.

### Buenas practicas frontend

- [ ] No saturar de elementos visuales innecesarios.
- [ ] Mantener foco en claridad de respuesta.
- [ ] Hacer que la UI ayude a explicar el analisis.
- [ ] Evitar dependencias excesivas para un challenge acotado.

### Entregables

- [ ] Frontend listo para demo real.
- [ ] Respuestas visuales mas claras y convincentes.

---

## 16. Fase 12 - Testing funcional, tecnico y de regresion

### Objetivo

Validar que la solucion funciona bien en escenarios normales, ambiguos y fallidos.

### Alcance

- tests unitarios;
- tests de integracion;
- pruebas manuales guiadas;
- smoke tests de demo.

### Tareas

- [ ] Testear tools analiticas con casos conocidos.
- [ ] Testear forecast con series controladas.
- [ ] Testear endpoints FastAPI.
- [ ] Testear clasificacion de intents.
- [ ] Testear respuestas a preguntas del challenge.
- [ ] Testear follow-ups contextuales.
- [ ] Testear inputs ambiguos.
- [ ] Testear errores de BD simulados.
- [ ] Testear caida de Langfuse.
- [ ] Testear preguntas fuera de alcance.
- [ ] Crear checklist de smoke test previo a demo.

### Casos minimos obligatorios

- [ ] "Cuantas ventas tenemos al dia de la fecha?"
- [ ] "Cual fue el mes de mayores ventas?"
- [ ] "En que mes tuvimos pocos leads pero muchas ventas?"
- [ ] "Cual es la cantidad de leads y ventas proyectadas del proximo mes?"
- [ ] "Comparame junio con mayo"
- [ ] "Y por canal?"

### Buenas practicas de testing

- [ ] Testear logica critica sin depender del LLM cuando sea posible.
- [ ] Mockear servicios externos cuando convenga.
- [ ] Validar resultados esperados con tolerancias razonables en forecast.
- [ ] Cubrir tanto exito como fallo.

### Entregables

- [ ] Cobertura funcional basica asegurada.
- [ ] Confianza para demo y entrevista tecnica.

---

## 17. Fase 13 - Hardening final y preparacion de entrega

### Objetivo

Pulir la solucion para que quede lista para ejecutar, mostrar y explicar.

### Alcance

- limpieza final;
- documentacion;
- chequeos de configuracion;
- preparacion de demo;
- narrativa tecnica.

### Tareas

- [ ] Revisar codigo no usado.
- [ ] Revisar logs ruidosos.
- [ ] Revisar nombres y consistencia de modulos.
- [ ] Completar README del proyecto.
- [ ] Documentar como correr el proyecto.
- [ ] Documentar variables de entorno.
- [ ] Documentar arquitectura resumida.
- [ ] Documentar metodologia predictiva.
- [ ] Documentar estrategia de seguridad y errores.
- [ ] Preparar script o pasos de demo.
- [ ] Preparar respuestas a preguntas esperables de entrevista.

### Checklist de entrega

- [ ] El proyecto levanta localmente sin pasos ambiguos.
- [ ] El frontend carga correctamente.
- [ ] La API responde.
- [ ] El agente consulta la base real.
- [ ] Langfuse recibe trazas.
- [ ] Los prompts estan versionados.
- [ ] Las preguntas del challenge responden bien.
- [ ] La explicacion tecnica esta lista.

### Entregables

- [ ] Solucion final lista para presentar.
- [ ] Material suficiente para defensa tecnica.

---

## 18. Orden recomendado de ejecucion real

Para reducir riesgo, conviene seguir este orden:

- [x] Fase 0 - Preparacion inicial
- [x] Fase 1 - FastAPI y base web
- [x] Fase 2 - MySQL y acceso a datos
- [x] Fase 3 - Tools analiticas
- [x] Fase 4 - Forecast
- [x] Fase 5 - Grafo LangGraph
- [ ] Fase 6 - Integracion LLM
- [ ] Fase 7 - Prompt management Langfuse
- [ ] Fase 8 - Observabilidad Langfuse
- [ ] Fase 9 - Guardrails y seguridad
- [ ] Fase 10 - Manejo de errores
- [ ] Fase 11 - Frontend final
- [ ] Fase 12 - Testing
- [ ] Fase 13 - Hardening y entrega

---

## 19. Notas operativas para trabajar sobre este plan

- [ ] Marcar cada checkbox solo cuando el entregable este realmente verificado.
- [ ] Si una fase cambia el diseno, actualizar este documento.
- [ ] No avanzar a una fase compleja si la base anterior no esta estable.
- [ ] Priorizar siempre un camino demoable antes que perfeccion abstracta.
- [ ] Si aparece una decision nueva importante, documentarla junto al por que.

---

## 20. Resultado esperado

Si seguimos este plan, el resultado deberia ser un sistema que:

- use IA de forma moderna pero controlada;
- responda sobre datos reales;
- tenga arquitectura limpia;
- sea observable y trazable;
- permita iterar prompts con criterio;
- maneje errores profesionalmente;
- y pueda defenderse con solidez en una entrevista tecnica y funcional.
