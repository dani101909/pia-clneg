"""Una conexion (y una transaccion) por peticion; arma la aplicacion sobre ella."""
from dataclasses import dataclass

from fastapi import Request

from ..application.resultado import Resultado
from ..infrastructure.composicion import Aplicacion
from ..infrastructure.composicion_sql import construirAplicacionSql
from ..infrastructure.sql_repositorios import (CotizacionRepositorySql,
                                               ServicioRepositorySql)


class ErrorDeNegocio(Exception):
    """Resultado fallido de un caso de uso; main.py lo traduce a HTTP."""

    def __init__(self, codigo, detalle=""):
        super().__init__(codigo)
        self.codigo = codigo
        self.detalle = detalle


@dataclass
class Contexto:
    app: Aplicacion
    cotizaciones: CotizacionRepositorySql    # solo lectura para las vistas
    servicios: ServicioRepositorySql


def contexto(request: Request):
    conexion = request.app.state.bd.abrir()
    try:
        yield Contexto(construirAplicacionSql(conexion),
                       CotizacionRepositorySql(conexion), ServicioRepositorySql(conexion))
    finally:
        conexion.cerrar()


def exigir(resultado: Resultado) -> Resultado:
    if not resultado.exito:
        raise ErrorDeNegocio(resultado.codigo, resultado.detalle)
    return resultado
