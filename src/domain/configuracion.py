"""Componente de soporte ConfiguracionDePoliticas (RNF-04).

NINGUN valor esta definido en la U2: tiempo de cortesia, criterio de precio
significativo, cobro por acceso negado y penalizacion por reprogramacion
tardia quedan en None hasta validarse con el negocio. Solo Administracion
puede modificarla y cada cambio conserva quien, cuando y por que (RNF-03).
"""
from dataclasses import dataclass, field
from datetime import datetime

from .errores import SinPermiso
from .valores import Actor, Motivo, Rol


@dataclass
class ConfiguracionDePoliticas:
    version: int = 1
    tiempo_de_cortesia: object = None
    catalogo_de_extras: frozenset = frozenset()
    criterio_precio_significativo: object = None
    politica_cobro_acceso_negado: object = None
    penalizacion_reprogramacion_tardia: object = None
    historial: list = field(default_factory=list)

    def actualizarCatalogoDeExtras(self, catalogo, actor: Actor, motivo: Motivo,
                                   momento: datetime = None):
        if actor.rol is not Rol.ADMINISTRACION:
            raise SinPermiso("Solo Administracion modifica las politicas")
        self.catalogo_de_extras = frozenset(catalogo)
        self.version += 1
        self.historial.append((actor.id, momento or datetime.now(),
                               "catalogo_de_extras", motivo.texto))
