"""Estados del Servicio y su State Machine (BPMN de la U2, invariantes S1 a S13)."""
from enum import Enum

from .maquina_estados import MaquinaDeEstados


class EstadoDeServicio(Enum):
    PROGRAMADO = "Programado"                    # programacion tentativa
    CUADRILLA_CONFIRMADA = "CuadrillaConfirmada"
    EN_EJECUCION = "EnEjecucion"
    TERMINADO = "Terminado"
    CERRADO_PARA_FACTURACION = "CerradoParaFacturacion"
    EN_RIESGO = "EnRiesgo"
    NO_REALIZADO = "NoRealizado"
    CANCELADO = "Cancelado"


class DisparadorDeServicio(Enum):
    CONFIRMAR_CUADRILLA = "confirmar cuadrilla"              # US-04, BR-02
    INICIAR = "iniciar servicio"                             # US-08
    TERMINAR = "terminar servicio"                           # US-08
    DECLARAR_SIN_REEMPLAZO = "declarar sin reemplazo"        # US-07
    CERRAR_PARA_FACTURACION = "cerrar para facturacion"      # US-17, BR-07
    # Los tres siguientes ya existen en la tabla; sus casos de uso se agregan despues.
    CANCELAR = "cancelar servicio"                           # US-16
    NEGAR_ACCESO = "registrar acceso negado"                 # US-13
    DAR_POR_NO_REALIZADO = "dar por no realizado"            # BPMN: sin reemplazo


E = EstadoDeServicio
D = DisparadorDeServicio

MAQUINA_DE_SERVICIO = MaquinaDeEstados("Servicio", {
    (E.PROGRAMADO, D.CONFIRMAR_CUADRILLA): E.CUADRILLA_CONFIRMADA,
    (E.PROGRAMADO, D.CANCELAR): E.CANCELADO,
    (E.CUADRILLA_CONFIRMADA, D.INICIAR): E.EN_EJECUCION,
    (E.CUADRILLA_CONFIRMADA, D.DECLARAR_SIN_REEMPLAZO): E.EN_RIESGO,
    (E.CUADRILLA_CONFIRMADA, D.CANCELAR): E.CANCELADO,
    (E.EN_EJECUCION, D.TERMINAR): E.TERMINADO,
    (E.EN_EJECUCION, D.DECLARAR_SIN_REEMPLAZO): E.EN_RIESGO,
    (E.EN_EJECUCION, D.NEGAR_ACCESO): E.NO_REALIZADO,
    (E.EN_RIESGO, D.DAR_POR_NO_REALIZADO): E.NO_REALIZADO,
    (E.TERMINADO, D.CERRAR_PARA_FACTURACION): E.CERRADO_PARA_FACTURACION,
})