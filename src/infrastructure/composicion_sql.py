"""Raiz de composicion con persistencia SQL (misma aplicacion, otros repositorios)."""
from ..application.cierre_app_service import CierreAppService
from ..application.consultas import ConsultasAppService
from ..application.cotizaciones_app_service import CotizacionesAppService
from ..application.ejecucion_app_service import EjecucionAppService
from ..application.personal_app_service import PersonalAppService
from ..application.programacion_app_service import ProgramacionAppService
from ..domain.servicios_de_dominio import AsignadorDeCuadrilla, PoliticaDeExtras
from .adaptadores import FacturacionEventAdapter, NotificacionAdapter
from .composicion import Aplicacion
from .sql_repositorios import (ConfiguracionRepositorySql, CotizacionRepositorySql,
                               CuadrillaRepositorySql, DisponibilidadReadRepositorySql,
                               EmpleadoRepositorySql, ServicioRepositorySql,
                               UnitOfWorkSql)


def construirAplicacionSql(conexion) -> Aplicacion:
    """Arma la aplicacion sobre UNA conexion (una transaccion por caso de uso)."""
    uow = UnitOfWorkSql(conexion)
    cotizaciones = CotizacionRepositorySql(conexion)
    servicios = ServicioRepositorySql(conexion)
    cuadrillas = CuadrillaRepositorySql(conexion)
    empleados = EmpleadoRepositorySql(conexion)
    configuracion = ConfiguracionRepositorySql(conexion)
    notificaciones = NotificacionAdapter()
    facturacion = FacturacionEventAdapter()
    return Aplicacion(
        bd=conexion,
        cotizaciones=CotizacionesAppService(cotizaciones, servicios, uow),
        programacion=ProgramacionAppService(
            servicios, cuadrillas, AsignadorDeCuadrilla(servicios), uow),
        personal=PersonalAppService(servicios, empleados, notificaciones, uow),
        ejecucion=EjecucionAppService(servicios, PoliticaDeExtras(), configuracion, uow),
        cierre=CierreAppService(servicios, facturacion, uow),
        consultas=ConsultasAppService(DisponibilidadReadRepositorySql(conexion)),
        notificaciones=notificaciones,
        facturacion=facturacion)