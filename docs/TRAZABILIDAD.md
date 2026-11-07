# Trazabilidad: BRD / User Stories / BPMN → dominio → casos de uso → API → pruebas

Cada regla del BRD se puede seguir hasta el código y las pruebas que la verifican. Archivos de pruebas: `tests/test_dominio.py`, `test_maquina_estados.py`, `test_especificaciones.py`, `test_casos_de_uso.py`, `test_casos_de_uso_ampliados.py`, `test_contrato_repositorios.py`, `test_persistencia_sql.py`, `test_postgres.py` (en CI), `test_api.py`, `test_autenticacion.py`, `test_autorizacion.py`, `test_seguridad.py` y `test_usuarios.py`.

**BR-01 · NEC-02 · US-01 a US-03 · CU-01** (BPMN: «Calcular y emitir cotización», «Revisar y aceptar cotización», «¿Aceptada?»)
- Dominio: `src/domain/cotizacion.py` (Aggregate Cotización con estados Vigente, Aceptada, Rechazada); el Servicio nace Programado (`servicio.py`).
- Aplicación: `src/application/cotizaciones_app_service.py` (`emitirCotizacion`, `aceptarCotizacion`).
- API: `POST /cotizaciones` (Coordinador, Administración) y `POST /cotizaciones/{folio}/aceptacion` (Cliente).
- Pruebas: `test_casos_de_uso.py`, `test_api.py` (flujo completo y COTIZACION_NO_VIGENTE).

**BR-02 · RNF-02 · US-04 y US-05 · CU-02** (BPMN: «Confirmar cuadrilla (día previo)», «¿Cuadrilla disponible?»)
- Dominio: transición `PROGRAMADO → CUADRILLA_CONFIRMADA` en la State Machine; Specification `CuadrillaLibreEnFecha`; servicio de dominio `AsignadorDeCuadrilla`.
- Aplicación: `programacion_app_service.py` (`confirmarCuadrilla`); consulta `ConsultarDisponibilidad` (lado de lectura).
- API: `POST /servicios/{folio}/cuadrilla` (Coordinador) y `GET /disponibilidad` (personal interno).
- Pruebas: `test_especificaciones.py`, `test_casos_de_uso.py`, `test_api.py` (CUADRILLA_NO_DISPONIBLE).

**BR-03 · RNF-01 y RNF-03 · US-06 y US-07 · CU-03** (BPMN: «Reasignar personal», «¿Reemplazo encontrado?»)
- Dominio: Incidencia de tipo Ausencia; Specification `EmpleadoDisponibleParaCubrir`; transición `DECLARAR_SIN_REEMPLAZO → EN_RIESGO`.
- Aplicación: `personal_app_service.py` (`reportarAusencia`, `reasignarPersonal`).
- API: `POST /servicios/{folio}/ausencias` (Supervisor) y `/reasignaciones` (Administración).
- Pruebas: `test_casos_de_uso.py`, `test_casos_de_uso_ampliados.py`.

**US-08 · precondición de CU-05**
- Dominio: `RegistroDeTiempo`; transiciones `INICIAR` y `TERMINAR`; no se registra el término antes del inicio.
- API: `POST /servicios/{folio}/inicio` y `/termino` (Supervisor).
- Pruebas: `test_dominio.py`, `test_maquina_estados.py`, `test_api.py`.

**BR-04 · RNF-04 · US-09 y US-10 · CU-04** (BPMN: «Registrar incidencia / extra / ajuste»)
- Dominio: entidades Incidencia y Extra; Specification `ExtraRequiereConfirmacion`; `ConfiguracionDePoliticas` (ADR-003).
- Aplicación: `ejecucion_app_service.py` (`registrarExtra`, `confirmarExtra`, `documentarIncidencia`).
- API: `POST /servicios/{folio}/extras`, `/extras/{id}/confirmacion` (Coordinador) y `/incidencias` (Supervisor).
- Pruebas: `test_especificaciones.py`, `test_casos_de_uso_ampliados.py`, `test_api.py`.

**BR-07 · RNF-02 · US-17 · CU-05** (BPMN: «Verificar incidencias y extras pendientes», «¿Pendientes por documentar?», «Facturar servicio»)
- Dominio: Specification `SinPendientesPorDocumentar` y `servicioCerrableParaFacturacion()` (combinadas con el operador Y); transición `TERMINADO → CERRADO_PARA_FACTURACION`; evento `ServicioCerradoParaFacturacion` (ADR-004).
- Aplicación: `cierre_app_service.py` (`revisarIncidencia`, `cerrarParaFacturacion`).
- API: `POST /servicios/{folio}/incidencias/{id}/revision` y `/cierre` (Administración); respuesta CIERRE_BLOQUEADO con el detalle de lo que falta.
- Pruebas: `test_especificaciones.py`, `test_api.py` (`test_409_cierre_bloqueado_explica_que_falta`).

**US-18 y US-19** (panel de estados e historial)
- Aplicación: lado de lectura (`PanelReadRepositorySql`, CQRS básico). El cliente solo ve lo suyo.
- API: `GET /panel` y `GET /servicios/{folio}` (estado, historial y pendientes).
- Pruebas: `test_api.py`, `test_autorizacion.py`.

**RNF-02 · control de acceso**
- Autenticación por token firmado y autorización por rol en cada endpoint; el actor sale del token, no del cuerpo (ADR-005). Código: `src/api/autenticacion.py`, `rutas_auth.py`, `src/infrastructure/seguridad.py`, `src/domain/usuario.py`.
- Pruebas: `test_autenticacion.py`, `test_autorizacion.py` (matriz de roles, ids falsificados, aislamiento entre clientes), `test_seguridad.py`, `test_usuarios.py`.

**Diseñado, sin caso de uso programado:** US-11 (ajuste por inmueble mayor, BR-05), US-12 (material especial), US-13 (acceso negado), US-14 y US-15 (reprogramación, BR-06) y US-16 (cancelación, BR-08). Sus estados y transiciones ya existen en la State Machine (`CANCELAR`, `NEGAR_ACCESO`, `DAR_POR_NO_REALIZADO`); falta la capa de aplicación y la API. Se documentan como trabajo futuro.
