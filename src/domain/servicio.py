"""Aggregate Servicio (raiz: Folio). Invariantes S1 a S13 del mapa de dominio.

Alcance actual: CU-01 a CU-05. Los cambios de estado los gobierna la State
Machine de `estado_servicio.py`; aqui solo se validan rol y reglas de negocio.
Reprogramacion, cancelacion, ajuste de precio y acceso negado (US-11 a US-16)
todavia no tienen caso de uso, aunque sus transiciones ya estan en la tabla.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .base import RaizDeAggregate
from .errores import (CierreBloqueado, CuadrillaNoDisponible, DatosIncompletos,
                      ServicioSinFecha, SinPermiso, TransicionInvalida)
from .cotizacion import EstadoDeCotizacion
from .estado_servicio import (MAQUINA_DE_SERVICIO, DisparadorDeServicio as D,
                              EstadoDeServicio)
from .eventos import (AusenciaReportada, CuadrillaConfirmada, ExtraAceptado,
                      ExtraConfirmado, ExtraPendienteDeConfirmacion,
                      IncidenciaDocumentada, PersonalReasignado,
                      ServicioCerradoParaFacturacion, ServicioEnRiesgo,
                      ServicioIniciado, ServicioProgramado, ServicioTerminado)
from .valores import (Actor, AsignacionDePersonal, Motivo, RegistroDeTiempo,
                      Rol)


class TipoDeIncidencia(Enum):
    AUSENCIA = "Ausencia"
    ACCESO_NEGADO = "AccesoNegado"
    MATERIAL_ESPECIAL = "MaterialEspecial"
    DANIO_REPORTADO = "DanioReportado"


class EstadoDeIncidencia(Enum):
    PENDIENTE_DE_REVISION = "Pendiente de revision"
    REVISADA = "Revisada"


class EstadoDeExtra(Enum):
    ACEPTADO = "Aceptado"                        # en catalogo (BR-04)
    PENDIENTE_DE_CONFIRMACION = "Pendiente de confirmacion"
    CONFIRMADO = "Confirmado"


@dataclass
class Incidencia:
    """Entidad del Servicio con identidad local (S5)."""
    id: str
    tipo: TipoDeIncidencia
    descripcion: str
    hora: datetime
    reportada_por: str
    empleado_id: str = None
    estado: EstadoDeIncidencia = EstadoDeIncidencia.PENDIENTE_DE_REVISION


@dataclass
class Extra:
    """Extra solicitado en sitio (no cotizado)."""
    id: str
    descripcion: str
    solicitado_por: str
    estado: EstadoDeExtra


@dataclass(frozen=True)
class CambioRegistrado:
    """Quien, cuando y por que (RNF-03)."""
    quien: str
    cuando: datetime
    que: str
    motivo: str = ""


_ACTIVOS = (EstadoDeServicio.CUADRILLA_CONFIRMADA, EstadoDeServicio.EN_EJECUCION)


class Servicio(RaizDeAggregate):
    def __init__(self, folio, fecha=None):
        super().__init__()
        self.folio = folio                       # mismo Folio de la Cotizacion
        self.fecha = fecha
        self.estado = EstadoDeServicio.PROGRAMADO
        self.cuadrilla_id = None
        self.tiempo = RegistroDeTiempo()
        self.asignaciones = []
        self.incidencias = []
        self.extras = []
        self.historial = []

    # ---- S1: nace de una Cotizacion Aceptada, sin cuadrilla definitiva ----
    @classmethod
    def programarDesde(cls, cotizacion, fecha=None):
        if cotizacion.estado is not EstadoDeCotizacion.ACEPTADA:
            raise TransicionInvalida(
                "El Servicio solo nace de una Cotizacion Aceptada")
        servicio = cls(cotizacion.folio, fecha)
        servicio._registrar(ServicioProgramado(servicio.folio))
        return servicio

    def exigirFecha(self):
        if self.fecha is None:
            raise ServicioSinFecha("El servicio aun no tiene fecha programada")
        return self.fecha

    @property
    def tieneCuadrillaConfirmada(self):
        return self.cuadrilla_id is not None and self.estado not in (
            EstadoDeServicio.CANCELADO, EstadoDeServicio.NO_REALIZADO)

    # ---- S2 / BR-02: confirmacion de cuadrilla ----
    def confirmarCuadrilla(self, cuadrilla_id, disponible: bool, actor: Actor,
                           momento: datetime = None):
        self._exigirRol(actor, Rol.COORDINADOR)
        destino = self._siguiente(D.CONFIRMAR_CUADRILLA)
        if not disponible:
            raise CuadrillaNoDisponible(
                f"La cuadrilla {cuadrilla_id} no esta libre en la fecha del servicio")
        self.cuadrilla_id = cuadrilla_id
        self.estado = destino
        self._anotar(actor, "Cuadrilla confirmada", cuadrilla_id, momento)
        self._registrar(CuadrillaConfirmada(self.folio, cuadrilla_id))

    # ---- S3 / US-08: inicio y termino ----
    def registrarInicio(self, actor: Actor, momento: datetime = None):
        self._exigirRol(actor, Rol.SUPERVISOR)
        destino = self._siguiente(D.INICIAR)
        self.tiempo = self.tiempo.conInicio(momento or datetime.now())
        self.estado = destino
        self._registrar(ServicioIniciado(self.folio))

    def registrarTermino(self, actor: Actor, momento: datetime = None):
        self._exigirRol(actor, Rol.SUPERVISOR)
        tiempo = self.tiempo.conTermino(momento or datetime.now())  # valida S3
        destino = self._siguiente(D.TERMINAR)
        self.tiempo = tiempo
        self.estado = destino
        self._registrar(ServicioTerminado(self.folio))

    # ---- S5: incidencias ----
    def documentarIncidencia(self, tipo, descripcion, actor: Actor,
                             empleado_id=None, momento: datetime = None):
        self._exigirRol(actor, Rol.SUPERVISOR)
        self._exigirEstado(*_ACTIVOS, EstadoDeServicio.EN_RIESGO,
                           EstadoDeServicio.TERMINADO)
        if not descripcion:
            raise DatosIncompletos("La incidencia requiere descripcion")
        incidencia = Incidencia(
            id=f"INC-{len(self.incidencias) + 1}", tipo=tipo,
            descripcion=descripcion, hora=momento or datetime.now(),
            reportada_por=actor.id, empleado_id=empleado_id)
        self.incidencias.append(incidencia)
        self._registrar(IncidenciaDocumentada(self.folio, incidencia.id))
        return incidencia

    def revisarIncidencia(self, incidencia_id, actor: Actor):
        self._exigirRol(actor, Rol.ADMINISTRACION)
        incidencia = self._buscar(self.incidencias, incidencia_id, "incidencia")
        incidencia.estado = EstadoDeIncidencia.REVISADA

    # ---- S4 / BR-03: ausencia, reasignacion y servicio en riesgo ----
    def reportarAusencia(self, empleado_id, actor: Actor, momento: datetime = None):
        self._exigirRol(actor, Rol.SUPERVISOR)
        self._exigirEstado(*_ACTIVOS)
        incidencia = self.documentarIncidencia(
            TipoDeIncidencia.AUSENCIA, f"Ausencia del empleado {empleado_id}",
            actor, empleado_id=empleado_id, momento=momento)
        self._registrar(AusenciaReportada(self.folio, empleado_id))
        return incidencia

    def reasignarPersonal(self, empleado_original, sustituto, actor: Actor,
                          motivo: Motivo = None, momento: datetime = None):
        self._exigirRol(actor, Rol.ADMINISTRACION)
        self._exigirEstado(*_ACTIVOS)
        self._exigirAusenciaReportada(empleado_original)
        if any(a.empleado_original == empleado_original for a in self.asignaciones):
            raise TransicionInvalida(
                f"La ausencia de {empleado_original} ya fue reasignada")
        motivo = motivo or Motivo(f"Ausencia del empleado {empleado_original}")
        cuando = momento or datetime.now()
        self.asignaciones.append(AsignacionDePersonal(
            empleado_original, sustituto, actor.id, cuando, motivo))
        self._anotar(actor, "Personal reasignado",
                     f"{empleado_original} -> {sustituto}: {motivo.texto}", cuando)
        self._registrar(PersonalReasignado(self.folio, empleado_original, sustituto))

    def declararSinReemplazo(self, actor: Actor, momento: datetime = None):
        """Ausencia sin personal disponible: el servicio queda en riesgo."""
        self._exigirRol(actor, Rol.ADMINISTRACION)
        destino = self._siguiente(D.DECLARAR_SIN_REEMPLAZO)
        if not any(i.tipo is TipoDeIncidencia.AUSENCIA for i in self.incidencias):
            raise TransicionInvalida("No hay una ausencia reportada que cubrir")
        self.estado = destino
        self._anotar(actor, "Servicio en riesgo", "Sin reemplazo disponible", momento)
        self._registrar(ServicioEnRiesgo(self.folio))

    # ---- S6 / BR-04: extras en sitio ----
    def registrarExtra(self, descripcion, requiere_confirmacion: bool,
                       actor: Actor):
        self._exigirRol(actor, Rol.SUPERVISOR)
        self._exigirEstado(EstadoDeServicio.EN_EJECUCION)
        if not descripcion:
            raise DatosIncompletos("El extra requiere descripcion")
        estado = (EstadoDeExtra.PENDIENTE_DE_CONFIRMACION if requiere_confirmacion
                  else EstadoDeExtra.ACEPTADO)
        extra = Extra(f"EXT-{len(self.extras) + 1}", descripcion, actor.id, estado)
        self.extras.append(extra)
        evento = (ExtraPendienteDeConfirmacion if requiere_confirmacion
                  else ExtraAceptado)
        self._registrar(evento(self.folio, extra.id))
        return extra

    def confirmarExtra(self, extra_id, actor: Actor):
        self._exigirRol(actor, Rol.COORDINADOR)
        extra = self._buscar(self.extras, extra_id, "extra")
        if extra.estado is not EstadoDeExtra.PENDIENTE_DE_CONFIRMACION:
            raise TransicionInvalida("El extra no esta pendiente de confirmacion")
        extra.estado = EstadoDeExtra.CONFIRMADO
        self._registrar(ExtraConfirmado(self.folio, extra.id))

    # ---- S12 / BR-07 / US-17: cierre para facturacion ----
    def cerrarParaFacturacion(self, actor: Actor, momento: datetime = None):
        self._exigirRol(actor, Rol.ADMINISTRACION)
        destino = self._siguiente(D.CERRAR_PARA_FACTURACION)  # exige termino registrado
        pendientes = self.pendientesPorDocumentar()
        if pendientes:
            raise CierreBloqueado(pendientes)
        self.estado = destino
        self._anotar(actor, "Cerrado para facturacion", "", momento)
        self._registrar(ServicioCerradoParaFacturacion(self.folio))

    def pendientesPorDocumentar(self):
        """Detalle de que incidencia o extra falta documentar (US-17)."""
        faltantes = [
            f"Incidencia {i.id} ({i.tipo.value}) pendiente de revision"
            for i in self.incidencias
            if i.estado is EstadoDeIncidencia.PENDIENTE_DE_REVISION]
        faltantes += [
            f"Extra {e.id} ({e.descripcion}) pendiente de confirmacion"
            for e in self.extras
            if e.estado is EstadoDeExtra.PENDIENTE_DE_CONFIRMACION]
        return faltantes

    @property
    def accionesDisponibles(self):
        """Disparadores que la State Machine permite desde el estado actual."""
        return MAQUINA_DE_SERVICIO.disparadoresDesde(self.estado)

    # ---- apoyo interno ----
    def _siguiente(self, disparador):
        return MAQUINA_DE_SERVICIO.siguiente(self.estado, disparador)

    def _exigirRol(self, actor: Actor, *roles):
        if actor.rol not in roles:
            permitidos = ", ".join(r.value for r in roles)
            raise SinPermiso(f"Esta operacion corresponde a: {permitidos}")

    def _exigirEstado(self, *estados):
        if self.estado not in estados:
            esperados = ", ".join(e.value for e in estados)
            raise TransicionInvalida(
                f"El servicio esta {self.estado.value}; se requiere: {esperados}")

    def _exigirAusenciaReportada(self, empleado_id):
        if not any(i.tipo is TipoDeIncidencia.AUSENCIA and i.empleado_id == empleado_id
                   for i in self.incidencias):
            raise TransicionInvalida(
                f"No hay una ausencia reportada para el empleado {empleado_id}")

    def _anotar(self, actor, que, motivo="", momento=None):
        self.historial.append(CambioRegistrado(
            actor.id, momento or datetime.now(), que, str(motivo)))

    @staticmethod
    def _buscar(coleccion, identificador, nombre):
        for elemento in coleccion:
            if elemento.id == identificador:
                return elemento
        raise TransicionInvalida(f"No existe {nombre} {identificador} en el servicio")