"""Errores del dominio expresados en terminos del negocio.

Cada error lleva un `codigo` estable (por ejemplo CIERRE_BLOQUEADO) que la
capa de aplicacion devuelve al usuario sin exponer excepciones tecnicas.
"""


class ErrorDeDominio(Exception):
    codigo = "ERROR_DE_DOMINIO"

    def __init__(self, detalle=""):
        super().__init__(str(detalle))
        self.detalle = detalle


class DatosIncompletos(ErrorDeDominio):
    codigo = "DATOS_INCOMPLETOS"          # US-01


class ValorInvalido(ErrorDeDominio):
    codigo = "VALOR_INVALIDO"


class CotizacionNoVigente(ErrorDeDominio):
    codigo = "COTIZACION_NO_VIGENTE"      # C4, BR-01


class TransicionInvalida(ErrorDeDominio):
    codigo = "TRANSICION_INVALIDA"


class SinPermiso(ErrorDeDominio):
    codigo = "SIN_PERMISO"                # RNF-02


class ServicioSinFecha(ErrorDeDominio):
    codigo = "SERVICIO_SIN_FECHA"


class CuadrillaNoDisponible(ErrorDeDominio):
    codigo = "CUADRILLA_NO_DISPONIBLE"    # BR-02, US-04


class SustitutoNoDisponible(ErrorDeDominio):
    codigo = "SUSTITUTO_NO_DISPONIBLE"    # US-07


class TerminoInvalido(ErrorDeDominio):
    codigo = "TERMINO_INVALIDO"           # S3, US-08


class CierreBloqueado(ErrorDeDominio):
    codigo = "CIERRE_BLOQUEADO"           # S12, BR-07, US-17


class NoEncontrado(ErrorDeDominio):
    codigo = "NO_ENCONTRADO"


class FolioDuplicado(ErrorDeDominio):
    codigo = "FOLIO_DUPLICADO"