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


class UsuarioRepository(ABC):
    @abstractmethod
    def guardar(self, usuario): ...

    @abstractmethod
    def obtenerPorNombreDeUsuario(self, nombre_de_usuario):
        """Devuelve el Usuario o lanza NoEncontrado."""

    @abstractmethod
    def contar(self): ...
