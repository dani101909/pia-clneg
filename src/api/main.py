"""Aplicacion FastAPI. Swagger UI en /docs y OpenAPI en /openapi.json.

Ejecutar:  python -m uvicorn src.api.main:app --reload
BD:        variable DATABASE_URL (SQLite por defecto; PostgreSQL con una URL postgresql://)
"""
import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from ..domain.errores import ErrorDeDominio
from ..infrastructure.base_de_datos import BaseDeDatos
from ..infrastructure.seguridad import (ITERACIONES_POR_DEFECTO, ServicioDeTokens,
                                        hashearClave)
from .autenticacion import LimitadorDeIntentos
from .dependencias import ErrorDeNegocio
from .rutas import router
from .rutas_auth import router as router_auth

log = logging.getLogger("cleanpro")

# Codigo de dominio estable -> estado HTTP
ESTADO_HTTP = {
    "NO_ENCONTRADO": 404,
    "SIN_PERMISO": 403,
    "DATOS_INCOMPLETOS": 422,
    "VALOR_INVALIDO": 422,
    "TERMINO_INVALIDO": 422,
    "COTIZACION_NO_VIGENTE": 409,
    "TRANSICION_INVALIDA": 409,
    "CUADRILLA_NO_DISPONIBLE": 409,
    "SUSTITUTO_NO_DISPONIBLE": 409,
    "SERVICIO_SIN_FECHA": 409,
    "CIERRE_BLOQUEADO": 409,
    "FOLIO_DUPLICADO": 409,
    "CREDENCIALES_INVALIDAS": 401,
    "NO_AUTENTICADO": 401,
    "DEMASIADOS_INTENTOS": 429,
}


def _respuesta(codigo, detalle):
    estado = ESTADO_HTTP.get(codigo, 400)
    cabeceras = {"WWW-Authenticate": "Bearer"} if estado == 401 else None
    return JSONResponse(status_code=estado, headers=cabeceras,
                        content={"codigo": codigo, "detalle": detalle})


def _secreto_de_firma(secreto):
    """Argumento > variable CLEANPRO_SECRET > secreto aleatorio (solo para desarrollo)."""
    secreto = secreto or os.environ.get("CLEANPRO_SECRET")
    if secreto:
        return secreto
    log.warning("CLEANPRO_SECRET no esta definida: se usa un secreto aleatorio y las "
                "sesiones se pierden al reiniciar. Definela en produccion.")
    return secrets.token_urlsafe(32)


def crear_app(url_bd=None, cargar_demo=False, secreto=None, vigencia_segundos=3600,
              iteraciones_clave=ITERACIONES_POR_DEFECTO) -> FastAPI:
    @asynccontextmanager
    async def ciclo_de_vida(app):
        conexion = app.state.bd.abrir()
        try:
            conexion.crearEsquema()
            if cargar_demo:
                from ..infrastructure.datos_demo import cargar, cargarUsuarios
                cargar(conexion)
                cargarUsuarios(conexion, iteraciones=iteraciones_clave)
        finally:
            conexion.cerrar()
        yield

    app = FastAPI(
        title="CleanPro API",
        version="1.0.0",
        description="Servicios de limpieza residencial y empresarial. Dominio con "
                    "Aggregates, State Machine del Servicio y Specifications.",
        lifespan=ciclo_de_vida)
    app.state.bd = BaseDeDatos(url_bd)
    app.state.tokens = ServicioDeTokens(_secreto_de_firma(secreto), vigencia_segundos)
    app.state.limitador = LimitadorDeIntentos()
    app.state.hash_ficticio = hashearClave("clave-ficticia", iteraciones=iteraciones_clave)

    @app.exception_handler(ErrorDeNegocio)
    async def _negocio(_: Request, error: ErrorDeNegocio):
        return _respuesta(error.codigo, error.detalle)

    @app.exception_handler(ErrorDeDominio)       # lecturas directas (p. ej. 404)
    async def _dominio(_: Request, error: ErrorDeDominio):
        return _respuesta(error.codigo, error.detalle)

    app.include_router(router_auth)
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    def interfaz():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    return app


def _desde_entorno():
    import os
    return crear_app(cargar_demo=os.environ.get("CLEANPRO_DEMO") == "1")


app = _desde_entorno()