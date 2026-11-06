from ..domain.errores import ErrorDeDominio
from ..domain.repositorios import EmpleadoRepository, ServicioRepository
from ..domain.valores import Actor, Rol
from .comandos import ReasignarPersonal, ReportarAusencia
from .puertos import NotificacionPort
from .resultado import Resultado
from .unit_of_work import UnitOfWork


class PersonalAppService:
    """CU-03. Administracion recibe aviso inmediato (RNF-01) tras el commit."""

    def __init__(self, servicios: ServicioRepository, empleados: EmpleadoRepository,
                 notificaciones: NotificacionPort, uow: UnitOfWork):
        self._servicios = servicios
        self._empleados = empleados
        self._notificaciones = notificaciones
        self._uow = uow

    def reportarAusencia(self, comando: ReportarAusencia) -> Resultado:
        try:
            servicio = self._servicios.obtenerPorFolio(comando.folio)
            empleado = self._empleados.obtenerPorId(comando.empleado_id)
            actor = Actor(comando.supervisor_id, Rol.SUPERVISOR)
            servicio.reportarAusencia(empleado.id, actor)
            return self._cerrar(servicio)
        except ErrorDeDominio as error:
            self._uow.rollback()
            return Resultado.fallido(error)

    def reasignarPersonal(self, comando: ReasignarPersonal) -> Resultado:
        try:
            servicio = self._servicios.obtenerPorFolio(comando.folio)
            actor = Actor(comando.admin_id, Rol.ADMINISTRACION)
            if comando.sustituto_id is None:          # sin reemplazo -> en riesgo
                servicio.declararSinReemplazo(actor)
            else:
                sustituto = self._empleados.obtenerPorId(comando.sustituto_id)
                sustituto.exigirDisponibleParaCubrir()
                servicio.reasignarPersonal(comando.empleado_id, sustituto.id, actor)
            return self._cerrar(servicio)
        except ErrorDeDominio as error:
            self._uow.rollback()
            return Resultado.fallido(error)

    def _cerrar(self, servicio) -> Resultado:
        eventos = servicio.extraerEventos()
        self._servicios.guardar(servicio)
        self._uow.commit()
        for evento in eventos:
            self._notificaciones.notificar(evento)
        return Resultado.exitoso(servicio.estado.value, eventos)
