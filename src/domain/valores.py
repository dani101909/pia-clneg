"""Value Objects y tipos de apoyo (inmutables, definidos por sus valores)."""
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum

from .errores import DatosIncompletos, TerminoInvalido, ValorInvalido


class Rol(Enum):
    CLIENTE = "Cliente"
    COORDINADOR = "Coordinador"
    SUPERVISOR = "Supervisor"
    ADMINISTRACION = "Administracion"


@dataclass(frozen=True)
class Actor:
    """Quien ejecuta la operacion; el dominio decide con su rol (RNF-02)."""
    id: str
    rol: Rol


@dataclass(frozen=True)
class Folio:
    valor: str

    def __post_init__(self):
        if not self.valor:
            raise DatosIncompletos("El folio es obligatorio")


@dataclass(frozen=True)
class Dinero:
    # La moneda no esta definida en la U2 (pendiente de validar).
    monto: Decimal

    def __post_init__(self):
        if Decimal(self.monto) < 0:
            raise ValorInvalido("El monto no puede ser negativo")


@dataclass(frozen=True)
class DatosDelInmueble:
    ubicacion: str
    superficie: Decimal
    tipo_de_inmueble: str

    def __post_init__(self):
        if not self.ubicacion or not self.tipo_de_inmueble:
            raise DatosIncompletos("Ubicacion y tipo de inmueble son obligatorios")
        if self.superficie is None or Decimal(self.superficie) <= 0:
            raise DatosIncompletos("La superficie debe ser mayor que 0")


@dataclass(frozen=True)
class Frecuencia:
    valor: str

    def __post_init__(self):
        if not self.valor:
            raise DatosIncompletos("La frecuencia es obligatoria")


@dataclass(frozen=True)
class Estimacion:
    """Duracion, personal y precio (US-02). El coordinador puede editarla."""
    duracion: timedelta
    personal: int
    precio: Dinero

    def __post_init__(self):
        if self.personal <= 0:
            raise ValorInvalido("El personal requerido debe ser mayor que 0")


@dataclass(frozen=True)
class FechaDeServicio:
    fecha_hora: datetime

    @property
    def dia(self) -> date:
        return self.fecha_hora.date()


@dataclass(frozen=True)
class Motivo:
    texto: str

    def __post_init__(self):
        if not self.texto:
            raise ValorInvalido("El motivo es obligatorio")


@dataclass(frozen=True)
class AsignacionDePersonal:
    """Conserva al empleado original y al sustituto (US-07, RNF-03)."""
    empleado_original: str
    sustituto: str
    realizada_por: str
    cuando: datetime
    motivo: Motivo


@dataclass(frozen=True)
class RegistroDeTiempo:
    """Inicio y termino; el termino nunca es anterior al inicio (S3, US-08)."""
    inicio: datetime = None
    termino: datetime = None

    def conInicio(self, momento: datetime) -> "RegistroDeTiempo":
        return replace(self, inicio=momento)

    def conTermino(self, momento: datetime) -> "RegistroDeTiempo":
        if self.inicio is None:
            raise TerminoInvalido("No se puede registrar el termino sin hora de inicio")
        if momento < self.inicio:
            raise TerminoInvalido("El termino no puede ser anterior al inicio")
        return replace(self, termino=momento)
