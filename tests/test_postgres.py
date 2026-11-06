"""Verifica los repositorios SQL contra un PostgreSQL REAL.

Solo corre si existe TEST_DATABASE_URL (Docker Compose y GitHub Actions la definen):
    TEST_DATABASE_URL=postgresql://cleanpro:cleanpro@localhost:5432/cleanpro_test
Reutiliza los casos de uso de tests/test_casos_de_uso_ampliados.py y el flujo
CU-01..CU-05 cambiando unicamente la conexion (los repositorios no cambian: LSP).
"""
import os
import unittest

from src.infrastructure.base_de_datos import BaseDeDatos
from tests import test_casos_de_uso_ampliados as base

URL = os.environ.get("TEST_DATABASE_URL")
requiere_postgres = unittest.skipUnless(URL, "define TEST_DATABASE_URL para probar PostgreSQL")


class _SobrePostgres:
    """Cada prueba parte de un esquema vacio y lo vuelve a crear."""

    def abrirConexion(self):
        conexion = BaseDeDatos(URL).abrir()
        conexion.ejecutar("DROP SCHEMA public CASCADE")
        conexion.ejecutar("CREATE SCHEMA public")
        conexion.commit()
        conexion.crearEsquema()
        return conexion


@requiere_postgres
class EmitirCotizacionPostgres(_SobrePostgres, base.EmitirCotizacionTest):
    pass


@requiere_postgres
class InicioTerminoIncidenciaPostgres(_SobrePostgres, base.InicioTerminoIncidenciaTest):
    pass


@requiere_postgres
class FlujoCompletoPostgres(_SobrePostgres, base.AppSqlConDemo):
    def test_aceptar_confirmar_y_disponibilidad(self):
        from datetime import date
        from src.application.consultas import ConsultarDisponibilidad
        self.enEjecucion()
        filas = self.app.consultas.consultarDisponibilidad(
            ConsultarDisponibilidad(date(2026, 11, 20)))
        self.assertEqual({f.cuadrilla_id: f.libre for f in filas},
                         {"cuad-1": False, "cuad-2": True})

    def test_error_de_negocio_hace_rollback(self):
        r = self.app.cotizaciones.aceptarCotizacion(
            base.AceptarCotizacion(base.FOLIO, "otro-cliente", base.FECHA))
        self.assertEqual(r.codigo, "SIN_PERMISO")
        self.assertEqual(self.conexion.ejecutar(
            "SELECT COUNT(*) FROM servicios").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
