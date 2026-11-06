"""Domain Services: reglas que no pertenecen a una sola entidad.

Las reglas en si viven como Specifications (especificaciones.py); estos
servicios solo reunen los datos que cada Specification necesita.
"""
from .configuracion import ConfiguracionDePoliticas
from .cuadrilla import Cuadrilla
from .especificaciones import CuadrillaLibreEnFecha, ExtraRequiereConfirmacion
from .repositorios import ServicioRepository
from .valores import FechaDeServicio


class AsignadorDeCuadrilla:
    """Verifica que la cuadrilla este libre ese dia (US-04, US-05, Q1).

    Consulta una abstraccion (ServicioRepository), no SQL.
    """

    def __init__(self, servicios: ServicioRepository):
        self._servicios = servicios

    def estaLibre(self, cuadrilla: Cuadrilla, fecha: FechaDeServicio) -> bool:
        confirmados = self._servicios.obtenerConfirmadosPorFecha(fecha)
        return CuadrillaLibreEnFecha(confirmados).esSatisfechaPor(cuadrilla)


class PoliticaDeExtras:
    """Decide si un extra requiere confirmacion del coordinador (BR-04).

    Hoy aplica el criterio de catalogo (US-10). Cuando se valide el umbral de
    "precio significativo" se combina con `|` sin tocar a quien la usa.
    """

    def requiereConfirmacion(self, descripcion: str,
                             politicas: ConfiguracionDePoliticas) -> bool:
        return ExtraRequiereConfirmacion(politicas).esSatisfechaPor(descripcion)