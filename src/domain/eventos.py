"""Domain Events (mapa de dominio, seccion Domain Events)."""
from dataclasses import dataclass

from .base import EventoDeDominio


@dataclass(frozen=True)
class CotizacionEmitida(EventoDeDominio):
    pass


@dataclass(frozen=True)
class CotizacionAceptada(EventoDeDominio):
    pass


@dataclass(frozen=True)
class CotizacionRechazada(EventoDeDominio):
    pass


@dataclass(frozen=True)
class ServicioProgramado(EventoDeDominio):
    pass


@dataclass(frozen=True)
class CuadrillaConfirmada(EventoDeDominio):
    cuadrilla_id: str


@dataclass(frozen=True)
class ServicioIniciado(EventoDeDominio):
    pass


@dataclass(frozen=True)
class ServicioTerminado(EventoDeDominio):
    pass


@dataclass(frozen=True)
class IncidenciaDocumentada(EventoDeDominio):
    incidencia_id: str


@dataclass(frozen=True)
class AusenciaReportada(EventoDeDominio):
    empleado_id: str


@dataclass(frozen=True)
class PersonalReasignado(EventoDeDominio):
    empleado_original: str
    sustituto: str


@dataclass(frozen=True)
class ServicioEnRiesgo(EventoDeDominio):
    sugerencia: str = "Contactar al cliente"


@dataclass(frozen=True)
class ExtraAceptado(EventoDeDominio):
    extra_id: str


@dataclass(frozen=True)
class ExtraPendienteDeConfirmacion(EventoDeDominio):
    extra_id: str


@dataclass(frozen=True)
class ExtraConfirmado(EventoDeDominio):
    extra_id: str


@dataclass(frozen=True)
class ServicioCerradoParaFacturacion(EventoDeDominio):
    pass
