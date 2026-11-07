# ADR-009 · API REST con FastAPI, interfaz web en la misma aplicación y CQRS básico para las lecturas

**Estado:** Aceptada

## Contexto
El PIA exige una API REST documentada con Swagger/OpenAPI activo en producción. Los actores necesitan una interfaz para la demostración y el panel (US-18) y el historial (US-19) son lecturas que no deben pasar por los Aggregates.

## Alternativas
- **Flask:** ligero, pero la documentación OpenAPI no es nativa.
- **Django REST Framework:** completo, pero pesado para un dominio ya modelado a mano.
- **Una SPA separada:** mejor experiencia, pero duplica el despliegue y el tiempo disponible no lo justifica.
- **FastAPI con una página estática servida por la misma app:** OpenAPI y Swagger UI automáticos, validación de entrada con Pydantic y un solo despliegue.

## Decisión
FastAPI. Los endpoints solo traducen JSON a Commands, invocan el caso de uso y devuelven la vista; no contienen reglas. Los errores de negocio se traducen a `{codigo, detalle}` con el estado HTTP correspondiente (403 `SIN_PERMISO`, 404 `NO_ENCONTRADO`, 409 `TRANSICION_INVALIDA`, `CIERRE_BLOQUEADO` y otros, 422 para datos inválidos). La interfaz es una página única (`src/api/static/index.html`) servida en `/`. El panel se lee con una consulta SQL directa (`sql_lectura.py`), separada de los Aggregates (CQRS básico).

## Consecuencias
Swagger UI y `openapi.json` están siempre sincronizados con el código; un solo servicio que desplegar. Costo: la interfaz es sencilla y sin framework. La autenticación y los permisos por rol se documentan en el ADR-005.

## Trazabilidad
US-18, US-19; RNF-01, RNF-02; requisito de producción del PIA.
