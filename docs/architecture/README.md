# Arquitectura y decisiones técnicas — CleanPro (Equipo 12)

Este documento resume cómo está construido CleanPro y por qué. Las decisiones con alternativas están en los ADR; los diagramas están en `diagrams/`; el código base de la U3 está descrito en `README_codigo_base_U3.md`.

## Capas

- **Dominio** (`src/domain/`): Aggregates Cotización, Servicio, Cuadrilla y ConfiguracionDePoliticas; Value Objects; eventos de dominio; State Machine; Specification; servicios de dominio (`AsignadorDeCuadrilla`, `PoliticaDeExtras`). No depende de ninguna otra capa.
- **Aplicación** (`src/application/`): servicios de aplicación que orquestan cada caso de uso (emitir y aceptar cotización, confirmar cuadrilla, reportar ausencia, reasignar, registrar inicio/término/extras, documentar y revisar incidencias, cerrar para facturación) y los puertos `NotificacionPort` y `FacturacionPort`, además de las interfaces de los repositorios y la Unit of Work.
- **Infraestructura** (`src/infrastructure/`): repositorios en memoria y SQL (SQLite/PostgreSQL), Unit of Work, lectura del panel (`sql_lectura.py`), seguridad (hashes y token) y datos de demostración.
- **API e interfaz** (`src/api/`): FastAPI, esquemas Pydantic, autenticación y autorización por rol, y la página web servida en `/`.

La dependencia siempre apunta hacia el dominio (DIP).

## Patrones aplicados y por qué

- **Domain Model** — las invariantes viven en el Aggregate Servicio (ADR-001).
- **Aggregates separados con Folio compartido** (ADR-002).
- **State Machine por tabla de transiciones** — 8 estados y 8 disparadores (ADR-006).
- **Specification** — reglas combinables con Y, O y No, que explican por qué fallan (ADR-007).
- **Repository + Unit of Work** — persistencia sustituible: memoria, SQLite y PostgreSQL (ADR-008).
- **Service Layer** — un método por caso de uso, sin reglas en la API.
- **Ports and adapters** — notificación y facturación fuera del dominio (ADR-004).
- **CQRS básico** — el panel y el historial se leen con consultas directas, separadas de los Aggregates (ADR-009).
- **Políticas configurables** — sin valores inventados (ADR-003).
- **Autenticación y autorización** — PBKDF2-HMAC-SHA256, token firmado, roles verificados contra la base en cada petición (ADR-005).

## SOLID

- **SRP:** el Aggregate Servicio concentra las invariantes S1–S13 y cada Repository SQL atiende a un solo Aggregate.
- **OCP:** una política nueva entra por `ConfiguracionDePoliticas` o `PoliticaDeExtras` sin tocar el Aggregate.
- **LSP:** las implementaciones en memoria y SQL pasan la misma batería de contrato (`ServicioRepositoryContrato`, `CotizacionRepositoryContrato`, `UnitOfWorkContrato`).
- **ISP:** las consultas usan interfaces de lectura propias (`ConsultasAppService`, `DisponibilidadReadRepository`).
- **DIP:** la capa de aplicación depende de puertos; dos compromisos están documentados en el informe de la U3.

## Calidad y operación

- 156 pruebas automáticas pasan localmente (17 más, de PostgreSQL, se ejecutan solo en CI); cobertura local 99 %; el CI exige un mínimo de 80 %.
- CI en GitHub Actions: Python 3.13 y 3.14, servicio PostgreSQL 16 y construcción de la imagen Docker.
- Docker Compose define `db`, `app`, `db_test` y `tests`. Configuración por variables de entorno (12-Factor): `DATABASE_URL`, `CLEANPRO_SECRET`, `CLEANPRO_CLAVE_DEMO`, `CLEANPRO_DEMO`.
- Despliegue en Render con Swagger UI en `/docs`; la especificación está en `docs/api/openapi.json`.

## Índice de ADR

- ADR-001 Domain Model como patrón de lógica de negocio
- ADR-002 Cotización y Servicio como Aggregates separados
- ADR-003 Políticas configurables
- ADR-004 Facturación fuera del dominio
- ADR-005 Autenticación y autorización
- ADR-006 State Machine del Servicio
- ADR-007 Specification
- ADR-008 Persistencia SQL (SQLite y PostgreSQL)
- ADR-009 API REST con FastAPI, interfaz web y CQRS de lectura

## Diagramas

En `diagrams/`: diagrama de clases, diagrama de dominio y dos diagramas de secuencia (flujo principal y regla o excepción).

## Limitaciones conocidas

- Las historias US-11 a US-16 (ajuste de alcance, reglas de acceso negado y cancelación) y la estimación automática no están implementadas; la State Machine ya contiene sus transiciones.
- `docker compose` no se ejecutó localmente; la imagen sí se construye en el CI.
- El límite de intentos de login es en memoria (se reinicia con el proceso).
- Los servicios de aplicación usan un Actor con rol fijo por caso de uso; la autorización real se hace en la API.
- No hay endpoint para administrar usuarios; los usuarios de demostración se siembran al iniciar.
