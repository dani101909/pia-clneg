"""CU-01 a CU-05 recorridos por la Service Layer, con infraestructura en memoria."""
import unittest
from datetime import date, datetime

from src.application.comandos import (AceptarCotizacion, CerrarParaFacturacion,
                                          ConfirmarCuadrilla, ConfirmarExtra,
                                          ReasignarPersonal, RegistrarExtra,
                                          ReportarAusencia, RevisarIncidencia)
from src.application.consultas import ConsultarDisponibilidad
from src.domain.cotizacion import EstadoDeCotizacion
from src.domain.servicio import EstadoDeServicio
from src.infrastructure.composicion import construirAplicacion

from .utiles import (ADMIN, FECHA, FOLIO, SUPERVISOR, poblar)


def aceptada():
    app = construirAplicacion()
    poblar(app)
    r = app.cotizaciones.aceptarCotizacion(AceptarCotizacion(FOLIO, "cli-1", FECHA))
    assert r.exito, r
    return app


def confirmada(app):
    r = app.programacion.confirmarCuadrilla(ConfirmarCuadrilla(FOLIO, "cuad-1", "coord-1"))
    assert r.exito, r


def enEjecucion(app):
    confirmada(app)
    s = app.bd.servicios[FOLIO]
    s.registrarInicio(SUPERVISOR, datetime(2026, 10, 20, 8, 5))
    s.extraerEventos()


class CU01AceptarCotizacion(unittest.TestCase):
    def test_flujo_normal_crea_programacion_tentativa_sin_cuadrilla(self):
        app = aceptada()
        self.assertEqual(app.bd.cotizaciones[FOLIO].estado, EstadoDeCotizacion.ACEPTADA)
        servicio = app.bd.servicios[FOLIO]
        self.assertEqual(servicio.estado, EstadoDeServicio.PROGRAMADO)
        self.assertIsNone(servicio.cuadrilla_id)

    def test_excepcion_no_se_acepta_dos_veces_ni_por_otro_cliente(self):
        app = aceptada()
        r = app.cotizaciones.aceptarCotizacion(AceptarCotizacion(FOLIO, "cli-1", FECHA))
        self.assertEqual(r.codigo, "COTIZACION_NO_VIGENTE")
        app2 = construirAplicacion()
        poblar(app2)
        r = app2.cotizaciones.aceptarCotizacion(AceptarCotizacion(FOLIO, "otro", FECHA))
        self.assertEqual(r.codigo, "SIN_PERMISO")
        self.assertEqual(app2.bd.cotizaciones[FOLIO].estado, EstadoDeCotizacion.VIGENTE)
        self.assertNotIn(FOLIO, app2.bd.servicios)         # rollback


class CU02ConfirmarCuadrilla(unittest.TestCase):
    def test_flujo_normal(self):
        app = aceptada()
        confirmada(app)
        self.assertEqual(app.bd.servicios[FOLIO].estado,
                         EstadoDeServicio.CUADRILLA_CONFIRMADA)

    def test_excepcion_cuadrilla_ocupada_ese_dia_no_se_confirma(self):
        app = aceptada()
        confirmada(app)
        # otro servicio, misma fecha, misma cuadrilla
        from .utiles import cotizacionVigente
        from src.domain.servicio import Servicio
        from src.domain.valores import Folio
        otro = Folio("COT-0002")
        cot = cotizacionVigente(otro)
        cot.aceptar()
        app.bd.servicios[otro] = Servicio.programarDesde(cot, FECHA)
        r = app.programacion.confirmarCuadrilla(ConfirmarCuadrilla(otro, "cuad-1", "coord-1"))
        self.assertFalse(r.exito)
        self.assertEqual(r.codigo, "CUADRILLA_NO_DISPONIBLE")
        self.assertIsNone(app.bd.servicios[otro].cuadrilla_id)
        ok = app.programacion.confirmarCuadrilla(ConfirmarCuadrilla(otro, "cuad-2", "coord-1"))
        self.assertTrue(ok.exito)


class CU03AusenciaYReasignacion(unittest.TestCase):
    def test_flujo_normal_reasigna_y_notifica_a_administracion(self):
        app = aceptada()
        enEjecucion(app)
        r = app.personal.reportarAusencia(ReportarAusencia(FOLIO, "emp-1", "sup-1"))
        self.assertTrue(r.exito)
        avisos = [type(ev).__name__ for ev in app.notificaciones.enviadas]
        self.assertIn("AusenciaReportada", avisos)           # RNF-01
        r = app.personal.reasignarPersonal(ReasignarPersonal(FOLIO, "emp-1", "emp-3", "admin-1"))
        self.assertTrue(r.exito)
        a = app.bd.servicios[FOLIO].asignaciones[0]
        self.assertEqual((a.empleado_original, a.sustituto), ("emp-1", "emp-3"))

    def test_excepcion_sin_reemplazo_deja_el_servicio_en_riesgo(self):
        app = aceptada()
        enEjecucion(app)
        app.personal.reportarAusencia(ReportarAusencia(FOLIO, "emp-1", "sup-1"))
        r = app.personal.reasignarPersonal(ReasignarPersonal(FOLIO, "emp-1", None, "admin-1"))
        self.assertTrue(r.exito)
        self.assertEqual(app.bd.servicios[FOLIO].estado, EstadoDeServicio.EN_RIESGO)
        self.assertEqual(type(app.notificaciones.enviadas[-1]).__name__, "ServicioEnRiesgo")

    def test_excepcion_sustituto_no_disponible_se_rechaza(self):
        app = aceptada()
        enEjecucion(app)
        app.personal.reportarAusencia(ReportarAusencia(FOLIO, "emp-1", "sup-1"))
        r = app.personal.reasignarPersonal(
            ReasignarPersonal(FOLIO, "emp-1", "emp-ocupado", "admin-1"))
        self.assertEqual(r.codigo, "SUSTITUTO_NO_DISPONIBLE")
        self.assertEqual(app.bd.servicios[FOLIO].asignaciones, [])


class CU04RegistrarExtra(unittest.TestCase):
    def test_extra_en_catalogo_se_acepta_directo(self):
        app = aceptada()
        enEjecucion(app)
        r = app.ejecucion.registrarExtra(RegistrarExtra(FOLIO, "Limpieza de ventanas", "sup-1"))
        self.assertEqual(r.valor, "Aceptado")

    def test_extra_fuera_de_catalogo_queda_pendiente_hasta_que_confirme_el_coordinador(self):
        app = aceptada()
        enEjecucion(app)
        r = app.ejecucion.registrarExtra(RegistrarExtra(FOLIO, "Lavado de alfombra", "sup-1"))
        self.assertEqual(r.valor, "Pendiente de confirmacion")
        r = app.ejecucion.confirmarExtra(ConfirmarExtra(FOLIO, "EXT-1", "coord-1"))
        self.assertTrue(r.exito)

    def test_excepcion_solo_el_supervisor_y_solo_en_ejecucion(self):
        app = aceptada()
        r = app.ejecucion.registrarExtra(RegistrarExtra(FOLIO, "Limpieza de ventanas", "sup-1"))
        self.assertEqual(r.codigo, "TRANSICION_INVALIDA")      # aun no esta en ejecucion


class CU05CierreParaFacturacion(unittest.TestCase):
    def _terminado_con_incidencia(self):
        app = aceptada()
        enEjecucion(app)
        app.personal.reportarAusencia(ReportarAusencia(FOLIO, "emp-1", "sup-1"))
        s = app.bd.servicios[FOLIO]
        s.registrarTermino(SUPERVISOR, datetime(2026, 10, 20, 12, 0))
        s.extraerEventos()          # preparacion del escenario, no es parte del caso de uso
        return app

    def test_excepcion_se_bloquea_y_dice_cual_incidencia_falta(self):
        app = self._terminado_con_incidencia()
        r = app.cierre.cerrarParaFacturacion(CerrarParaFacturacion(FOLIO, "admin-1"))
        self.assertFalse(r.exito)
        self.assertEqual(r.codigo, "CIERRE_BLOQUEADO")
        self.assertIn("INC-1", r.detalle[0])
        self.assertEqual(app.facturacion.publicados, [])
        self.assertEqual(app.bd.servicios[FOLIO].estado, EstadoDeServicio.TERMINADO)

    def test_flujo_normal_cierra_y_publica_el_evento_de_facturacion(self):
        app = self._terminado_con_incidencia()
        app.cierre.revisarIncidencia(RevisarIncidencia(FOLIO, "INC-1", "admin-1"))
        r = app.cierre.cerrarParaFacturacion(CerrarParaFacturacion(FOLIO, "admin-1"))
        self.assertTrue(r.exito)
        self.assertEqual(app.bd.servicios[FOLIO].estado,
                         EstadoDeServicio.CERRADO_PARA_FACTURACION)
        self.assertEqual(type(app.facturacion.publicados[0]).__name__,
                         "ServicioCerradoParaFacturacion")


class ConsultaDeDisponibilidad(unittest.TestCase):
    def test_muestra_por_cuadrilla_si_esta_libre_u_ocupada(self):
        app = aceptada()
        confirmada(app)
        filas = app.consultas.consultarDisponibilidad(ConsultarDisponibilidad(date(2026, 10, 20)))
        self.assertEqual({f.cuadrilla_id: f.libre for f in filas},
                         {"cuad-1": False, "cuad-2": True})


if __name__ == "__main__":
    unittest.main()
