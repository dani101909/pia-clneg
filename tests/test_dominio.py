import unittest
from datetime import datetime
from decimal import Decimal

from src.domain import errores as e
from src.domain.cotizacion import Cotizacion, EstadoDeCotizacion
from src.domain.servicio import (EstadoDeExtra, EstadoDeIncidencia,
                                       EstadoDeServicio, Servicio, TipoDeIncidencia)
from src.domain.valores import (Actor, DatosDelInmueble, Folio, Rol,
                                      RegistroDeTiempo)

from .utiles import (ADMIN, COORDINADOR, FOLIO, SUPERVISOR, cotizacionVigente,
                     servicioConCuadrilla, servicioEnEjecucion, servicioProgramado,
                     servicioTerminado)


class CotizacionTest(unittest.TestCase):
    def test_C1_no_se_emite_sin_los_cinco_datos(self):
        with self.assertRaises(e.DatosIncompletos):
            Cotizacion.emitir(FOLIO, "cli-1", None, None, None, None)
        with self.assertRaises(e.DatosIncompletos):
            DatosDelInmueble("", Decimal("100"), "Casa")

    def test_C2_nace_vigente_con_folio(self):
        cot = cotizacionVigente()
        self.assertEqual(cot.estado, EstadoDeCotizacion.VIGENTE)
        self.assertEqual(cot.folio, FOLIO)

    def test_C4_solo_una_vigente_se_acepta(self):
        cot = cotizacionVigente()
        cot.aceptar()
        with self.assertRaises(e.CotizacionNoVigente):
            cot.aceptar()
        with self.assertRaises(e.CotizacionNoVigente):
            cot.rechazar()


class ServicioTest(unittest.TestCase):
    def test_S1_nace_programado_sin_cuadrilla_con_el_folio_de_la_cotizacion(self):
        s = servicioProgramado()
        self.assertEqual(s.estado, EstadoDeServicio.PROGRAMADO)
        self.assertIsNone(s.cuadrilla_id)
        self.assertEqual(s.folio, FOLIO)

    def test_S1_no_nace_de_una_cotizacion_vigente(self):
        with self.assertRaises(e.TransicionInvalida):
            Servicio.programarDesde(cotizacionVigente())

    def test_S2_cuadrilla_solo_se_confirma_si_hay_disponibilidad(self):
        s = servicioProgramado()
        with self.assertRaises(e.CuadrillaNoDisponible):
            s.confirmarCuadrilla("cuad-1", False, COORDINADOR)
        self.assertIsNone(s.cuadrilla_id)
        s.confirmarCuadrilla("cuad-1", True, COORDINADOR)
        self.assertEqual(s.estado, EstadoDeServicio.CUADRILLA_CONFIRMADA)

    def test_S2_solo_el_coordinador_confirma(self):
        with self.assertRaises(e.SinPermiso):
            servicioProgramado().confirmarCuadrilla("cuad-1", True, SUPERVISOR)

    def test_S3_el_termino_no_puede_ir_sin_inicio_ni_antes_del_inicio(self):
        with self.assertRaises(e.TerminoInvalido):
            servicioConCuadrilla().registrarTermino(SUPERVISOR)
        s = servicioEnEjecucion()
        with self.assertRaises(e.TerminoInvalido):
            s.registrarTermino(SUPERVISOR, datetime(2026, 10, 20, 7, 0))
        with self.assertRaises(e.TerminoInvalido):
            RegistroDeTiempo().conTermino(datetime.now())

    def test_S4_ausencia_crea_incidencia_pendiente_y_evento(self):
        s = servicioEnEjecucion()
        s.extraerEventos()
        inc = s.reportarAusencia("emp-1", SUPERVISOR)
        self.assertEqual(inc.tipo, TipoDeIncidencia.AUSENCIA)
        self.assertEqual(inc.estado, EstadoDeIncidencia.PENDIENTE_DE_REVISION)
        nombres = [type(ev).__name__ for ev in s.extraerEventos()]
        self.assertIn("AusenciaReportada", nombres)

    def test_S4_reasignacion_conserva_original_y_sustituto(self):
        s = servicioEnEjecucion()
        s.reportarAusencia("emp-1", SUPERVISOR)
        s.reasignarPersonal("emp-1", "emp-3", ADMIN)
        a = s.asignaciones[0]
        self.assertEqual((a.empleado_original, a.sustituto, a.realizada_por),
                         ("emp-1", "emp-3", ADMIN.id))
        self.assertEqual(s.historial[-1].quien, ADMIN.id)       # RNF-03

    def test_S4_no_se_reasigna_sin_ausencia_reportada(self):
        with self.assertRaises(e.TransicionInvalida):
            servicioEnEjecucion().reasignarPersonal("emp-1", "emp-3", ADMIN)

    def test_S4_sin_reemplazo_el_servicio_queda_en_riesgo(self):
        s = servicioEnEjecucion()
        s.reportarAusencia("emp-1", SUPERVISOR)
        s.declararSinReemplazo(ADMIN)
        self.assertEqual(s.estado, EstadoDeServicio.EN_RIESGO)

    def test_S6_extra_en_catalogo_se_acepta_y_fuera_queda_pendiente(self):
        s = servicioEnEjecucion()
        self.assertEqual(s.registrarExtra("A", False, SUPERVISOR).estado,
                         EstadoDeExtra.ACEPTADO)
        extra = s.registrarExtra("B", True, SUPERVISOR)
        self.assertEqual(extra.estado, EstadoDeExtra.PENDIENTE_DE_CONFIRMACION)
        s.confirmarExtra(extra.id, COORDINADOR)
        self.assertEqual(extra.estado, EstadoDeExtra.CONFIRMADO)

    def test_S12_cierre_bloqueado_indica_que_falta_documentar(self):
        s = servicioTerminado()
        s.documentarIncidencia(TipoDeIncidencia.DANIO_REPORTADO, "Vaso roto", SUPERVISOR)
        with self.assertRaises(e.CierreBloqueado) as ctx:
            s.cerrarParaFacturacion(ADMIN)
        self.assertIn("INC-1", ctx.exception.detalle[0])
        self.assertEqual(s.estado, EstadoDeServicio.TERMINADO)

    def test_S12_cierre_exitoso_sin_pendientes_y_emite_evento(self):
        s = servicioTerminado()
        s.extraerEventos()
        s.cerrarParaFacturacion(ADMIN)
        self.assertEqual(s.estado, EstadoDeServicio.CERRADO_PARA_FACTURACION)
        self.assertEqual(type(s.extraerEventos()[0]).__name__,
                         "ServicioCerradoParaFacturacion")

    def test_S12_solo_administracion_cierra_y_requiere_termino(self):
        with self.assertRaises(e.SinPermiso):
            servicioTerminado().cerrarParaFacturacion(COORDINADOR)
        with self.assertRaises(e.TransicionInvalida):
            servicioEnEjecucion().cerrarParaFacturacion(ADMIN)


if __name__ == "__main__":
    unittest.main()
