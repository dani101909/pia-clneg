"""Commands (CQRS): cada uno expresa la intencion completa de un caso de uso."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class AceptarCotizacion:                 # CU-01
    folio: object
    cliente_id: str
    fecha: object = None                 # FechaDeServicio; origen no definido en U2


@dataclass(frozen=True)
class ConfirmarCuadrilla:                # CU-02
    folio: object
    cuadrilla_id: str
    coordinador_id: str


@dataclass(frozen=True)
class ReportarAusencia:                  # CU-03
    folio: object
    empleado_id: str
    supervisor_id: str


@dataclass(frozen=True)
class ReasignarPersonal:                 # CU-03
    folio: object
    empleado_id: str
    sustituto_id: str                    # None si no hay reemplazo disponible
    admin_id: str


@dataclass(frozen=True)
class RegistrarExtra:                    # CU-04
    folio: object
    descripcion: str
    supervisor_id: str


@dataclass(frozen=True)
class ConfirmarExtra:                    # CU-04 (extra fuera de catalogo)
    folio: object
    extra_id: str
    coordinador_id: str


@dataclass(frozen=True)
class RevisarIncidencia:                 # prepara CU-05
    folio: object
    incidencia_id: str
    admin_id: str


@dataclass(frozen=True)
class CerrarParaFacturacion:             # CU-05
    folio: object
    admin_id: str


@dataclass(frozen=True)
class EmitirCotizacion:                  # US-01 (la estimacion la captura el coordinador)
    folio: object
    cliente_id: str
    ubicacion: str
    superficie: Decimal
    tipo_de_inmueble: str
    frecuencia: str
    extras: tuple
    duracion: timedelta
    personal: int
    precio: Decimal


@dataclass(frozen=True)
class RegistrarInicio:                   # US-08
    folio: object
    supervisor_id: str
    momento: datetime = None


@dataclass(frozen=True)
class RegistrarTermino:                  # US-08
    folio: object
    supervisor_id: str
    momento: datetime = None


@dataclass(frozen=True)
class DocumentarIncidencia:              # S5
    folio: object
    tipo: object                         # TipoDeIncidencia
    descripcion: str
    supervisor_id: str
    empleado_id: str = None
