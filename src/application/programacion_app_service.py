from ..domain.errores import ErrorDeDominio
from ..domain.repositorios import CuadrillaRepository, ServicioRepository
from ..domain.servicios_de_dominio import AsignadorDeCuadrilla
from ..domain.valores import Actor, Rol
from .comandos import ConfirmarCuadrilla
from .resultado import Resultado
from .unit_of_work import UnitOfWork


class ProgramacionAppService:
    """CU-02. Coordina; la regla de confirmacion vive en Servicio (S2)."""

    def __init__(self, servicios: ServicioRepository,
                 cuadrillas: CuadrillaRepository,
                 asignador: AsignadorDeCuadrilla, uow: UnitOfWork):
        self._servicios = servicios
        self._cuadrillas = cuadrillas
        self._asignador = asignador
        self._uow = uow

    def confirmarCuadrilla(self, comando: ConfirmarCuadrilla) -> Resultado:
        try:
            servicio = self._servicios.obtenerPorFolio(comando.folio)
            cuadrilla = self._cuadrillas.obtenerPorId(comando.cuadrilla_id)
            disponible = self._asignador.estaLibre(cuadrilla, servicio.exigirFecha())
            actor = Actor(comando.coordinador_id, Rol.COORDINADOR)
            servicio.confirmarCuadrilla(cuadrilla.id, disponible, actor)
            eventos = servicio.extraerEventos()
            self._servicios.guardar(servicio)
            self._uow.commit()
            return Resultado.exitoso(servicio.estado.value, eventos)
        except ErrorDeDominio as error:
            self._uow.rollback()
            return Resultado.fallido(error)
