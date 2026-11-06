"""Aggregate Cotizacion (raiz: Folio). Invariantes C1 a C5."""
from enum import Enum

from .base import RaizDeAggregate
from .errores import CotizacionNoVigente, DatosIncompletos
from .eventos import CotizacionAceptada, CotizacionEmitida, CotizacionRechazada


class EstadoDeCotizacion(Enum):
    VIGENTE = "Vigente"
    ACEPTADA = "Aceptada"
    RECHAZADA = "Rechazada"


class Cotizacion(RaizDeAggregate):
    def __init__(self, folio, cliente_id, datos, frecuencia, extras, estimacion):
        super().__init__()
        self.folio = folio
        self.cliente_id = cliente_id
        self.datos = datos
        self.frecuencia = frecuencia
        self.extras = tuple(extras)          # extras cotizados (no los de sitio)
        self.estimacion = estimacion
        self.estado = EstadoDeCotizacion.VIGENTE

    @classmethod
    def emitir(cls, folio, cliente_id, datos, frecuencia, extras, estimacion):
        """C1: no se emite sin los cinco datos. C2: folio y estado Vigente.

        `extras` debe indicarse explicitamente; una tupla vacia significa
        "sin extras" (supuesto a validar con el stakeholder).
        """
        if None in (folio, datos, frecuencia, extras, estimacion):
            raise DatosIncompletos(
                "Se requieren ubicacion, superficie, tipo de inmueble, "
                "frecuencia y extras")
        cotizacion = cls(folio, cliente_id, datos, frecuencia, extras, estimacion)
        cotizacion._registrar(CotizacionEmitida(folio))
        return cotizacion

    def aceptar(self):
        """C4 y C5: solo una cotizacion Vigente se acepta; no asigna cuadrilla."""
        self._exigirVigente()
        self.estado = EstadoDeCotizacion.ACEPTADA
        self._registrar(CotizacionAceptada(self.folio))

    def rechazar(self):
        self._exigirVigente()
        self.estado = EstadoDeCotizacion.RECHAZADA
        self._registrar(CotizacionRechazada(self.folio))

    def _exigirVigente(self):
        if self.estado is not EstadoDeCotizacion.VIGENTE:
            raise CotizacionNoVigente(
                f"La cotizacion esta {self.estado.value}; solo una Vigente "
                "puede aceptarse o rechazarse")
