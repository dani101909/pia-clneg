"""Autenticacion en el borde HTTP (RNF-02): quien eres, no que puedes hacer.

* `usuario_actual`: exige `Authorization: Bearer <token>`, valida la firma y el
  vencimiento y devuelve el Usuario ACTIVO. El rol se lee de la base en cada
  peticion (el `rol` que viaja en el token se ignora), asi una baja o un cambio de
  rol se aplica al instante.
* `LimitadorDeIntentos`: bloqueo temporal tras varios logins fallidos.

El dominio no conoce esto: solo recibe un Actor ya resuelto.
"""
import time

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..domain.errores import NoEncontrado
from ..domain.usuario import Usuario
from ..domain.valores import Rol
from ..infrastructure.seguridad import TokenInvalido
from ..infrastructure.sql_usuarios import UsuarioRepositorySql
from .dependencias import Contexto, ErrorDeNegocio, contexto

esquema_bearer = HTTPBearer(auto_error=False, description=(
    "Token obtenido en POST /auth/login. Pegalo sin la palabra Bearer."))


def usuario_actual(request: Request,
                   credenciales: HTTPAuthorizationCredentials = Depends(esquema_bearer),
                   ctx: Contexto = Depends(contexto)) -> Usuario:
    if credenciales is None:
        raise ErrorDeNegocio("NO_AUTENTICADO", "Falta el token (Authorization: Bearer ...)")
    try:
        datos = request.app.state.tokens.verificar(credenciales.credentials)
    except TokenInvalido as error:
        raise ErrorDeNegocio("NO_AUTENTICADO", str(error))
    try:
        usuario = ctx.usuarios.obtenerPorNombreDeUsuario(datos["sub"])
    except NoEncontrado:
        raise ErrorDeNegocio("NO_AUTENTICADO", "El usuario del token ya no existe")
    if not usuario.activo:
        raise ErrorDeNegocio("NO_AUTENTICADO", "El usuario esta desactivado")
    return usuario


STAFF = (Rol.COORDINADOR, Rol.SUPERVISOR, Rol.ADMINISTRACION)      # personal interno


def requiere(*roles: Rol):
    """Dependencia: usuario autenticado cuyo rol (el de la base) esta permitido."""
    def dependencia(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            permitidos = ", ".join(r.value for r in roles)
            raise ErrorDeNegocio("SIN_PERMISO",
                                 f"Tu rol ({usuario.rol.value}) no puede hacer esto. "
                                 f"Permitido para: {permitidos}")
        return usuario
    return dependencia


class LimitadorDeIntentos:
    """Tras `maximo` fallos seguidos de un usuario, lo bloquea `segundos` segundos.

    Vive en la memoria del proceso: basta para una instancia; con varias habria que
    moverlo a la base o a Redis.
    """

    def __init__(self, maximo=5, segundos=60, reloj=time.monotonic):
        self._maximo, self._segundos, self._reloj = maximo, segundos, reloj
        self._estado = {}              # usuario -> (fallos, bloqueado_hasta)

    def segundosRestantes(self, usuario: str) -> int:
        _, hasta = self._estado.get(usuario, (0, 0))
        restante = hasta - self._reloj()
        return int(restante) + 1 if restante > 0 else 0

    def registrarFallo(self, usuario: str):
        fallos, hasta = self._estado.get(usuario, (0, 0))
        if hasta and hasta <= self._reloj():       # el bloqueo ya vencio: se empieza de nuevo
            fallos, hasta = 0, 0
        fallos += 1
        if fallos >= self._maximo:
            self._estado[usuario] = (0, self._reloj() + self._segundos)
        else:
            self._estado[usuario] = (fallos, hasta)

    def registrarAcierto(self, usuario: str):
        self._estado.pop(usuario, None)
