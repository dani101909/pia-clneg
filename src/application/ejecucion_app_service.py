from ..domain.errores import ErrorDeDominio
from ..domain.repositorios import ConfiguracionRepository, ServicioRepository
from ..domain.servicios_de_dominio import PoliticaDeExtras
from ..domain.valores import Actor, Rol
from .comandos import (ConfirmarExtra, DocumentarIncidencia, RegistrarExtra,
                       RegistrarInicio, RegistrarTermino)
from .resultado import Resultado
from .unit_of_work import UnitOfWork


class EjecucionAppService:
    """CU-04, inicio/termino (US-08) e incidencias. La politica decide si hay catalogo; el Servicio registra el extra."""

    def __init__(self, servicios: ServicioRepository, politica: PoliticaDeExtras,
                 configuraciones: ConfiguracionRepository, uow: UnitOfWork):
        self._servicios = servicios
        self._politica = politica
        self._configuraciones = configuraciones
        self._uow = uow

    def registrarExtra(self, comando: RegistrarExtra) -> Resultado:
        try:
            servicio = self._servicios.obtenerPorFolio(comando.folio)
            politicas = self._configuraciones.obtenerPoliticasVigentes()
            requiere = self._politica.requiereConfirmacion(comando.descripcion, politicas)
            actor = Actor(comando.supervisor_id, Rol.SUPERVISOR)
            extra = servicio.registrarExtra(comando.descripcion, requiere, actor)
            eventos = servicio.extraerEventos()
            self._servicios.guardar(servicio)
            self._uow.commit()
            return Resultado.exitoso(extra.estado.value, eventos)
        except ErrorDeDominio as error:
            self._uow.rollback()
            return Resultado.fallido(error)

    def confirmarExtra(self, comando: ConfirmarExtra) -> Resultado:
        try:
            servicio = self._servicios.obtenerPorFolio(comando.folio)
            servicio.confirmarExtra(comando.extra_id,
                                    Actor(comando.coordinador_id, Rol.COORDINADOR))
            eventos = servicio.extraerEventos()
            self._servicios.guardar(servicio)
            self._uow.commit()
            return Resultado.exitoso("Confirmado", eventos)
        except ErrorDeDominio as error:
            self._uow.rollback()
            return Resultado.fallido(error)

    def registrarInicio(self, comando: RegistrarInicio) -> Resultado:
        return self._sobreServicio(
            comando.folio,
            lambda s: s.registrarInicio(Actor(comando.supervisor_id, Rol.SUPERVISOR),
                                        comando.momento),
            lambda s, _: s.estado.value)

    def registrarTermino(self, comando: RegistrarTermino) -> Resultado:
        return self._sobreServicio(
            comando.folio,
            lambda s: s.registrarTermino(Actor(comando.supervisor_id, Rol.SUPERVISOR),
                                         comando.momento),
            lambda s, _: s.estado.value)

    def documentarIncidencia(self, comando: DocumentarIncidencia) -> Resultado:
        return self._sobreServicio(
            comando.folio,
            lambda s: s.documentarIncidencia(
                comando.tipo, comando.descripcion,
                Actor(comando.supervisor_id, Rol.SUPERVISOR), comando.empleado_id),
            lambda s, incidencia: incidencia.id)

    def _sobreServicio(self, folio, operacion, valor) -> Resultado:
        """Plantilla comun: cargar, operar sobre el Aggregate, guardar y confirmar."""
        try:
            servicio = self._servicios.obtenerPorFolio(folio)
            devuelto = operacion(servicio)
            eventos = servicio.extraerEventos()
            self._servicios.guardar(servicio)
            self._uow.commit()
            return Resultado.exitoso(valor(servicio, devuelto), eventos)
        except ErrorDeDominio as error:
            self._uow.rollback()
            return Resultado.fallido(error)
