from ..domain.cotizacion import Cotizacion
from ..domain.errores import ErrorDeDominio, FolioDuplicado, NoEncontrado, SinPermiso
from ..domain.repositorios import CotizacionRepository, ServicioRepository
from ..domain.servicio import Servicio
from ..domain.valores import (DatosDelInmueble, Dinero, Estimacion, Folio,
                              Frecuencia)
from .comandos import AceptarCotizacion, EmitirCotizacion
from .resultado import Resultado
from .unit_of_work import UnitOfWork


class CotizacionesAppService:
    """CU-01. Unica operacion con dos Aggregates (excepcion documentada en ADR-002)."""

    def __init__(self, cotizaciones: CotizacionRepository,
                 servicios: ServicioRepository, uow: UnitOfWork):
        self._cotizaciones = cotizaciones
        self._servicios = servicios
        self._uow = uow

    def aceptarCotizacion(self, comando: AceptarCotizacion) -> Resultado:
        try:
            cotizacion = self._cotizaciones.obtenerPorFolio(comando.folio)
            if cotizacion.cliente_id != comando.cliente_id:
                raise SinPermiso("Solo el cliente de la cotizacion puede aceptarla")
            cotizacion.aceptar()                                   # BR-01, C4
            servicio = Servicio.programarDesde(cotizacion, comando.fecha)   # S1
            eventos = cotizacion.extraerEventos() + servicio.extraerEventos()
            self._cotizaciones.guardar(cotizacion)
            self._servicios.guardar(servicio)
            self._uow.commit()
            return Resultado.exitoso(servicio.estado.value, eventos)
        except ErrorDeDominio as error:
            self._uow.rollback()
            return Resultado.fallido(error)

    def emitirCotizacion(self, comando: EmitirCotizacion) -> Resultado:
        """US-01: emite una cotizacion Vigente; el folio no puede repetirse."""
        try:
            try:
                self._cotizaciones.obtenerPorFolio(comando.folio)
            except NoEncontrado:
                pass
            else:
                raise FolioDuplicado(f"Ya existe la cotizacion {comando.folio.valor}")
            cotizacion = Cotizacion.emitir(
                comando.folio, comando.cliente_id,
                DatosDelInmueble(comando.ubicacion, comando.superficie,
                                 comando.tipo_de_inmueble),
                Frecuencia(comando.frecuencia), tuple(comando.extras),
                Estimacion(comando.duracion, comando.personal, Dinero(comando.precio)))
            eventos = cotizacion.extraerEventos()
            self._cotizaciones.guardar(cotizacion)
            self._uow.commit()
            return Resultado.exitoso(cotizacion.estado.value, eventos)
        except ErrorDeDominio as error:
            self._uow.rollback()
            return Resultado.fallido(error)
