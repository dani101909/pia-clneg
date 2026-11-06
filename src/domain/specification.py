"""Patron Specification: reglas de negocio pequenas, nombradas y combinables.

Cada regla responde `esSatisfechaPor(candidato)` y, si no se cumple, explica por
que con `razonesDeIncumplimiento` (util para mostrar el motivo al usuario).
Se combinan con Y / O / No, o con los operadores  &  |  ~ .
"""
from abc import ABC, abstractmethod


class Especificacion(ABC):
    descripcion = "La regla no se cumple"

    @abstractmethod
    def esSatisfechaPor(self, candidato) -> bool: ...

    def razonesDeIncumplimiento(self, candidato):
        """Lista vacia si se cumple; si no, los motivos en lenguaje de negocio."""
        return [] if self.esSatisfechaPor(candidato) else [self.descripcion]

    def y(self, otra):
        return Y(self, otra)

    def o(self, otra):
        return O(self, otra)

    def no(self):
        return No(self)

    __and__ = y
    __or__ = o
    __invert__ = no


class Y(Especificacion):
    def __init__(self, izquierda: Especificacion, derecha: Especificacion):
        self._izq, self._der = izquierda, derecha
        self.descripcion = f"({izquierda.descripcion} Y {derecha.descripcion})"

    def esSatisfechaPor(self, candidato):
        return (self._izq.esSatisfechaPor(candidato)
                and self._der.esSatisfechaPor(candidato))

    def razonesDeIncumplimiento(self, candidato):
        return (self._izq.razonesDeIncumplimiento(candidato)
                + self._der.razonesDeIncumplimiento(candidato))


class O(Especificacion):
    def __init__(self, izquierda: Especificacion, derecha: Especificacion):
        self._izq, self._der = izquierda, derecha
        self.descripcion = f"({izquierda.descripcion} O {derecha.descripcion})"

    def esSatisfechaPor(self, candidato):
        return (self._izq.esSatisfechaPor(candidato)
                or self._der.esSatisfechaPor(candidato))

    def razonesDeIncumplimiento(self, candidato):
        if self.esSatisfechaPor(candidato):
            return []
        return (self._izq.razonesDeIncumplimiento(candidato)
                + self._der.razonesDeIncumplimiento(candidato))


class No(Especificacion):
    def __init__(self, interna: Especificacion):
        self._interna = interna
        self.descripcion = f"NO ({interna.descripcion})"

    def esSatisfechaPor(self, candidato):
        return not self._interna.esSatisfechaPor(candidato)

    def razonesDeIncumplimiento(self, candidato):
        if self.esSatisfechaPor(candidato):
            return []
        return [f"No debe cumplirse: {self._interna.descripcion}"]