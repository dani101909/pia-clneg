"""Piezas comunes: eventos de dominio y raiz de Aggregate."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class EventoDeDominio:
    """Hecho del negocio que ya ocurrio."""
    folio: object
    ocurrido_en: datetime = field(default_factory=datetime.now, kw_only=True)


class RaizDeAggregate:
    """Acumula los eventos que emite; la capa de aplicacion los extrae."""

    def __init__(self):
        self._eventos = []

    def _registrar(self, evento):
        self._eventos.append(evento)

    def extraerEventos(self):
        eventos = list(self._eventos)
        self._eventos.clear()
        return eventos
