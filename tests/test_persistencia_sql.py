"""Persistencia SQL: contrato de los Repository, ida y vuelta de los Aggregates e integracion."""
import os
import tempfile
import unittest
from datetime import date, datetime

from src.application.comandos import (AceptarCotizacion, CerrarParaFacturacion,
                                      ConfirmarCuadrilla, ConfirmarExtra,
                                      ReasignarPersonal, RegistrarExtra,
                                      ReportarAusencia, RevisarIncidencia)
from src.application.consultas import ConsultarDisponibilidad
from src.domain.configuracion import ConfiguracionDePoliticas
from src.domain.cotizacion import EstadoDeCotizacion
from src.domain.cuadrilla import Cuadrilla, Empleado
from src.domain.errores import NoEncontrado
from src.domain.estado_servicio import EstadoDeServicio
from src.domain.valores import Motivo
from src.infrastructure.base_de_datos import BaseDeDatos
from src.infrastructure.composicion_sql import construirAplicacionSql
from src.infrastructure.sql_repositorios import (ConfiguracionRepositorySql,
                                                 CotizacionRepositorySql,
                                                 CuadrillaRepositorySql,
                                                 EmpleadoRepositorySql,
                                                 ServicioRepositorySql, UnitOfWorkSql)

from .test_contrato_repositorios import (CotizacionRepositoryContrato,
                                         ServicioRepositoryContrato,
                                         UnitOfWorkContrato)
from .utiles import (ADMIN, FECHA, FOLIO, SUPERVISOR, cotizacionVigente,
                     servicioEnEjecucion)


def conexionNueva():
    conexion = BaseDeDatos("sqlite:///:memory:").abrir()
    conexion.crearEsquema()
    return conexion


# ---- el mismo contrato que ya cumplen los repositorios en memoria (LSP) ----
class ServicioRepositorySqlTest(ServicioRepositoryContrato, unittest.TestCase):
    def crearRepositorio(self):
        return ServicioRepositorySql(conexionNueva())


class CotizacionRepositorySqlTest(CotizacionRepositoryContrato, unittest.TestCase):
    def crearRepositorio(self):
        return CotizacionRepositorySql(conexionNueva())


class UnitOfWorkSqlTest(UnitOfWorkContrato, unittest.TestCase):
    def crearUnidad(self):
        conexion = conexionNueva()
        return UnitOfWorkSql(conexion), ServicioRepositorySql(conexion)


# ---- ida y vuelta de cada Aggregate ----
class IdaYVueltaTest(unittest.TestCase):
    def setUp(self):
        self.conexion = conexionNueva()

    def test_cotizacion_conserva_todos_sus_datos(self):
        repo = CotizacionRepositorySql(self.conexion)
        original = cotizacionVigente()
        original.aceptar()
        repo.guardar(original)
        leida = repo.obtenerPorFolio(FOLIO)
        for campo in ("folio", "cliente_id", "datos", "frecuencia", "extras",
                      "estimacion", "estado"):
            self.assertEqual(getattr(leida, campo), getattr(original, campo), campo)
        self.assertEqual(leida.estado, EstadoDeCotizacion.ACEPTADA)
        self.assertEqual(leida.extraerEventos(), [])          # leer no emite eventos

    def test_servicio_completo_conserva_hijos_y_orden(self):
        repo = ServicioRepositorySql(self.conexion)
        s = servicioEnEjecucion()
        s.reportarAusencia("emp-1", SUPERVISOR, momento=datetime(2026, 10, 20, 8, 30))
        s.reasignarPersonal("emp-1", "emp-3", ADMIN, momento=datetime(2026, 10, 20, 8, 40))
        s.registrarExtra("Lavado de alfombra", True, SUPERVISOR)
        s.registrarExtra("Limpieza de ventanas", False, SUPERVISOR)
        repo.guardar(s)
        leido = repo.obtenerPorFolio(FOLIO)
        self.assertEqual(leido.estado, s.estado)
        self.assertEqual(leido.fecha, s.fecha)
        self.assertEqual(leido.cuadrilla_id, s.cuadrilla_id)
        self.assertEqual(leido.tiempo, s.tiempo)
        self.assertEqual(leido.incidencias, s.incidencias)
        self.assertEqual(leido.extras, s.extras)
        self.assertEqual([e.id for e in leido.extras], ["EXT-1", "EXT-2"])
        self.assertEqual(leido.asignaciones, s.asignaciones)
        self.assertEqual(leido.historial, s.historial)

    def test_guardar_de_nuevo_actualiza_sin_duplicar_hijos(self):
        repo = ServicioRepositorySql(self.conexion)
        s = servicioEnEjecucion()
        s.reportarAusencia("emp-1", SUPERVISOR)
        repo.guardar(s)
        leido = repo.obtenerPorFolio(FOLIO)
        leido.revisarIncidencia("INC-1", ADMIN)
        repo.guardar(leido)
        final = repo.obtenerPorFolio(FOLIO)
        self.assertEqual(len(final.incidencias), 1)
        self.assertEqual(final.incidencias[0].estado.value, "Revisada")

    def test_servicio_sin_fecha_ni_tiempos(self):
        from src.domain.servicio import Servicio
        cot = cotizacionVigente()
        cot.aceptar()
        repo = ServicioRepositorySql(self.conexion)
        repo.guardar(Servicio.programarDesde(cot, None))
        leido = repo.obtenerPorFolio(FOLIO)
        self.assertIsNone(leido.fecha)
        self.assertIsNone(leido.tiempo.inicio)

    def test_cuadrilla_y_empleado(self):
        CuadrillaRepositorySql(self.conexion).agregar(Cuadrilla("cuad-1", ("emp-2", "emp-1")))
        EmpleadoRepositorySql(self.conexion).agregar(Empleado("emp-1", "Ana", False))
        self.assertEqual(CuadrillaRepositorySql(self.conexion).obtenerPorId("cuad-1"),
                         Cuadrilla("cuad-1", ("emp-2", "emp-1")))
        self.assertEqual(EmpleadoRepositorySql(self.conexion).obtenerPorId("emp-1"),
                         Empleado("emp-1", "Ana", False))
        with self.assertRaises(NoEncontrado):
            CuadrillaRepositorySql(self.conexion).obtenerPorId("nada")
        with self.assertRaises(NoEncontrado):
            EmpleadoRepositorySql(self.conexion).obtenerPorId("nada")

    def test_politicas_con_catalogo_e_historial(self):
        repo = ConfiguracionRepositorySql(self.conexion)
        self.assertEqual(repo.obtenerPoliticasVigentes(), ConfiguracionDePoliticas())
        politicas = ConfiguracionDePoliticas()
        politicas.actualizarCatalogoDeExtras({"Ventanas", "Cochera"}, ADMIN,
                                             Motivo("Catalogo inicial"),
                                             datetime(2026, 10, 1, 9, 0))
        repo.guardar(politicas)
        leidas = repo.obtenerPoliticasVigentes()
        self.assertEqual(leidas, politicas)
        self.assertEqual(leidas.version, 2)


# ---- integracion: casos de uso reales sobre SQL ----
def aplicacionSql():
    conexion = conexionNueva()
    app = construirAplicacionSql(conexion)
    cuadrillas, empleados = CuadrillaRepositorySql(conexion), EmpleadoRepositorySql(conexion)
    cuadrillas.agregar(Cuadrilla("cuad-1", ("emp-1", "emp-2")))
    cuadrillas.agregar(Cuadrilla("cuad-2", ("emp-3",)))
    for e in (Empleado("emp-1", "Ana"), Empleado("emp-2", "Luis"), Empleado("emp-3", "Rosa"),
              Empleado("emp-ocupado", "Mario", False)):
        empleados.agregar(e)
    politicas = ConfiguracionDePoliticas()
    politicas.actualizarCatalogoDeExtras({"Limpieza de ventanas"}, ADMIN, Motivo("Prueba"))
    ConfiguracionRepositorySql(conexion).guardar(politicas)
    CotizacionRepositorySql(conexion).guardar(cotizacionVigente())
    conexion.commit()
    return app, conexion


class CasosDeUsoSobreSqlTest(unittest.TestCase):
    def setUp(self):
        self.app, self.conexion = aplicacionSql()
        self.servicios = ServicioRepositorySql(self.conexion)

    def _aceptar_y_confirmar(self):
        r = self.app.cotizaciones.aceptarCotizacion(AceptarCotizacion(FOLIO, "cli-1", FECHA))
        self.assertTrue(r.exito, r)
        r = self.app.programacion.confirmarCuadrilla(
            ConfirmarCuadrilla(FOLIO, "cuad-1", "coord-1"))
        self.assertTrue(r.exito, r)

    def _poner_en_ejecucion(self):
        s = self.servicios.obtenerPorFolio(FOLIO)
        s.registrarInicio(SUPERVISOR, datetime(2026, 10, 20, 8, 5))
        self.servicios.guardar(s)
        self.conexion.commit()

    def _terminar(self):
        s = self.servicios.obtenerPorFolio(FOLIO)
        s.registrarTermino(SUPERVISOR, datetime(2026, 10, 20, 12, 0))
        self.servicios.guardar(s)
        self.conexion.commit()

    def test_cu01_acepta_y_programa_y_persiste(self):
        self.app.cotizaciones.aceptarCotizacion(AceptarCotizacion(FOLIO, "cli-1", FECHA))
        self.assertEqual(CotizacionRepositorySql(self.conexion).obtenerPorFolio(FOLIO).estado,
                         EstadoDeCotizacion.ACEPTADA)
        self.assertEqual(self.servicios.obtenerPorFolio(FOLIO).estado,
                         EstadoDeServicio.PROGRAMADO)

    def test_cu01_error_de_negocio_hace_rollback_completo(self):
        r = self.app.cotizaciones.aceptarCotizacion(AceptarCotizacion(FOLIO, "otro", FECHA))
        self.assertEqual(r.codigo, "SIN_PERMISO")
        self.assertEqual(CotizacionRepositorySql(self.conexion).obtenerPorFolio(FOLIO).estado,
                         EstadoDeCotizacion.VIGENTE)
        with self.assertRaises(NoEncontrado):
            self.servicios.obtenerPorFolio(FOLIO)

    def test_cu02_cuadrilla_ocupada_y_disponibilidad(self):
        self._aceptar_y_confirmar()
        filas = self.app.consultas.consultarDisponibilidad(
            ConsultarDisponibilidad(date(2026, 10, 20)))
        self.assertEqual({f.cuadrilla_id: f.libre for f in filas},
                         {"cuad-1": False, "cuad-2": True})
        from src.domain.servicio import Servicio
        from src.domain.valores import Folio
        otro = Folio("COT-0002")
        cot = cotizacionVigente(otro)
        cot.aceptar()
        self.servicios.guardar(Servicio.programarDesde(cot, FECHA))
        self.conexion.commit()
        r = self.app.programacion.confirmarCuadrilla(ConfirmarCuadrilla(otro, "cuad-1", "coord-1"))
        self.assertEqual(r.codigo, "CUADRILLA_NO_DISPONIBLE")
        self.assertTrue(self.app.programacion.confirmarCuadrilla(
            ConfirmarCuadrilla(otro, "cuad-2", "coord-1")).exito)

    def test_cu03_ausencia_y_reasignacion(self):
        self._aceptar_y_confirmar()
        self._poner_en_ejecucion()
        self.assertTrue(self.app.personal.reportarAusencia(
            ReportarAusencia(FOLIO, "emp-1", "sup-1")).exito)
        r = self.app.personal.reasignarPersonal(
            ReasignarPersonal(FOLIO, "emp-1", "emp-ocupado", "admin-1"))
        self.assertEqual(r.codigo, "SUSTITUTO_NO_DISPONIBLE")
        self.assertEqual(self.servicios.obtenerPorFolio(FOLIO).asignaciones, [])
        self.assertTrue(self.app.personal.reasignarPersonal(
            ReasignarPersonal(FOLIO, "emp-1", "emp-3", "admin-1")).exito)
        a = self.servicios.obtenerPorFolio(FOLIO).asignaciones[0]
        self.assertEqual((a.empleado_original, a.sustituto), ("emp-1", "emp-3"))

    def test_cu04_y_cu05_extra_pendiente_bloquea_el_cierre_hasta_confirmarse(self):
        self._aceptar_y_confirmar()
        self._poner_en_ejecucion()
        r = self.app.ejecucion.registrarExtra(
            RegistrarExtra(FOLIO, "Lavado de alfombra", "sup-1"))
        self.assertEqual(r.valor, "Pendiente de confirmacion")
        self._terminar()
        r = self.app.cierre.cerrarParaFacturacion(CerrarParaFacturacion(FOLIO, "admin-1"))
        self.assertEqual(r.codigo, "CIERRE_BLOQUEADO")
        self.assertIn("EXT-1", r.detalle[0])
        self.assertEqual(self.servicios.obtenerPorFolio(FOLIO).estado,
                         EstadoDeServicio.TERMINADO)
        self.assertTrue(self.app.ejecucion.confirmarExtra(
            ConfirmarExtra(FOLIO, "EXT-1", "coord-1")).exito)
        r = self.app.cierre.cerrarParaFacturacion(CerrarParaFacturacion(FOLIO, "admin-1"))
        self.assertTrue(r.exito, r)
        self.assertEqual(self.servicios.obtenerPorFolio(FOLIO).estado,
                         EstadoDeServicio.CERRADO_PARA_FACTURACION)
        self.assertEqual(type(self.app.facturacion.publicados[0]).__name__,
                         "ServicioCerradoParaFacturacion")

    def test_cu05_incidencia_pendiente_se_revisa_y_luego_cierra(self):
        self._aceptar_y_confirmar()
        self._poner_en_ejecucion()
        self.app.personal.reportarAusencia(ReportarAusencia(FOLIO, "emp-1", "sup-1"))
        self._terminar()
        r = self.app.cierre.cerrarParaFacturacion(CerrarParaFacturacion(FOLIO, "admin-1"))
        self.assertIn("INC-1", r.detalle[0])
        self.app.cierre.revisarIncidencia(RevisarIncidencia(FOLIO, "INC-1", "admin-1"))
        self.assertTrue(self.app.cierre.cerrarParaFacturacion(
            CerrarParaFacturacion(FOLIO, "admin-1")).exito)


class PersistenciaEntreConexionesTest(unittest.TestCase):
    def test_lo_confirmado_sobrevive_y_lo_no_confirmado_no(self):
        with tempfile.TemporaryDirectory() as carpeta:
            base = BaseDeDatos("sqlite:///" + os.path.join(carpeta, "prueba.db"))
            a = base.abrir()
            a.crearEsquema()
            ServicioRepositorySql(a).guardar(servicioEnEjecucion())
            a.commit()
            a.cerrar()
            b = base.abrir()
            self.assertEqual(ServicioRepositorySql(b).obtenerPorFolio(FOLIO).estado,
                             EstadoDeServicio.EN_EJECUCION)
            b.cerrar()

    def test_url_no_soportada(self):
        with self.assertRaises(ValueError):
            BaseDeDatos("mysql://x")


if __name__ == "__main__":
    unittest.main()