# CleanPro · PIA de Componentes de Lógica de Negocios

Universidad Autónoma de Nuevo León (UANL) · Facultad de Ingeniería Mecánica y Eléctrica (FIME)
Materia: Componentes de Lógica de Negocios · Grupo 001 · Hora N1 · Agosto - Diciembre 2026
Docente: Miguel Ángel Gómez Marroquín · **Equipo 12**

## Qué es

CleanPro es una empresa de servicios de limpieza residencial y empresarial. Este proyecto implementa su proceso operativo central: desde que el cliente acepta una cotización hasta que el servicio se cierra para facturación, pasando por la programación, la confirmación de cuadrilla, la ejecución en sitio, las ausencias de personal, los extras y las incidencias (casos de uso CU-01 a CU-05).

## Enlaces

| Qué | Dónde |
|---|---|
| Aplicación en línea (interfaz) | https://pia-clneg.onrender.com |
| Documentación de la API (Swagger UI) | https://pia-clneg.onrender.com/docs |
| Especificación OpenAPI | https://pia-clneg.onrender.com/openapi.json |
| Repositorio | https://github.com/dani101909/pia-clneg |

El despliegue gratuito de Render se duerme tras 15 minutos sin uso: la primera visita puede tardar un minuto en responder.

## Qué incluye

- **Domain Model (DDD):** Aggregates `Cotizacion` y `Servicio`, Value Objects, Domain Events y servicios de dominio.
- **State Machine** del Servicio: Programado, CuadrillaConfirmada, EnEjecucion, Terminado, CerradoParaFacturacion, EnRiesgo, NoRealizado y Cancelado, con las transiciones válidas en una sola tabla.
- **Specification** composable (`Y`, `O`, `No`): cuadrilla libre en fecha, extra que requiere confirmación, empleado disponible para cubrir, servicio cerrable para facturación, entre otras.
- **API REST** con FastAPI, documentada con Swagger UI y OpenAPI.
- **Persistencia SQL** en SQLite (local) y PostgreSQL (producción), detrás de interfaces de Repository.
- **Autenticación y autorización** por rol con tokens firmados.
- **Interfaz web** en `/`, con login y vistas distintas para cada rol.
- **Calidad:** pruebas unitarias y de integración, cobertura mínima del 80 % y CI en GitHub Actions.
- **Producción:** Dockerfile y Docker Compose (base de datos, aplicación y pruebas).

## Arquitectura

Tres capas con dependencias hacia adentro: el dominio no conoce a las demás.

```
src/
  domain/           reglas del negocio: Aggregates, State Machine, Specifications,
                    eventos, errores, interfaces de Repository
  application/      casos de uso (Application Services), comandos y consultas
  infrastructure/   SQL (SQLite y PostgreSQL), repositorios, seguridad, datos de demo
  api/              FastAPI: rutas, esquemas, autenticación e interfaz web (static/)
tests/              pruebas por invariante, caso de uso, API, autorización y persistencia
docs/               informe, glosario, matriz de trazabilidad, diagramas y ADRs
scripts/            exportar_openapi.py
```

Las decisiones de diseño están en los ADR: ADR-001 a ADR-004 en el informe de la U3 (`docs/docs.pdf`) y [ADR-005 (autenticación y autorización)](docs/architecture/adr/ADR-005-autenticacion-y-autorizacion.md).

## Cómo ejecutarlo

### En local (Windows, PowerShell)

Requiere Python 3.13 o superior.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:CLEANPRO_DEMO="1"
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload
```

Abrir `http://127.0.0.1:8000/` (interfaz) o `http://127.0.0.1:8000/docs` (Swagger). Con `CLEANPRO_DEMO=1` se cargan datos y usuarios de demostración. Por defecto usa SQLite (`cleanpro.db`).

### Con Docker Compose

```powershell
docker compose up --build
```

La API queda en `http://localhost:8000/docs`, con PostgreSQL 16 como base de datos. Para correr las pruebas contra PostgreSQL:

```powershell
docker compose --profile tests run --rm tests
```

## Usuarios de demo

Se crean con `CLEANPRO_DEMO=1` y todos comparten la misma contraseña: `cleanpro123` en local; en el despliegue público es la definida en `CLEANPRO_CLAVE_DEMO` y se entrega al docente por separado.

| Usuario | Rol | Qué puede hacer |
|---|---|---|
| `cliente1`, `cliente2`, `cliente3` | Cliente | Aceptar su cotización y consultar solo lo suyo |
| `coord1` | Coordinador | Confirmar cuadrilla y extras fuera de catálogo; emitir cotización |
| `sup1` | Supervisor | Registrar inicio y término, ausencias, extras e incidencias |
| `admin1` | Administración | Reasignar personal, revisar incidencias, cerrar para facturación; emitir cotización |

**Cómo entrar:** en la interfaz (`/`) con usuario y contraseña. En Swagger, ejecutar `POST /auth/login`, copiar el `access_token` y pegarlo (sin la palabra `Bearer`) en el botón **Authorize**. El token dura 1 hora.

**Recorrido sugerido para probar el flujo completo:** `cliente1` acepta una cotización con fecha, `coord1` confirma la cuadrilla, `sup1` registra inicio y término, y `admin1` cierra para facturación.

## API

Todos los endpoints de negocio exigen token; solo son públicos `/salud`, `/`, `/docs`, `/openapi.json` y `POST /auth/login`.

| Endpoint | Rol | Caso de uso |
|---|---|---|
| `POST /auth/login`, `GET /auth/yo` | Público / autenticado | Iniciar sesión y consultar el usuario actual |
| `POST /cotizaciones` | Coordinador, Administración | Emitir cotización (US-01) |
| `GET /cotizaciones/{folio}` | Autenticado (el cliente solo la suya) | Consultar cotización |
| `POST /cotizaciones/{folio}/aceptacion` | Cliente | Aceptar y programar el servicio (CU-01) |
| `GET /servicios/{folio}` | Autenticado (el cliente solo el suyo) | Estado, historial y pendientes (US-19) |
| `POST /servicios/{folio}/cuadrilla` | Coordinador | Confirmar cuadrilla (CU-02) |
| `POST /servicios/{folio}/inicio`, `/termino` | Supervisor | Registrar inicio y término (US-08) |
| `POST /servicios/{folio}/ausencias` | Supervisor | Reportar ausencia (CU-03) |
| `POST /servicios/{folio}/reasignaciones` | Administración | Reasignar personal o declarar sin reemplazo (CU-03) |
| `POST /servicios/{folio}/extras` | Supervisor | Registrar extra en sitio (CU-04) |
| `POST /servicios/{folio}/extras/{id}/confirmacion` | Coordinador | Confirmar extra fuera de catálogo (CU-04) |
| `POST /servicios/{folio}/incidencias` | Supervisor | Documentar incidencia |
| `POST /servicios/{folio}/incidencias/{id}/revision` | Administración | Marcar incidencia como revisada |
| `POST /servicios/{folio}/cierre` | Administración | Cerrar para facturación (CU-05) |
| `GET /disponibilidad` | Personal interno | Disponibilidad de cuadrillas por fecha (US-05) |
| `GET /panel` | Autenticado (el cliente ve solo lo suyo) | Panel operativo (US-18) |

**Errores:** `401 NO_AUTENTICADO` o `CREDENCIALES_INVALIDAS`, `403 SIN_PERMISO`, `404 NO_ENCONTRADO`, `409` para reglas de negocio (por ejemplo `CIERRE_BLOQUEADO` o `TRANSICION_INVALIDA`), `422` para datos inválidos y `429 DEMASIADOS_INTENTOS` (5 fallos de login bloquean al usuario 60 segundos).

Para guardar una copia de la especificación en el repositorio:

```powershell
.\.venv\Scripts\python.exe scripts\exportar_openapi.py
```

Genera `docs/api/openapi.json`.

## Pruebas y CI

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m pytest tests --cov=src --cov-report=term-missing --cov-fail-under=80
```

Resultado esperado en local: `156 passed, 17 skipped`. Las 17 omitidas son las pruebas de PostgreSQL, que se saltan si no se define `TEST_DATABASE_URL`; en el CI sí se ejecutan contra PostgreSQL 16.

El pipeline (`.github/workflows/ci.yml`) corre en cada push y pull request: pruebas con cobertura mínima del 80 % en Python 3.13 y 3.14 con PostgreSQL 16, y después la construcción de la imagen Docker.

## Variables de entorno

Hay una plantilla en `.env.example`. No subas tu `.env` a GitHub.

| Variable | Para qué sirve | Si falta |
|---|---|---|
| `DATABASE_URL` | Base de datos (`sqlite:///cleanpro.db` o `postgresql://...`) | SQLite local |
| `CLEANPRO_DEMO` | `1` carga datos y usuarios de demo al arrancar | No se cargan |
| `CLEANPRO_SECRET` | Secreto de firma de los tokens (mínimo 16 caracteres) | Secreto aleatorio; las sesiones se pierden al reiniciar |
| `CLEANPRO_CLAVE_DEMO` | Contraseña de los usuarios de demo | `cleanpro123` |
| `PORT` | Puerto de la API | `8000` |

## Documentación

- Informe de arquitectura y ADR-001 a ADR-004 (U3): `docs/docs.pdf`
- Glosario: `docs/Glosario_Actualizado.pdf`
- Matriz de trazabilidad: `docs/Matriz_de_Trazabilidad.pdf`
- Diagramas de dominio, clases y secuencia: `docs/architecture/diagrams/`
- ADR-005, autenticación y autorización: `docs/architecture/adr/`
- Bitácora de uso de IA: carpeta `docs/`

## Limitaciones conocidas

- Los casos US-11 a US-16 (ajuste por inmueble mayor, material especial, acceso negado, reprogramación, cancelación y modificación) no tienen aún caso de uso ni endpoint. Las transiciones de cancelar, negar acceso y dar por no realizado ya existen en la State Machine.
- La estimación (duración, personal y precio) se captura al emitir la cotización; no se calcula automáticamente (US-02). La U2 no define tarifas y los valores quedan configurables.
- El limitador de intentos de login vive en la memoria del proceso: sirve para una instancia. No hay cierre de sesión en el servidor (el token vence a la hora) ni endpoint para administrar usuarios.
- Los datos de demostración son ilustrativos.

## Equipo

- Pérez Ordaz Andrés Daniel (2163200)
- Ramos Ortiz Patricia Lizeth (2161739)
- Esquivel Anaya Jonathan (2160886)
