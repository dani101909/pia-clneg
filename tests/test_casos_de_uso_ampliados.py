"""Casos de uso agregados para la API: emitir cotizacion, inicio, termino, incidencias.

Se ejecutan sobre SQL (SQLite en memoria) con la misma raiz de composicion de produccion.
"""
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from src.application.comandos import (AceptarCotizacion, ConfirmarCuadrilla,
                                      DocumentarIncidencia, EmitirCotizacion,
                                      RegistrarInicio, RegistrarTermino)
from src.domain.estado_servicio import EstadoDeServicio
from src.domain.servicio import TipoDeIncidencia
from src.domain.valores import FechaDeServicio, Folio
from src.infrastructure.base_de_datos import BaseDeDatos
from src.infrastructure.composicion_sql import construirAplicacionSql
from src.infrastructure.datos_demo import cargar
from src.infrastructure.sql_repositorios import ServicioRepositorySql

FOLIO = Folio("COT-0001")
FECHA = FechaDeServicio(datetime(2026, 11, 20, 8, 0))


def emitir(folio="COT-NUEVA", **cambios):
    datos = dict(folio=Folio(folio), cliente_id="cli-9", ubicacion="Monterrey",
                 superficie=Decimal("60"), tipo_de_inmueble="Casa", frecuencia="Unica",
                 extras=(), duracion=timedelta(hours=2), personal=2, precio=Decimal("800"))
    datos.update(cambios)
    return EmitirCotizacion(**datos)


class AppSqlConDemo(unittest.TestCase):
    def abrirConexion(self):
        """Gancho: test_postgres.py lo redefine para correr lo mismo sobre PostgreSQL."""
        conexion = BaseDeDatos("sqlite:///:memory:").abrir()
        conexion.crearEsquema()
        return conexion

    def setUp(self):
        self.conexion = self.abrirConexion()
        cargar(self.conexion)
        self.app = construirAplicacionSql(self.conexion)

    def tearDown(self):
        self.conexion.cerrar()

    def estadoDelServicio(self):
        return ServicioRepositorySql(self.conexion).obtenerPorFolio(FOLIO).estado

    def enEjecucion(self):
        self.app.cotizaciones.aceptarCotizacion(AceptarCotizacion(FOLIO, "cli-1", FECHA))
        self.app.programacion.confirmarCuadrilla(
            ConfirmarCuadrilla(FOLIO, "cuad-1", "coord-1"))
        return self.app.ejecucion.registrarInicio(RegistrarInicio(FOLIO, "sup-1"))


class EmitirCotizacionTest(AppSqlConDemo):
    def test_emite_una_cotizacion_vigente_y_se_puede_aceptar(self):
        r = self.app.cotizaciones.emitirCotizacion(emitir())
        self.assertTrue(r.exito)
        self.assertEqual(r.valor, "Vigente")
        self.assertEqual(type(r.eventos[0]).__name__, "CotizacionEmitida")
        self.assertTrue(self.app.cotizaciones.aceptarCotizacion(
            AceptarCotizacion(Folio("COT-NUEVA"), "cli-9", FECHA)).exito)

    def test_excepcion_folio_repetido_no_sobrescribe(self):
        r = self.app.cotizaciones.emitirCotizacion(emitir("COT-0001", ubicacion="Otra"))
        self.assertEqual(r.codigo, "FOLIO_DUPLICADO")
        original = self.app.cotizaciones.aceptarCotizacion(
            AceptarCotizacion(FOLIO, "cli-1", FECHA))
        self.assertTrue(original.exito)           # la original sigue Vigente e intacta

    def test_excepcion_datos_invalidos(self):
        self.assertEqual(self.app.cotizaciones.emitirCotizacion(
            emitir(superficie=Decimal("0"))).codigo, "DATOS_INCOMPLETOS")
        self.assertEqual(self.app.cotizaciones.emitirCotizacion(
            emitir(personal=0)).codigo, "VALOR_INVALIDO")


class InicioTerminoIncidenciaTest(AppSqlConDemo):
    def test_flujo_normal_inicio_y_termino(self):
        self.assertEqual(self.enEjecucion().valor, "EnEjecucion")
        r = self.app.ejecucion.registrarTermino(RegistrarTermino(FOLIO, "sup-1"))
        self.assertEqual(r.valor, "Terminado")
        self.assertEqual(self.estadoDelServicio(), EstadoDeServicio.TERMINADO)

    def test_excepcion_inicio_sin_cuadrilla_confirmada(self):
        self.app.cotizaciones.aceptarCotizacion(AceptarCotizacion(FOLIO, "cli-1", FECHA))
        r = self.app.ejecucion.registrarInicio(RegistrarInicio(FOLIO, "sup-1"))
        self.assertEqual(r.codigo, "TRANSICION_INVALIDA")
        self.assertEqual(self.estadoDelServicio(), EstadoDeServicio.PROGRAMADO)

    def test_excepcion_termino_anterior_al_inicio(self):
        self.enEjecucion()
        antes = datetime.now() - timedelta(days=1)
        r = self.app.ejecucion.registrarTermino(RegistrarTermino(FOLIO, "sup-1", antes))
        self.assertEqual(r.codigo, "TERMINO_INVALIDO")
        self.assertEqual(self.estadoDelServicio(), EstadoDeServicio.EN_EJECUCION)

    def test_incidencia_documentada_bloquea_el_cierre_hasta_revisarla(self):
        from src.application.comandos import CerrarParaFacturacion, RevisarIncidencia
        self.enEjecucion()
        r = self.app.ejecucion.documentarIncidencia(DocumentarIncidencia(
            FOLIO, TipoDeIncidencia.MATERIAL_ESPECIAL, "Piso delicado", "sup-1"))
        self.assertEqual(r.valor, "INC-1")
        self.app.ejecucion.registrarTermino(RegistrarTermino(FOLIO, "sup-1"))
        self.assertEqual(self.app.cierre.cerrarParaFacturacion(
            CerrarParaFacturacion(FOLIO, "admin-1")).codigo, "CIERRE_BLOQUEADO")
        self.app.cierre.revisarIncidencia(RevisarIncidencia(FOLIO, "INC-1", "admin-1"))
        self.assertTrue(self.app.cierre.cerrarParaFacturacion(
            CerrarParaFacturacion(FOLIO, "admin-1")).exito)

    def test_excepcion_incidencia_sin_descripcion(self):
        self.enEjecucion()
        r = self.app.ejecucion.documentarIncidencia(DocumentarIncidencia(
            FOLIO, TipoDeIncidencia.DANIO_REPORTADO, "", "sup-1"))
        self.assertEqual(r.codigo, "DATOS_INCOMPLETOS")


class PanelOperativoTest(AppSqlConDemo):
    def test_resume_cotizaciones_servicios_y_pendientes(self):
        from src.infrastructure.sql_lectura import PanelReadRepositorySql
        panel = PanelReadRepositorySql(self.conexion)
        inicial = panel.resumen()
        self.assertEqual(len(inicial["cotizaciones"]), 3)
        self.assertEqual(inicial["servicios"], [])
        self.assertEqual([c["id"] for c in inicial["cuadrillas"]], ["cuad-1", "cuad-2"])
        self.assertEqual(inicial["cuadrillas"][0]["integrantes"], ["emp-1", "emp-2"])
        self.assertFalse(next(e for e in inicial["empleados"] if e["id"] == "emp-6")
                         ["disponible_para_cubrir"])
        self.enEjecucion()
        self.app.ejecucion.documentarIncidencia(DocumentarIncidencia(
            FOLIO, TipoDeIncidencia.DANIO_REPORTADO, "Vidrio roto", "sup-1"))
        servicio = panel.resumen()["servicios"][0]
        self.assertEqual((servicio["folio"], servicio["estado"], servicio["pendientes"]),
                         ("COT-0001", "EnEjecucion", 1))


if __name__ == "__main__":
    unittest.main()