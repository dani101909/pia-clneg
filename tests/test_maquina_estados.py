"""State Machine del Servicio: tabla de transiciones y su uso desde el Aggregate."""
import unittest
from datetime import datetime

from src.domain import errores as e
from src.domain.estado_servicio import (MAQUINA_DE_SERVICIO,
                                        DisparadorDeServicio as D,
                                        EstadoDeServicio as E)
from src.domain.maquina_estados import MaquinaDeEstados

from .utiles import (ADMIN, COORDINADOR, SUPERVISOR, servicioConCuadrilla,
                     servicioEnEjecucion, servicioProgramado, servicioTerminado)

PERMITIDAS = {
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
}


class TablaDeTransicionesTest(unittest.TestCase):
    def test_cada_transicion_permitida_lleva_a_su_destino(self):
        for (origen, disparador), destino in PERMITIDAS.items():
            with self.subTest(origen=origen, disparador=disparador):
                self.assertTrue(MAQUINA_DE_SERVICIO.puede(origen, disparador))
                self.assertEqual(MAQUINA_DE_SERVICIO.siguiente(origen, disparador),
                                 destino)

    def test_toda_otra_combinacion_es_transicion_invalida(self):
        for origen in E:
            for disparador in D:
                if (origen, disparador) in PERMITIDAS:
                    continue
                with self.subTest(origen=origen, disparador=disparador):
                    self.assertFalse(MAQUINA_DE_SERVICIO.puede(origen, disparador))
                    with self.assertRaises(e.TransicionInvalida):
                        MAQUINA_DE_SERVICIO.siguiente(origen, disparador)

    def test_estados_finales(self):
        finales = {estado for estado in E if MAQUINA_DE_SERVICIO.esFinal(estado)}
        self.assertEqual(finales, {E.CERRADO_PARA_FACTURACION, E.NO_REALIZADO,
                                   E.CANCELADO})

    def test_la_tabla_no_se_puede_modificar_desde_fuera(self):
        self.assertEqual(len(MAQUINA_DE_SERVICIO.transiciones()), len(PERMITIDAS))
        with self.assertRaises(TypeError):
            MAQUINA_DE_SERVICIO._tabla[(E.PROGRAMADO, D.INICIAR)] = E.EN_EJECUCION

    def test_maquina_generica_con_otra_tabla(self):
        m = MaquinaDeEstados("Prueba", {(E.PROGRAMADO, D.CANCELAR): E.CANCELADO})
        self.assertEqual(m.siguiente(E.PROGRAMADO, D.CANCELAR), E.CANCELADO)
        self.assertEqual(m.disparadoresDesde(E.PROGRAMADO), (D.CANCELAR,))
        with self.assertRaises(e.TransicionInvalida):
            m.siguiente(E.CANCELADO, D.CANCELAR)


class ServicioUsaLaMaquinaTest(unittest.TestCase):
    def test_flujo_completo_recorre_los_estados_en_orden(self):
        s = servicioProgramado()
        self.assertEqual(s.estado, E.PROGRAMADO)
        s.confirmarCuadrilla("cuad-1", True, COORDINADOR)
        self.assertEqual(s.estado, E.CUADRILLA_CONFIRMADA)
        s.registrarInicio(SUPERVISOR, datetime(2026, 10, 20, 8, 5))
        self.assertEqual(s.estado, E.EN_EJECUCION)
        s.registrarTermino(SUPERVISOR, datetime(2026, 10, 20, 12, 0))
        self.assertEqual(s.estado, E.TERMINADO)
        s.cerrarParaFacturacion(ADMIN)
        self.assertEqual(s.estado, E.CERRADO_PARA_FACTURACION)

    def test_no_se_puede_iniciar_sin_confirmar_cuadrilla(self):
        with self.assertRaises(e.TransicionInvalida):
            servicioProgramado().registrarInicio(SUPERVISOR)

    def test_no_se_puede_cerrar_sin_haber_terminado(self):
        with self.assertRaises(e.TransicionInvalida):
            servicioEnEjecucion().cerrarParaFacturacion(ADMIN)

    def test_no_se_puede_confirmar_dos_veces(self):
        with self.assertRaises(e.TransicionInvalida):
            servicioConCuadrilla().confirmarCuadrilla("cuad-2", True, COORDINADOR)

    def test_un_servicio_cerrado_no_admite_mas_transiciones(self):
        s = servicioTerminado()
        s.cerrarParaFacturacion(ADMIN)
        with self.assertRaises(e.TransicionInvalida):
            s.cerrarParaFacturacion(ADMIN)
        self.assertEqual(s.accionesDisponibles, ())

    def test_acciones_disponibles_segun_el_estado(self):
        self.assertEqual(set(servicioProgramado().accionesDisponibles),
                         {D.CONFIRMAR_CUADRILLA, D.CANCELAR})
        self.assertEqual(set(servicioEnEjecucion().accionesDisponibles),
                         {D.TERMINAR, D.DECLARAR_SIN_REEMPLAZO, D.NEGAR_ACCESO})

    def test_un_estado_invalido_no_cambia_el_servicio(self):
        s = servicioProgramado()
        with self.assertRaises(e.TransicionInvalida):
            s.registrarInicio(SUPERVISOR)
        self.assertEqual(s.estado, E.PROGRAMADO)
        self.assertIsNone(s.tiempo.inicio)


if __name__ == "__main__":
    unittest.main()