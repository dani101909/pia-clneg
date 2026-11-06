"""Raiz de composicion: aqui y solo aqui se eligen las implementaciones."""
from dataclasses import dataclass

from ..application.cierre_app_service import CierreAppService
from ..application.consultas import ConsultasAppService
from ..application.cotizaciones_app_service import CotizacionesAppService
from ..application.ejecucion_app_service import EjecucionAppService
from ..application.personal_app_service import PersonalAppService
from ..application.programacion_app_service import ProgramacionAppService
from ..domain.servicios_de_dominio import AsignadorDeCuadrilla, PoliticaDeExtras
from .adaptadores import FacturacionEventAdapter, NotificacionAdapter
from .en_memoria import (BaseDeDatosEnMemoria, ConfiguracionRepositoryEnMemoria,
                         CotizacionRepositoryEnMemoria, CuadrillaRepositoryEnMemoria,
                         DisponibilidadReadRepositoryEnMemoria,
                         EmpleadoRepositoryEnMemoria, ServicioRepositoryEnMemoria,
                         UnitOfWorkEnMemoria)


@dataclass
class Aplicacion:
    bd: BaseDeDatosEnMemoria
    cotizaciones: CotizacionesAppService
    programacion: ProgramacionAppService
    personal: PersonalAppService
    ejecucion: EjecucionAppService
    cierre: CierreAppService
    consultas: ConsultasAppService
    notificaciones: NotificacionAdapter
    facturacion: FacturacionEventAdapter


def construirAplicacion() -> Aplicacion:
    bd = BaseDeDatosEnMemoria()
    uow = UnitOfWorkEnMemoria(bd)
    cotizaciones = CotizacionRepositoryEnMemoria(bd)
    servicios = ServicioRepositoryEnMemoria(bd)
    cuadrillas = CuadrillaRepositoryEnMemoria(bd)
    empleados = EmpleadoRepositoryEnMemoria(bd)
    configuracion = ConfiguracionRepositoryEnMemoria(bd)
    notificaciones = NotificacionAdapter()
    facturacion = FacturacionEventAdapter()
    return Aplicacion(
        bd=bd,
        cotizaciones=CotizacionesAppService(cotizaciones, servicios, uow),
        programacion=ProgramacionAppService(
            servicios, cuadrillas, AsignadorDeCuadrilla(servicios), uow),
        personal=PersonalAppService(servicios, empleados, notificaciones, uow),
        ejecucion=EjecucionAppService(servicios, PoliticaDeExtras(), configuracion, uow),
        cierre=CierreAppService(servicios, facturacion, uow),
        consultas=ConsultasAppService(DisponibilidadReadRepositoryEnMemoria(bd)),
        notificaciones=notificaciones,
        facturacion=facturacion)
