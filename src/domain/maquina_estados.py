"""Maquina de estados generica (patron State Machine).

Una maquina se define SOLO con una tabla: (estado_origen, disparador) -> estado_destino.
Todo lo que no esta en la tabla es una transicion invalida. La tabla es la unica
fuente de verdad de los estados permitidos; las entidades no repiten `if estado == ...`.
"""
from types import MappingProxyType

from .errores import TransicionInvalida


class MaquinaDeEstados:
    def __init__(self, nombre, transiciones):
        self.nombre = nombre
        self._tabla = MappingProxyType(dict(transiciones))

    def puede(self, estado, disparador):
        return (estado, disparador) in self._tabla

    def siguiente(self, estado, disparador):
        """Estado destino, o TransicionInvalida si la tabla no la permite."""
        try:
            return self._tabla[(estado, disparador)]
        except KeyError:
            raise TransicionInvalida(
                f"{self.nombre} en estado {estado.value}: "
                f"no admite '{disparador.value}'") from None

    def disparadoresDesde(self, estado):
        return tuple(d for (origen, d) in self._tabla if origen == estado)

    def esFinal(self, estado):
        return not self.disparadoresDesde(estado)

    def transiciones(self):
        """Lista (origen, disparador, destino); sirve para documentar y probar."""
        return tuple((o, d, dest) for (o, d), dest in self._tabla.items())