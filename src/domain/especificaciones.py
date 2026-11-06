"""Specifications concretas de CleanPro (cada una apunta a su regla de la U2)."""
from .estado_servicio import MAQUINA_DE_SERVICIO, DisparadorDeServicio, EstadoDeServicio
from .specification import Especificacion


class CuadrillaLibreEnFecha(Especificacion):
    """BR-02, US-04, US-05: la cuadrilla no tiene otro servicio confirmado ese dia."""
    descripcion = "La cuadrilla ya tiene un servicio confirmado ese dia"

    def __init__(self, servicios_confirmados_ese_dia):
        self._confirmados = tuple(servicios_confirmados_ese_dia)

    def esSatisfechaPor(self, cuadrilla):
        return all(s.cuadrilla_id != cuadrilla.id for s in self._confirmados)


class ExtraRequiereConfirmacion(Especificacion):
    """BR-04, US-10: un extra fuera del catalogo lo confirma el Coordinador."""
    descripcion = "El extra esta en el catalogo y no requiere confirmacion"

    def __init__(self, politicas):
        self._politicas = politicas

    def esSatisfechaPor(self, descripcion_del_extra):
        return descripcion_del_extra not in self._politicas.catalogo_de_extras


class EmpleadoDisponibleParaCubrir(Especificacion):
    """US-07: solo un empleado disponible puede sustituir a quien falto."""
    descripcion = "El empleado no esta disponible para cubrir la ausencia"

    def esSatisfechaPor(self, empleado):
        return empleado.disponible_para_cubrir


class ServicioAdmite(Especificacion):
    """La State Machine permite ese disparador desde el estado actual del servicio."""

    def __init__(self, disparador: DisparadorDeServicio):
        self._disparador = disparador
        self.descripcion = f"El servicio admite '{disparador.value}'"

    def esSatisfechaPor(self, servicio):
        return MAQUINA_DE_SERVICIO.puede(servicio.estado, self._disparador)

    def razonesDeIncumplimiento(self, servicio):
        if self.esSatisfechaPor(servicio):
            return []
        return [f"El servicio esta {servicio.estado.value}; "
                f"no admite '{self._disparador.value}'"]


class SinPendientesPorDocumentar(Especificacion):
    """S12, BR-07, US-17: ninguna incidencia ni extra queda sin documentar."""
    descripcion = "Hay incidencias o extras pendientes por documentar"

    def esSatisfechaPor(self, servicio):
        return not servicio.pendientesPorDocumentar()

    def razonesDeIncumplimiento(self, servicio):
        return list(servicio.pendientesPorDocumentar())     # dice cual falta


def servicioCerrableParaFacturacion():
    """US-17: termino registrado Y nada pendiente por documentar."""
    return (ServicioAdmite(DisparadorDeServicio.CERRAR_PARA_FACTURACION)
            & SinPendientesPorDocumentar())


def servicioCancelable():
    """US-16: solo si aun no inicia (lo define la State Machine)."""
    return ServicioAdmite(DisparadorDeServicio.CANCELAR)