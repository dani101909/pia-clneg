"""Interfaces de Repository, expresadas en terminos del dominio (sin SQL)."""
from abc import ABC, abstractmethod


class CotizacionRepository(ABC):
    @abstractmethod
    def guardar(self, cotizacion): ...

    @abstractmethod
    def obtenerPorFolio(self, folio): ...


class ServicioRepository(ABC):
    @abstractmethod
    def guardar(self, servicio): ...

    @abstractmethod
    def obtenerPorFolio(self, folio): ...

    @abstractmethod
    def obtenerConfirmadosPorFecha(self, fecha):
        """Servicios con cuadrilla confirmada el dia de `fecha`."""


class CuadrillaRepository(ABC):
    @abstractmethod
    def obtenerPorId(self, cuadrilla_id): ...


class EmpleadoRepository(ABC):
    @abstractmethod
    def obtenerPorId(self, empleado_id): ...


class ConfiguracionRepository(ABC):
    @abstractmethod
    def obtenerPoliticasVigentes(self): ...
