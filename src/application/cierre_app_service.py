from ..domain.errores import ErrorDeDominio
from ..domain.repositorios import ServicioRepository
from ..domain.valores import Actor, Rol
from .comandos import CerrarParaFacturacion, RevisarIncidencia
from .puertos import FacturacionPort
from .resultado import Resultado
from .unit_of_work import UnitOfWork


class CierreAppService:
    """CU-05. El bloqueo por pendientes lo decide el Aggregate (BR-07), no el servicio."""

    def __init__(self, servicios: ServicioRepository, facturacion: FacturacionPort,
                 uow: UnitOfWork):
        self._servicios = servicios
        self._facturacion = facturacion
        self._uow = uow

    def cerrarParaFacturacion(self, comando: CerrarParaFacturacion) -> Resultado:
        try:
            servicio = self._servicios.obtenerPorFolio(comando.folio)
            servicio.cerrarParaFacturacion(Actor(comando.admin_id, Rol.ADMINISTRACION))
            eventos = servicio.extraerEventos()
            self._servicios.guardar(servicio)
            self._uow.commit()
            for evento in eventos:                      # tras el commit
                self._facturacion.publicar(evento)
            return Resultado.exitoso(servicio.estado.value, eventos)
        except ErrorDeDominio as error:                 # incluye CIERRE_BLOQUEADO
            self._uow.rollback()
            return Resultado.fallido(error)

    def revisarIncidencia(self, comando: RevisarIncidencia) -> Resultado:
        try:
            servicio = self._servicios.obtenerPorFolio(comando.folio)
            servicio.revisarIncidencia(comando.incidencia_id,
                                       Actor(comando.admin_id, Rol.ADMINISTRACION))
            self._servicios.guardar(servicio)
            self._uow.commit()
            return Resultado.exitoso("Revisada")
        except ErrorDeDominio as error:
            self._uow.rollback()
            return Resultado.fallido(error)
