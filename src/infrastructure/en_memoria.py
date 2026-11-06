"""Implementaciones en memoria de los Repository y la Unit of Work.

Corresponden a las clases *EnMemoria del diagrama de clases: una por Repository
mas UnitOfWorkEnMemoria. Cumplen las mismas interfaces (LSP) y se verifican con
tests/test_contrato_repositorios.py, asi que una version SQL puede reemplazarlas
sin tocar dominio ni aplicacion si pasa esa misma bateria.

Los repositorios entregan y guardan COPIAS: un cambio en un Aggregate solo
persiste cuando el servicio de aplicacion llama a guardar() y luego commit().
"""
from copy import deepcopy
from datetime import date

from ..application.consultas import DisponibilidadDTO, DisponibilidadReadRepository
from ..application.unit_of_work import UnitOfWork
from ..domain.configuracion import ConfiguracionDePoliticas
from ..domain.errores import NoEncontrado
from ..domain.repositorios import (ConfiguracionRepository, CotizacionRepository,
                                    CuadrillaRepository, EmpleadoRepository,
                                    ServicioRepository)


class BaseDeDatosEnMemoria:
    def __init__(self):
        self.cotizaciones = {}
        self.servicios = {}
        self.cuadrillas = {}
        self.empleados = {}
        self.politicas = ConfiguracionDePoliticas()
        self._respaldo = None

    def antesDeEscribir(self):
        if self._respaldo is None:
            self._respaldo = deepcopy((self.cotizaciones, self.servicios))

    def confirmar(self):
        self._respaldo = None

    def revertir(self):
        if self._respaldo is not None:
            self.cotizaciones, self.servicios = self._respaldo
            self._respaldo = None


class UnitOfWorkEnMemoria(UnitOfWork):
    def __init__(self, bd: BaseDeDatosEnMemoria):
        self._bd = bd

    def commit(self):
        self._bd.confirmar()

    def rollback(self):
        self._bd.revertir()


def _obtener(coleccion, clave, nombre):
    try:
        return deepcopy(coleccion[clave])
    except KeyError:
        raise NoEncontrado(f"No existe {nombre} {clave}") from None


class CotizacionRepositoryEnMemoria(CotizacionRepository):
    def __init__(self, bd):
        self._bd = bd

    def guardar(self, cotizacion):
        self._bd.antesDeEscribir()
        self._bd.cotizaciones[cotizacion.folio] = deepcopy(cotizacion)

    def obtenerPorFolio(self, folio):
        return _obtener(self._bd.cotizaciones, folio, "la cotizacion")


class ServicioRepositoryEnMemoria(ServicioRepository):
    def __init__(self, bd):
        self._bd = bd

    def guardar(self, servicio):
        self._bd.antesDeEscribir()
        self._bd.servicios[servicio.folio] = deepcopy(servicio)

    def obtenerPorFolio(self, folio):
        return _obtener(self._bd.servicios, folio, "el servicio")

    def obtenerConfirmadosPorFecha(self, fecha):
        return [deepcopy(s) for s in self._bd.servicios.values()
                if s.fecha is not None and s.fecha.dia == fecha.dia
                and s.tieneCuadrillaConfirmada]


class CuadrillaRepositoryEnMemoria(CuadrillaRepository):
    def __init__(self, bd):
        self._bd = bd

    def obtenerPorId(self, cuadrilla_id):
        return _obtener(self._bd.cuadrillas, cuadrilla_id, "la cuadrilla")


class EmpleadoRepositoryEnMemoria(EmpleadoRepository):
    def __init__(self, bd):
        self._bd = bd

    def obtenerPorId(self, empleado_id):
        return _obtener(self._bd.empleados, empleado_id, "el empleado")


class ConfiguracionRepositoryEnMemoria(ConfiguracionRepository):
    def __init__(self, bd):
        self._bd = bd

    def obtenerPoliticasVigentes(self):
        return deepcopy(self._bd.politicas)


class DisponibilidadReadRepositoryEnMemoria(DisponibilidadReadRepository):
    """Lectura directa: arma el DTO sin ensamblar Aggregates de escritura."""

    def __init__(self, bd):
        self._bd = bd

    def disponibilidadPorFecha(self, fecha: date):
        ocupadas = {s.cuadrilla_id for s in self._bd.servicios.values()
                    if s.fecha is not None and s.fecha.dia == fecha
                    and s.tieneCuadrillaConfirmada}
        return [DisponibilidadDTO(c, c not in ocupadas)
                for c in sorted(self._bd.cuadrillas)]
