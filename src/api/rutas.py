"""Endpoints REST. Cada uno traduce JSON -> Command, invoca el caso de uso y devuelve
la vista actualizada. No contiene reglas de negocio.

Autenticacion y autorizacion (RNF-02): todo endpoint de negocio exige
`Authorization: Bearer <token>`. El id del actor sale del usuario autenticado, nunca
del cuerpo (si el cuerpo trae ids de actor se ignoran); el rol permitido por endpoint
se exige aqui con `requiere(...)` (403) y el dominio lo vuelve a validar.
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
from ..domain.usuario import Usuario
from ..domain.valores import FechaDeServicio, Folio, Rol
from . import esquemas as e
from .autenticacion import STAFF, requiere, usuario_actual
from .dependencias import Contexto, ErrorDeNegocio, contexto, exigir

router = APIRouter()
ERRORES = {400: {"model": e.ErrorOut}, 401: {"model": e.ErrorOut},
           403: {"model": e.ErrorOut}, 404: {"model": e.ErrorOut},
           409: {"model": e.ErrorOut}, 422: {"model": e.ErrorOut}}


def _salida(resultado, servicio):
    return {"resultado": resultado.valor,
            "eventos": [type(ev).__name__ for ev in resultado.eventos],
            "servicio": e.vistaServicio(servicio)}


def _exigir_propiedad(usuario: Usuario, cliente_id: str):
    """Un cliente solo consulta lo suyo; el personal interno consulta todo."""
    if usuario.rol == Rol.CLIENTE and usuario.actor_id != cliente_id:
        raise ErrorDeNegocio("SIN_PERMISO",
                             "Solo puedes consultar tus propias cotizaciones y servicios")


def _devolver(ctx: Contexto, folio: str, resultado):
    exigir(resultado)
    return _salida(resultado, ctx.servicios.obtenerPorFolio(Folio(folio)))


# ---- Cotizaciones ----
@router.post("/cotizaciones", status_code=201, tags=["Cotizaciones"], responses=ERRORES,
             summary="Emitir cotizacion (US-01) · Coordinador o Administracion")
def emitir_cotizacion(datos: e.EmitirCotizacionIn, ctx: Contexto = Depends(contexto),
                      _: Usuario = Depends(requiere(Rol.COORDINADOR, Rol.ADMINISTRACION))):
    folio = Folio(datos.folio or f"COT-{uuid.uuid4().hex[:8].upper()}")
    r = exigir(ctx.app.cotizaciones.emitirCotizacion(EmitirCotizacion(
        folio, datos.cliente_id, datos.ubicacion, datos.superficie,
        datos.tipo_de_inmueble, datos.frecuencia, tuple(datos.extras),
        timedelta(hours=float(datos.duracion_horas)), datos.personal, datos.precio)))
    return {"resultado": r.valor, "eventos": [type(ev).__name__ for ev in r.eventos],
            "cotizacion": e.vistaCotizacion(ctx.cotizaciones.obtenerPorFolio(folio))}


@router.get("/cotizaciones/{folio}", tags=["Cotizaciones"], responses=ERRORES,
            summary="Consultar cotizacion · el cliente solo la suya")
def consultar_cotizacion(folio: str, ctx: Contexto = Depends(contexto),
                         usuario: Usuario = Depends(usuario_actual)):
    cotizacion = ctx.cotizaciones.obtenerPorFolio(Folio(folio))
    _exigir_propiedad(usuario, cotizacion.cliente_id)
    return e.vistaCotizacion(cotizacion)


@router.post("/cotizaciones/{folio}/aceptacion", tags=["Cotizaciones"], responses=ERRORES,
             summary="Aceptar cotizacion y programar el servicio (CU-01) · Cliente")
def aceptar_cotizacion(folio: str, datos: e.AceptarCotizacionIn,
                       ctx: Contexto = Depends(contexto),
                       usuario: Usuario = Depends(requiere(Rol.CLIENTE))):
    fecha = FechaDeServicio(datos.fecha) if datos.fecha else None
    r = ctx.app.cotizaciones.aceptarCotizacion(
        AceptarCotizacion(Folio(folio), usuario.actor_id, fecha))
    return _devolver(ctx, folio, r)


# ---- Servicios ----
@router.get("/servicios/{folio}", tags=["Servicios"], responses=ERRORES,
            summary="Estado, historial y pendientes del servicio (US-19) · el cliente solo el suyo")
def consultar_servicio(folio: str, ctx: Contexto = Depends(contexto),
                       usuario: Usuario = Depends(usuario_actual)):
    servicio = ctx.servicios.obtenerPorFolio(Folio(folio))
    if usuario.rol == Rol.CLIENTE:             # el servicio comparte folio con su cotizacion
        _exigir_propiedad(usuario, ctx.cotizaciones.obtenerPorFolio(Folio(folio)).cliente_id)
    return e.vistaServicio(servicio)


@router.post("/servicios/{folio}/cuadrilla", tags=["Programacion"], responses=ERRORES,
             summary="Confirmar cuadrilla (CU-02) · Coordinador")
def confirmar_cuadrilla(folio: str, datos: e.ConfirmarCuadrillaIn,
                        ctx: Contexto = Depends(contexto),
                        usuario: Usuario = Depends(requiere(Rol.COORDINADOR))):
    return _devolver(ctx, folio, ctx.app.programacion.confirmarCuadrilla(
        ConfirmarCuadrilla(Folio(folio), datos.cuadrilla_id, usuario.actor_id)))


@router.post("/servicios/{folio}/inicio", tags=["Ejecucion"], responses=ERRORES,
             summary="Registrar inicio (US-08) · Supervisor")
def registrar_inicio(folio: str, datos: e.RegistrarInicioIn = e.RegistrarInicioIn(),
                     ctx: Contexto = Depends(contexto),
                     usuario: Usuario = Depends(requiere(Rol.SUPERVISOR))):
    return _devolver(ctx, folio, ctx.app.ejecucion.registrarInicio(
        RegistrarInicio(Folio(folio), usuario.actor_id, datos.momento)))


@router.post("/servicios/{folio}/termino", tags=["Ejecucion"], responses=ERRORES,
             summary="Registrar termino (US-08) · Supervisor")
def registrar_termino(folio: str, datos: e.RegistrarTerminoIn = e.RegistrarTerminoIn(),
                      ctx: Contexto = Depends(contexto),
                      usuario: Usuario = Depends(requiere(Rol.SUPERVISOR))):
    return _devolver(ctx, folio, ctx.app.ejecucion.registrarTermino(
        RegistrarTermino(Folio(folio), usuario.actor_id, datos.momento)))


@router.post("/servicios/{folio}/ausencias", tags=["Personal"], responses=ERRORES,
             summary="Reportar ausencia (CU-03) · Supervisor")
def reportar_ausencia(folio: str, datos: e.ReportarAusenciaIn,
                      ctx: Contexto = Depends(contexto),
                      usuario: Usuario = Depends(requiere(Rol.SUPERVISOR))):
    return _devolver(ctx, folio, ctx.app.personal.reportarAusencia(
        ReportarAusencia(Folio(folio), datos.empleado_id, usuario.actor_id)))


@router.post("/servicios/{folio}/reasignaciones", tags=["Personal"], responses=ERRORES,
             summary="Reasignar personal o declarar sin reemplazo (CU-03) · Administracion")
def reasignar_personal(folio: str, datos: e.ReasignarPersonalIn,
                       ctx: Contexto = Depends(contexto),
                       usuario: Usuario = Depends(requiere(Rol.ADMINISTRACION))):
    return _devolver(ctx, folio, ctx.app.personal.reasignarPersonal(
        ReasignarPersonal(Folio(folio), datos.empleado_id, datos.sustituto_id,
                          usuario.actor_id)))


@router.post("/servicios/{folio}/extras", status_code=201, tags=["Ejecucion"],
             responses=ERRORES, summary="Registrar extra en sitio (CU-04) · Supervisor")
def registrar_extra(folio: str, datos: e.RegistrarExtraIn,
                    ctx: Contexto = Depends(contexto),
                    usuario: Usuario = Depends(requiere(Rol.SUPERVISOR))):
    return _devolver(ctx, folio, ctx.app.ejecucion.registrarExtra(
        RegistrarExtra(Folio(folio), datos.descripcion, usuario.actor_id)))


@router.post("/servicios/{folio}/extras/{extra_id}/confirmacion", tags=["Ejecucion"],
             responses=ERRORES,
             summary="Confirmar extra fuera de catalogo (CU-04) · Coordinador")
def confirmar_extra(folio: str, extra_id: str, ctx: Contexto = Depends(contexto),
                    usuario: Usuario = Depends(requiere(Rol.COORDINADOR))):
    return _devolver(ctx, folio, ctx.app.ejecucion.confirmarExtra(
        ConfirmarExtra(Folio(folio), extra_id, usuario.actor_id)))


@router.post("/servicios/{folio}/incidencias", status_code=201, tags=["Ejecucion"],
             responses=ERRORES, summary="Documentar incidencia · Supervisor")
def documentar_incidencia(folio: str, datos: e.DocumentarIncidenciaIn,
                          ctx: Contexto = Depends(contexto),
                          usuario: Usuario = Depends(requiere(Rol.SUPERVISOR))):
    return _devolver(ctx, folio, ctx.app.ejecucion.documentarIncidencia(
        DocumentarIncidencia(Folio(folio), datos.tipo, datos.descripcion,
                             usuario.actor_id, datos.empleado_id)))


@router.post("/servicios/{folio}/incidencias/{incidencia_id}/revision", tags=["Cierre"],
             responses=ERRORES, summary="Marcar incidencia como revisada · Administracion")
def revisar_incidencia(folio: str, incidencia_id: str, ctx: Contexto = Depends(contexto),
                       usuario: Usuario = Depends(requiere(Rol.ADMINISTRACION))):
    return _devolver(ctx, folio, ctx.app.cierre.revisarIncidencia(
        RevisarIncidencia(Folio(folio), incidencia_id, usuario.actor_id)))


@router.post("/servicios/{folio}/cierre", tags=["Cierre"], responses=ERRORES,
             summary="Cerrar para facturacion (CU-05) · Administracion")
def cerrar_para_facturacion(folio: str, ctx: Contexto = Depends(contexto),
                            usuario: Usuario = Depends(requiere(Rol.ADMINISTRACION))):
    return _devolver(ctx, folio, ctx.app.cierre.cerrarParaFacturacion(
        CerrarParaFacturacion(Folio(folio), usuario.actor_id)))


# ---- Consultas ----
@router.get("/disponibilidad", tags=["Consultas"], responses=ERRORES,
            summary="Disponibilidad de cuadrillas por fecha (US-05) · personal interno")
def consultar_disponibilidad(fecha: date = Query(description="AAAA-MM-DD"),
                             ctx: Contexto = Depends(contexto),
                             _: Usuario = Depends(requiere(*STAFF))):
    filas = ctx.app.consultas.consultarDisponibilidad(ConsultarDisponibilidad(fecha))
    return [{"cuadrilla_id": f.cuadrilla_id, "libre": f.libre} for f in filas]


@router.get("/panel", tags=["Consultas"], responses=ERRORES,
            summary="Panel operativo (US-18) · el cliente ve solo lo suyo")
def panel_operativo(ctx: Contexto = Depends(contexto),
                    usuario: Usuario = Depends(usuario_actual)):
    return ctx.panel.resumen(usuario.actor_id if usuario.rol == Rol.CLIENTE else None)


@router.get("/salud", tags=["Sistema"], summary="Verificacion de que la API responde (publico)")
def salud():
    return {"estado": "ok"}
