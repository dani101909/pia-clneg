"""Lado de lectura (CQRS basico): consultas con View Models propios.

No cargan Aggregates ni reutilizan el modelo de escritura (Etapa 6).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ConsultarDisponibilidad:           # Query (US-05)
    fecha: date


@dataclass(frozen=True)
class DisponibilidadDTO:                 # View Model de lectura
    cuadrilla_id: str
    libre: bool


class DisponibilidadReadRepository(ABC):
    @abstractmethod
    def disponibilidadPorFecha(self, fecha: date) -> list: ...


class ConsultasAppService:
    def __init__(self, lectura: DisponibilidadReadRepository):
        self._lectura = lectura

    def consultarDisponibilidad(self, consulta: ConsultarDisponibilidad):
        return self._lectura.disponibilidadPorFecha(consulta.fecha)
