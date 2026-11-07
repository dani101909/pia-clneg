"""Endpoints de autenticacion: POST /auth/login y GET /auth/yo."""
import time

from fastapi import APIRouter, Depends, Request

from ..domain.errores import NoEncontrado
from ..domain.usuario import Usuario
from ..infrastructure.seguridad import verificarClave
from . import esquemas as e
from .autenticacion import usuario_actual
from .dependencias import Contexto, ErrorDeNegocio, contexto

router = APIRouter(prefix="/auth", tags=["Autenticacion"])
ERRORES = {401: {"model": e.ErrorOut}, 429: {"model": e.ErrorOut}}


def _usuario_out(u: Usuario) -> dict:
    return {"usuario": u.nombre_de_usuario, "nombre": u.nombre, "rol": u.rol.value,
            "actor_id": u.actor_id}


@router.post("/login", response_model=e.TokenOut, responses=ERRORES,
             summary="Iniciar sesion y obtener un token")
def iniciar_sesion(datos: e.LoginIn, request: Request, ctx: Contexto = Depends(contexto)):
    estado = request.app.state
    espera = estado.limitador.segundosRestantes(datos.usuario)
    if espera:
        raise ErrorDeNegocio("DEMASIADOS_INTENTOS",
                             f"Demasiados intentos fallidos. Espera {espera} s.")
    try:
        usuario = ctx.usuarios.obtenerPorNombreDeUsuario(datos.usuario)
        correcta = verificarClave(datos.clave, usuario.clave_hash)
    except NoEncontrado:
        # Se hace el mismo trabajo que con un usuario real para que "no existe" no
        # responda mas rapido que "clave incorrecta" (enumeracion de usuarios).
        verificarClave(datos.clave, estado.hash_ficticio)
        usuario, correcta = None, False
    if not (correcta and usuario.activo):
        estado.limitador.registrarFallo(datos.usuario)
        raise ErrorDeNegocio("CREDENCIALES_INVALIDAS", "Usuario o contrasena incorrectos")
    estado.limitador.registrarAcierto(datos.usuario)
    token = estado.tokens.emitir(usuario.nombre_de_usuario, usuario.rol.value)
    vence = estado.tokens.verificar(token)["exp"]
    return {"access_token": token, "expira_en": int(vence - time.time()),
            "usuario": _usuario_out(usuario)}


@router.get("/yo", response_model=e.UsuarioOut, responses=ERRORES,
            summary="Usuario autenticado (con el rol actual en la base)")
def quien_soy(usuario: Usuario = Depends(usuario_actual)):
    return _usuario_out(usuario)
