"""Endpoints REST. Cada uno traduce JSON -> Command, invoca el caso de uso y devuelve
la vista actualizada. No contiene reglas de negocio.

Autenticacion: pendiente. Por ahora el actor llega como id en el cuerpo y su rol lo
fija el caso de uso (el dominio valida el permiso, RNF-02).
"""
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from ..application.comandos import (AceptarCotizacion, CerrarParaFacturacion,
                                    ConfirmarCuadrilla, ConfirmarExtra,
                                    DocumentarIncidencia, EmitirCotizacion,
                                    ReasignarPersonal, RegistrarExtra, RegistrarInicio,
                                    RegistrarTermino, ReportarAusencia,
                                    RevisarIncidencia)
from ..application.consultas import ConsultarDisponibilidad
from ..domain.valores import FechaDeServicio, Folio
from . import esquemas as e
from .dependencias import Contexto, contexto, exigir

router = APIRouter()
ERRORES = {400: {"model": e.ErrorOut}, 403: {"model": e.ErrorOut},
           404: {"model": e.ErrorOut}, 409: {"model": e.ErrorOut},
           422: {"model": e.ErrorOut}}


def _salida(resultado, servicio):
    return {"resultado": resultado.valor,
            "eventos": [type(ev).__name__ for ev in resultado.eventos],
            "servicio": e.vistaServicio(servicio)}


def _devolver(ctx: Contexto, folio: str, resultado):
    exigir(resultado)
    return _salida(resultado, ctx.servicios.obtenerPorFolio(Folio(folio)))


# ---- Cotizaciones ----
@router.post("/cotizaciones", status_code=201, tags=["Cotizaciones"], responses=ERRORES,
             summary="Emitir cotizacion (US-01)")
def emitir_cotizacion(datos: e.EmitirCotizacionIn, ctx: Contexto = Depends(contexto)):
    folio = Folio(datos.folio or f"COT-{uuid.uuid4().hex[:8].upper()}")
    r = exigir(ctx.app.cotizaciones.emitirCotizacion(EmitirCotizacion(
        folio, datos.cliente_id, datos.ubicacion, datos.superficie,
        datos.tipo_de_inmueble, datos.frecuencia, tuple(datos.extras),
        timedelta(hours=float(datos.duracion_horas)), datos.personal, datos.precio)))
    return {"resultado": r.valor, "eventos": [type(ev).__name__ for ev in r.eventos],
            "cotizacion": e.vistaCotizacion(ctx.cotizaciones.obtenerPorFolio(folio))}


@router.get("/cotizaciones/{folio}", tags=["Cotizaciones"], responses=ERRORES)
def consultar_cotizacion(folio: str, ctx: Contexto = Depends(contexto)):
    return e.vistaCotizacion(ctx.cotizaciones.obtenerPorFolio(Folio(folio)))


@router.post("/cotizaciones/{folio}/aceptacion", tags=["Cotizaciones"], responses=ERRORES,
             summary="Aceptar cotizacion y programar el servicio (CU-01)")
def aceptar_cotizacion(folio: str, datos: e.AceptarCotizacionIn,
                       ctx: Contexto = Depends(contexto)):
    fecha = FechaDeServicio(datos.fecha) if datos.fecha else None
    r = ctx.app.cotizaciones.aceptarCotizacion(
        AceptarCotizacion(Folio(folio), datos.cliente_id, fecha))
    return _devolver(ctx, folio, r)


# ---- Servicios ----
@router.get("/servicios/{folio}", tags=["Servicios"], responses=ERRORES,
            summary="Estado, historial y pendientes del servicio (US-19)")
def consultar_servicio(folio: str, ctx: Contexto = Depends(contexto)):
    return e.vistaServicio(ctx.servicios.obtenerPorFolio(Folio(folio)))


@router.post("/servicios/{folio}/cuadrilla", tags=["Programacion"], responses=ERRORES,
             summary="Confirmar cuadrilla (CU-02)")
def confirmar_cuadrilla(folio: str, datos: e.ConfirmarCuadrillaIn,
                        ctx: Contexto = Depends(contexto)):
    return _devolver(ctx, folio, ctx.app.programacion.confirmarCuadrilla(
        ConfirmarCuadrilla(Folio(folio), datos.cuadrilla_id, datos.coordinador_id)))


@router.post("/servicios/{folio}/inicio", tags=["Ejecucion"], responses=ERRORES,
             summary="Registrar inicio (US-08)")
def registrar_inicio(folio: str, datos: e.RegistrarInicioIn,
                     ctx: Contexto = Depends(contexto)):
    return _devolver(ctx, folio, ctx.app.ejecucion.registrarInicio(
        RegistrarInicio(Folio(folio), datos.supervisor_id, datos.momento)))


@router.post("/servicios/{folio}/termino", tags=["Ejecucion"], responses=ERRORES,
             summary="Registrar termino (US-08)")
def registrar_termino(folio: str, datos: e.RegistrarTerminoIn,
                      ctx: Contexto = Depends(contexto)):
    return _devolver(ctx, folio, ctx.app.ejecucion.registrarTermino(
        RegistrarTermino(Folio(folio), datos.supervisor_id, datos.momento)))


@router.post("/servicios/{folio}/ausencias", tags=["Personal"], responses=ERRORES,
             summary="Reportar ausencia (CU-03)")
def reportar_ausencia(folio: str, datos: e.ReportarAusenciaIn,
                      ctx: Contexto = Depends(contexto)):
    return _devolver(ctx, folio, ctx.app.personal.reportarAusencia(
        ReportarAusencia(Folio(folio), datos.empleado_id, datos.supervisor_id)))


@router.post("/servicios/{folio}/reasignaciones", tags=["Personal"], responses=ERRORES,
             summary="Reasignar personal o declarar sin reemplazo (CU-03)")
def reasignar_personal(folio: str, datos: e.ReasignarPersonalIn,
                       ctx: Contexto = Depends(contexto)):
    return _devolver(ctx, folio, ctx.app.personal.reasignarPersonal(
        ReasignarPersonal(Folio(folio), datos.empleado_id, datos.sustituto_id,
                          datos.admin_id)))


@router.post("/servicios/{folio}/extras", status_code=201, tags=["Ejecucion"],
             responses=ERRORES, summary="Registrar extra en sitio (CU-04)")
def registrar_extra(folio: str, datos: e.RegistrarExtraIn,
                    ctx: Contexto = Depends(contexto)):
    return _devolver(ctx, folio, ctx.app.ejecucion.registrarExtra(
        RegistrarExtra(Folio(folio), datos.descripcion, datos.supervisor_id)))


@router.post("/servicios/{folio}/extras/{extra_id}/confirmacion", tags=["Ejecucion"],
             responses=ERRORES, summary="Confirmar extra fuera de catalogo (CU-04)")
def confirmar_extra(folio: str, extra_id: str, datos: e.ConfirmarExtraIn,
                    ctx: Contexto = Depends(contexto)):
    return _devolver(ctx, folio, ctx.app.ejecucion.confirmarExtra(
        ConfirmarExtra(Folio(folio), extra_id, datos.coordinador_id)))


@router.post("/servicios/{folio}/incidencias", status_code=201, tags=["Ejecucion"],
             responses=ERRORES, summary="Documentar incidencia")
def documentar_incidencia(folio: str, datos: e.DocumentarIncidenciaIn,
                          ctx: Contexto = Depends(contexto)):
    return _devolver(ctx, folio, ctx.app.ejecucion.documentarIncidencia(
        DocumentarIncidencia(Folio(folio), datos.tipo, datos.descripcion,
                             datos.supervisor_id, datos.empleado_id)))


@router.post("/servicios/{folio}/incidencias/{incidencia_id}/revision", tags=["Cierre"],
             responses=ERRORES, summary="Marcar incidencia como revisada")
def revisar_incidencia(folio: str, incidencia_id: str, datos: e.RevisarIncidenciaIn,
                       ctx: Contexto = Depends(contexto)):
    return _devolver(ctx, folio, ctx.app.cierre.revisarIncidencia(
        RevisarIncidencia(Folio(folio), incidencia_id, datos.admin_id)))


@router.post("/servicios/{folio}/cierre", tags=["Cierre"], responses=ERRORES,
             summary="Cerrar para facturacion (CU-05)")
def cerrar_para_facturacion(folio: str, datos: e.CerrarParaFacturacionIn,
                            ctx: Contexto = Depends(contexto)):
    return _devolver(ctx, folio, ctx.app.cierre.cerrarParaFacturacion(
        CerrarParaFacturacion(Folio(folio), datos.admin_id)))


# ---- Consultas ----
@router.get("/disponibilidad", tags=["Consultas"], responses=ERRORES,
            summary="Disponibilidad de cuadrillas por fecha (US-05)")
def consultar_disponibilidad(fecha: date = Query(description="AAAA-MM-DD"),
                             ctx: Contexto = Depends(contexto)):
    filas = ctx.app.consultas.consultarDisponibilidad(ConsultarDisponibilidad(fecha))
    return [{"cuadrilla_id": f.cuadrilla_id, "libre": f.libre} for f in filas]


@router.get("/panel", tags=["Consultas"],
            summary="Panel operativo: cotizaciones, servicios por estado, cuadrillas y personal (US-18)")
def panel_operativo(ctx: Contexto = Depends(contexto)):
    return ctx.panel.resumen()


@router.get("/salud", tags=["Sistema"], summary="Verificacion de que la API responde")
def salud():
    return {"estado": "ok"}