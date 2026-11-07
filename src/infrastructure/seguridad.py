"""Seguridad: hash de contrasenas y tokens firmados con vencimiento (solo biblioteca estandar).

Contrasenas: PBKDF2-HMAC-SHA256 con sal aleatoria. Se guardan como
    pbkdf2_sha256$<iteraciones>$<sal base64>$<hash base64>
Tokens:  <payload base64url>.<firma base64url>, firmados con HMAC-SHA256 y un
secreto del servidor (variable de entorno CLEANPRO_SECRET). El payload lleva
el id del usuario (sub), su rol y la hora de vencimiento (exp).
"""
import base64
import hashlib
import hmac
import json
import os
import time

ITERACIONES_POR_DEFECTO = 600_000
VIGENCIA_POR_DEFECTO = 3600          # segundos (1 hora)


class TokenInvalido(Exception):
    """Token ausente, mal formado, con firma incorrecta o vencido."""


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode("ascii").rstrip("=")


def _desb64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


# ---------------------------------------------------------------- contrasenas
def hashearClave(clave: str, sal: bytes = None,
                 iteraciones: int = ITERACIONES_POR_DEFECTO) -> str:
    if not clave:
        raise ValueError("La clave no puede estar vacia")
    sal = sal if sal is not None else os.urandom(16)
    derivado = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, iteraciones)
    return f"pbkdf2_sha256${iteraciones}${_b64(sal)}${_b64(derivado)}"


def verificarClave(clave: str, almacenado: str) -> bool:
    """True solo si la clave corresponde al hash; nunca lanza por datos mal formados."""
    try:
        algoritmo, iteraciones, sal, esperado = almacenado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        derivado = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"),
                                       _desb64(sal), int(iteraciones))
        return hmac.compare_digest(derivado, _desb64(esperado))
    except (ValueError, TypeError, AttributeError):
        return False


# --------------------------------------------------------------------- tokens
class ServicioDeTokens:
    def __init__(self, secreto: str, vigencia_segundos: int = VIGENCIA_POR_DEFECTO):
        if not secreto or len(secreto) < 16:
            raise ValueError("El secreto debe tener al menos 16 caracteres")
        self._secreto = secreto.encode("utf-8")
        self._vigencia = vigencia_segundos

    @classmethod
    def desdeEntorno(cls):
        """Lee CLEANPRO_SECRET; sin ella la autenticacion no puede arrancar."""
        secreto = os.environ.get("CLEANPRO_SECRET")
        if not secreto:
            raise RuntimeError("Falta la variable de entorno CLEANPRO_SECRET")
        return cls(secreto)

    def _firmar(self, cuerpo: str) -> str:
        return _b64(hmac.new(self._secreto, cuerpo.encode("ascii"), hashlib.sha256).digest())

    def emitir(self, usuario_id: str, rol: str, ahora: float = None) -> str:
        ahora = time.time() if ahora is None else ahora
        payload = {"sub": usuario_id, "rol": rol, "exp": int(ahora) + self._vigencia}
        cuerpo = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        return f"{cuerpo}.{self._firmar(cuerpo)}"

    def verificar(self, token: str, ahora: float = None) -> dict:
        """Devuelve {'sub', 'rol', 'exp'} o lanza TokenInvalido."""
        ahora = time.time() if ahora is None else ahora
        try:
            cuerpo, firma = token.split(".")
        except (ValueError, AttributeError):
            raise TokenInvalido("Token mal formado") from None
        if not hmac.compare_digest(firma, self._firmar(cuerpo)):
            raise TokenInvalido("Firma invalida")
        try:
            payload = json.loads(_desb64(cuerpo))
            if not {"sub", "rol", "exp"} <= payload.keys():
                raise KeyError
        except (ValueError, KeyError, TypeError, AttributeError):
            raise TokenInvalido("Contenido del token invalido") from None
        if payload["exp"] <= ahora:
            raise TokenInvalido("Token vencido")
        return payload
