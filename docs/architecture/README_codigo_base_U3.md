# Codigo base · CleanPro (Unidad 3)

Codigo minimo que representa la arquitectura propuesta: **dominio**, **aplicacion**
e **infraestructura** separados. Cubre CU-01 a CU-05. No tiene dependencias externas
(solo Python 3.10+ y `unittest`).

## Como revisarlo

```bash
# desde la raiz del repositorio
python -m unittest discover -s tests -t . -v
```

## Estructura

```
src/cleanpro/
  dominio/           reglas del negocio; no importa aplicacion ni infraestructura
    servicio.py          Aggregate Servicio (S1-S13), entidades Incidencia y Extra
    cotizacion.py        Aggregate Cotizacion (C1-C5)
    cuadrilla.py         Cuadrilla y Empleado (raices minimas)
    configuracion.py     ConfiguracionDePoliticas (sin valores definidos, RNF-04)
    valores.py           Value Objects, Actor y Rol
    eventos.py           Domain Events
    servicios_de_dominio.py   AsignadorDeCuadrilla, PoliticaDeExtras
    repositorios.py      interfaces de Repository
    errores.py           errores con codigo de negocio (CIERRE_BLOQUEADO, ...)
  aplicacion/        coordina casos de uso; depende solo de interfaces
    *_app_service.py     un Application Service por grupo de casos de uso
    comandos.py          Commands (CQRS)    consultas.py   Query + DTO de lectura
    unit_of_work.py      UnitOfWork         puertos.py     NotificacionPort, FacturacionPort
  infraestructura/   detalles concretos
    en_memoria.py        Repository y UnitOfWork en memoria
    adaptadores.py       NotificacionAdapter, FacturacionEventAdapter
    composicion.py       unico lugar donde se eligen las implementaciones
tests/               pruebas por invariante y por caso de uso
```

## Caso de uso -> componente -> prueba

| Caso de uso | Application Service | Regla en el dominio | Pruebas |
|---|---|---|---|
| CU-01 Aceptar cotizacion | `CotizacionesAppService.aceptarCotizacion` | `Cotizacion.aceptar` (C4, C5), `Servicio.programarDesde` (S1) | `CU01AceptarCotizacion` |
| CU-02 Confirmar cuadrilla | `ProgramacionAppService.confirmarCuadrilla` | `Servicio.confirmarCuadrilla` (S2), `AsignadorDeCuadrilla` | `CU02ConfirmarCuadrilla` |
| CU-03 Ausencia y reasignacion | `PersonalAppService.reportarAusencia / reasignarPersonal` | `Servicio.reportarAusencia`, `reasignarPersonal`, `declararSinReemplazo` (S4) | `CU03AusenciaYReasignacion` |
| CU-04 Extra en sitio | `EjecucionAppService.registrarExtra / confirmarExtra` | `PoliticaDeExtras`, `Servicio.registrarExtra` (S6) | `CU04RegistrarExtra` |
| CU-05 Cierre para facturacion | `CierreAppService.cerrarParaFacturacion` | `Servicio.cerrarParaFacturacion` (S12, BR-07) | `CU05CierreParaFacturacion` |

Cada caso tiene un flujo normal y uno de excepcion o rechazo.

## Correspondencia con el diagrama de clases

- Los nombres de clases y metodos del diagrama se conservan tal cual (`confirmarCuadrilla`,
  `obtenerPorFolio`, `estaLibre`, ...), por eso los metodos van en camelCase.
- `RepositoriosSql` y `SqlUnitOfWork` se sustituyen por `en_memoria.py`: cumplen las
  mismas interfaces, asi que una version SQL las reemplaza solo en `composicion.py`.
- Los Application Services reciben un **Command** y devuelven un **Resultado**
  (`exito`, `codigo`, `detalle`). El diagrama muestra los datos del Command como parametros.
- Cada servicio hace `obtener -> invocar al dominio -> extraerEventos -> guardar -> commit`;
  los eventos se publican **despues** del commit (como en las secuencias). Ante un error de
  dominio se hace `rollback` y se devuelve el codigo de negocio.

## Elementos que NO estan en el diagrama de clases (conviene alinearlo)

- `ConsultasAppService`, `ConsultarDisponibilidad`, `DisponibilidadDTO` (lado de lectura de CQRS).
- Flechas de `CotizacionesAppService`, `PersonalAppService` y `EjecucionAppService` hacia
  `ServicioRepository` y `UnitOfWork` (el diseno las necesita; el diagrama solo las muestra
  para `ProgramacionAppService` y `CierreAppService`). `PersonalAppService` tambien usa `EmpleadoRepository`.
- `Resultado` y los Commands.

## Supuestos del codigo (no definidos en la U2; validar o ajustar)

- La **fecha del servicio** llega en `AceptarCotizacion.fecha`; la U2 no dice de donde sale.
- Una cotizacion con `extras = ()` se interpreta como "sin extras" (el dato debe indicarse).
- Para reasignar debe existir una **ausencia reportada** de ese empleado; el sustituto debe
  estar `disponible_para_cubrir`.
- Una incidencia nace *Pendiente de revision* y **Administracion la marca revisada** (la U2 no
  define como sale de ese estado). Los extras fuera de catalogo los confirma el Coordinador.
- `ConfiguracionDePoliticas` arranca **sin valores**: con catalogo vacio todo extra requiere
  confirmacion. Los datos de `tests/utiles.py` son solo ilustrativos.
- No se define la moneda de `Dinero` ni las unidades de `superficie`.

## Fuera del alcance de este codigo base

Emitir cotizacion como caso de uso (solo existe `Cotizacion.emitir`), `CalculadoraDeEstimacion`,
ajuste por inmueble mayor, acceso negado, reprogramacion, cancelacion, panel e historial
(US-11 a US-16, US-18, US-19), implementacion SQL y autenticacion (el `Actor` se arma a partir
del id recibido; en un sistema real el rol vendria de la autenticacion).
