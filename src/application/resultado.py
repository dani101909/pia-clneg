"""Resultado que se devuelve al usuario, en terminos del negocio."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Resultado:
    exito: bool
    codigo: str = ""                 # p. ej. CIERRE_BLOQUEADO
    detalle: object = ""             # p. ej. lista de lo que falta documentar
    valor: object = None
    eventos: tuple = field(default_factory=tuple)

    @classmethod
    def exitoso(cls, valor=None, eventos=()):
        return cls(True, valor=valor, eventos=tuple(eventos))

    @classmethod
    def fallido(cls, error):
        return cls(False, codigo=error.codigo, detalle=error.detalle)
