"""Usuario del sistema: quien inicia sesion y con que rol actua (RNF-02).

`actor_id` es el identificador con el que el dominio reconoce a la persona
(cli-1, coord-1, sup-1, admin-1...).
"""
from dataclasses import dataclass

from .valores import Actor, Rol


@dataclass(frozen=True)
class Usuario:
    nombre_de_usuario: str
    nombre: str
    rol: Rol
    actor_id: str
    clave_hash: str
    activo: bool = True

    @property
    def actor(self) -> Actor:
        return Actor(self.actor_id, self.rol)

    def __repr__(self):                       # nunca imprimir el hash en logs
        return (f"Usuario({self.nombre_de_usuario!r}, rol={self.rol.value}, "
                f"actor={self.actor_id!r}, activo={self.activo})")
