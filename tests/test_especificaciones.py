"""Specification: combinadores Y/O/No y las reglas concretas de CleanPro."""
import unittest
from datetime import datetime
from itertools import product

from src.domain.configuracion import ConfiguracionDePoliticas
from src.domain.cuadrilla import Cuadrilla, Empleado
from src.domain.especificaciones import (CuadrillaLibreEnFecha,
                                         EmpleadoDisponibleParaCubrir,
                                         ExtraRequiereConfirmacion,
                                         servicioCancelable,
                                         servicioCerrableParaFacturacion)
from src.domain.servicio import TipoDeIncidencia
from src.domain.specification import Especificacion

from .utiles import (ADMIN, SUPERVISOR, servicioConCuadrilla, servicioEnEjecucion,
                     servicioProgramado, servicioTerminado)


class Fija(Especificacion):
    """Regla de prueba: siempre da el valor indicado."""

    def __init__(self, valor, texto):
        self._valor = valor
        self.descripcion = texto

    def esSatisfechaPor(self, candidato):
        return self._valor


class CombinadoresTest(unittest.TestCase):
    def test_tabla_de_verdad_y_o_no(self):
        for a, b in product([True, False], repeat=2):
            with self.subTest(a=a, b=b):
                sa, sb = Fija(a, "A"), Fija(b, "B")
                self.assertEqual((sa & sb).esSatisfechaPor(None), a and b)
                self.assertEqual((sa | sb).esSatisfechaPor(None), a or b)
                self.assertEqual((~sa).esSatisfechaPor(None), not a)
                self.assertEqual(sa.y(sb).esSatisfechaPor(None), a and b)
                self.assertEqual(sa.o(sb).esSatisfechaPor(None), a or b)
                self.assertEqual(sa.no().esSatisfechaPor(None), not a)

    def test_se_pueden_anidar(self):
        regla = (Fija(True, "A") & Fija(False, "B")) | ~Fija(False, "C")
        self.assertTrue(regla.esSatisfechaPor(None))

    def test_razones_de_incumplimiento(self):
        self.assertEqual((Fija(True, "A") & Fija(True, "B"))
                         .razonesDeIncumplimiento(None), [])
        self.assertEqual((Fija(False, "A") & Fija(False, "B"))
                         .razonesDeIncumplimiento(None), ["A", "B"])
        self.assertEqual((Fija(False, "A") | Fija(False, "B"))
                         .razonesDeIncumplimiento(None), ["A", "B"])
        self.assertEqual((Fija(False, "A") | Fija(True, "B"))
                         .razonesDeIncumplimiento(None), [])
        self.assertEqual((~Fija(True, "A")).razonesDeIncumplimiento(None),
                         ["No debe cumplirse: A"])

    def test_descripcion_de_una_regla_compuesta(self):
        self.assertEqual((Fija(True, "A") & ~Fija(True, "B")).descripcion,
                         "(A Y NO (B))")


class ReglasDeCleanProTest(unittest.TestCase):
    def test_cuadrilla_libre_en_fecha(self):
        ocupada = servicioConCuadrilla()                     # usa cuad-1
        regla = CuadrillaLibreEnFecha([ocupada])
        self.assertFalse(regla.esSatisfechaPor(Cuadrilla("cuad-1")))
        self.assertTrue(regla.esSatisfechaPor(Cuadrilla("cuad-2")))
        self.assertTrue(CuadrillaLibreEnFecha([]).esSatisfechaPor(Cuadrilla("cuad-1")))

    def test_extra_requiere_confirmacion_si_esta_fuera_del_catalogo(self):
        politicas = ConfiguracionDePoliticas(catalogo_de_extras=frozenset({"Ventanas"}))
        regla = ExtraRequiereConfirmacion(politicas)
        self.assertFalse(regla.esSatisfechaPor("Ventanas"))
        self.assertTrue(regla.esSatisfechaPor("Lavar alfombra"))
        self.assertTrue(ExtraRequiereConfirmacion(ConfiguracionDePoliticas())
                        .esSatisfechaPor("Ventanas"))          # catalogo vacio

    def test_empleado_disponible_para_cubrir(self):
        regla = EmpleadoDisponibleParaCubrir()
        self.assertTrue(regla.esSatisfechaPor(Empleado("e1", "Ana")))
        self.assertFalse(regla.esSatisfechaPor(Empleado("e2", "Mario", False)))

    def test_cerrable_requiere_termino_y_sin_pendientes(self):
        regla = servicioCerrableParaFacturacion()
        self.assertTrue(regla.esSatisfechaPor(servicioTerminado()))
        en_curso = servicioEnEjecucion()
        self.assertFalse(regla.esSatisfechaPor(en_curso))
        self.assertIn("no admite", regla.razonesDeIncumplimiento(en_curso)[0])

    def test_cerrable_dice_que_incidencia_falta(self):
        s = servicioTerminado()
        s.documentarIncidencia(TipoDeIncidencia.DANIO_REPORTADO, "Vidrio roto",
                               SUPERVISOR, momento=datetime(2026, 10, 20, 12, 5))
        regla = servicioCerrableParaFacturacion()
        self.assertFalse(regla.esSatisfechaPor(s))
        self.assertIn("INC-1", regla.razonesDeIncumplimiento(s)[0])
        s.revisarIncidencia("INC-1", ADMIN)
        self.assertTrue(regla.esSatisfechaPor(s))

    def test_cancelable_solo_si_no_ha_iniciado(self):
        regla = servicioCancelable()
        self.assertTrue(regla.esSatisfechaPor(servicioProgramado()))
        self.assertTrue(regla.esSatisfechaPor(servicioConCuadrilla()))
        self.assertFalse(regla.esSatisfechaPor(servicioEnEjecucion()))
        self.assertFalse(regla.esSatisfechaPor(servicioTerminado()))


if __name__ == "__main__":
    unittest.main()