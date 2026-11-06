"""Aggregates minimos Cuadrilla y Empleado.

La Cuadrilla no guarda agenda: su disponibilidad se deriva de los servicios
ya confirmados (US-05), asi una confirmacion modifica un solo Aggregate.
"""
from dataclasses import dataclass

from .errores import SustitutoNoDisponible


@dataclass
class Cuadrilla:
    id: str
    integrantes: tuple = ()      # EmpleadoId de sus integrantes


@dataclass
class Empleado:
    id: str
    nombre: str
    disponible_para_cubrir: bool = True

    def exigirDisponibleParaCubrir(self):
        if not self.disponible_para_cubrir:
            raise SustitutoNoDisponible(
                f"El empleado {self.id} no esta disponible para cubrir la ausencia")
