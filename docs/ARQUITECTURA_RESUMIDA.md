# Arquitectura Resumida

## Objetivo

Dejar definida la base del proyecto para que el BI Assistant crezca de forma ordenada desde el primer commit.

## Stack confirmado

- `Python`
- `FastAPI`
- `LangGraph`
- `LangChain`
- `Langfuse`
- `PyMySQL`
- `pandas`
- `OpenAI`
- `Chart.js`

## Convenciones base

- El frontend no contiene secretos ni acceso directo a terceros.
- El backend es el unico punto de acceso a OpenAI, MySQL y Langfuse.
- La configuracion vive en variables de entorno cargadas desde `app/config.py`.
- Las rutas HTTP solo orquestan; la logica vive en `services/` y mas adelante en `graph/` y `tools/`.
- Los contratos de request y response viven en `schemas/`.
- Los errores controlados devuelven una respuesta JSON consistente.
- El `thread_id` es el identificador de sesion conversacional y viaja en cada request.

## Contrato inicial de API

`POST /api/chat`

- entrada:
  - `message`
  - `thread_id`
- salida:
  - `answer`
  - `intent`
  - `data_range`
  - `chart`
  - `meta`

`GET /api/health`

- estado general de la aplicacion

`GET /api/coverage`

- devuelve el rango real de datos y cantidad de registros desde MySQL

`GET /api/kpis`

- devuelve un resumen agregado inicial de leads, ventas, ingresos, costo, clics e impresiones

`GET /api/forecast`

- devuelve la proyeccion deterministica del proximo mes para leads y ventas
- incluye metodologia, warnings y trazabilidad del historico mensual

## Estrategia de logs y errores

- Los errores tecnicos se registran en backend.
- Las respuestas al cliente no exponen stack traces.
- La UI recibe mensajes consistentes y aptos para demo.
- Los errores del dominio se modelan con excepciones propias.
