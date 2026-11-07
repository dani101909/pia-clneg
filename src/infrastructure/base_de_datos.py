"""Conexion y esquema de la base de datos (SQLite para desarrollo, PostgreSQL en produccion).

La URL llega por la variable de entorno DATABASE_URL (12-Factor):
    sqlite:///cleanpro.db            archivo local
    sqlite:///:memory:               en memoria (pruebas; cada conexion es una BD nueva)
    postgresql://usuario:clave@host:5432/cleanpro

El SQL de los repositorios se escribe una sola vez con marcadores `?`; para
PostgreSQL se convierten a `%s` en `Conexion.ejecutar`. El esquema usa solo tipos
portables (TEXT / INTEGER): fechas en ISO 8601, decimales como texto.
"""
import os
import sqlite3

URL_POR_DEFECTO = "sqlite:///cleanpro.db"

ESQUEMA = (
    """CREATE TABLE IF NOT EXISTS cotizaciones (
        folio TEXT PRIMARY KEY,
        cliente_id TEXT NOT NULL,
        ubicacion TEXT NOT NULL,
        superficie TEXT NOT NULL,
        tipo_de_inmueble TEXT NOT NULL,
        frecuencia TEXT NOT NULL,
        extras TEXT NOT NULL,
        duracion_segundos INTEGER NOT NULL,
        personal INTEGER NOT NULL,
        precio TEXT NOT NULL,
        estado TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS servicios (
        folio TEXT PRIMARY KEY,
        fecha_hora TEXT,
        dia TEXT,
        estado TEXT NOT NULL,
        cuadrilla_id TEXT,
        inicio TEXT,
        termino TEXT)""",
    "CREATE INDEX IF NOT EXISTS idx_servicios_dia ON servicios (dia)",
    """CREATE TABLE IF NOT EXISTS incidencias (
        servicio_folio TEXT NOT NULL REFERENCES servicios (folio),
        orden INTEGER NOT NULL,
        id TEXT NOT NULL,
        tipo TEXT NOT NULL,
        descripcion TEXT NOT NULL,
        hora TEXT NOT NULL,
        reportada_por TEXT NOT NULL,
        empleado_id TEXT,
        estado TEXT NOT NULL,
        PRIMARY KEY (servicio_folio, orden))""",
    """CREATE TABLE IF NOT EXISTS extras_servicio (
        servicio_folio TEXT NOT NULL REFERENCES servicios (folio),
        orden INTEGER NOT NULL,
        id TEXT NOT NULL,
        descripcion TEXT NOT NULL,
        solicitado_por TEXT NOT NULL,
        estado TEXT NOT NULL,
        PRIMARY KEY (servicio_folio, orden))""",
    """CREATE TABLE IF NOT EXISTS asignaciones (
        servicio_folio TEXT NOT NULL REFERENCES servicios (folio),
        orden INTEGER NOT NULL,
        empleado_original TEXT NOT NULL,
        sustituto TEXT,
        realizada_por TEXT NOT NULL,
        cuando TEXT NOT NULL,
        motivo TEXT NOT NULL,
        PRIMARY KEY (servicio_folio, orden))""",
    """CREATE TABLE IF NOT EXISTS historial_servicio (
        servicio_folio TEXT NOT NULL REFERENCES servicios (folio),
        orden INTEGER NOT NULL,
        quien TEXT NOT NULL,
        cuando TEXT NOT NULL,
        que TEXT NOT NULL,
        motivo TEXT NOT NULL,
        PRIMARY KEY (servicio_folio, orden))""",
    """CREATE TABLE IF NOT EXISTS empleados (
        id TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        disponible_para_cubrir INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS usuarios (
        nombre_de_usuario TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        rol TEXT NOT NULL,
        actor_id TEXT NOT NULL,
        clave_hash TEXT NOT NULL,
        activo INTEGER NOT NULL)""",
    "CREATE TABLE IF NOT EXISTS cuadrillas (id TEXT PRIMARY KEY)",
    """CREATE TABLE IF NOT EXISTS cuadrilla_integrantes (
        cuadrilla_id TEXT NOT NULL REFERENCES cuadrillas (id),
        orden INTEGER NOT NULL,
        empleado_id TEXT NOT NULL,
        PRIMARY KEY (cuadrilla_id, orden))""",
    """CREATE TABLE IF NOT EXISTS politicas (
        id INTEGER PRIMARY KEY,
        version INTEGER NOT NULL,
        tiempo_de_cortesia TEXT,
        criterio_precio_significativo TEXT,
        politica_cobro_acceso_negado TEXT,
        penalizacion_reprogramacion_tardia TEXT)""",
    "CREATE TABLE IF NOT EXISTS politicas_catalogo (descripcion TEXT PRIMARY KEY)",
    """CREATE TABLE IF NOT EXISTS politicas_historial (
        orden INTEGER PRIMARY KEY,
        actor TEXT NOT NULL,
        cuando TEXT NOT NULL,
        campo TEXT NOT NULL,
        motivo TEXT NOT NULL)""",
)


class Conexion:
    """Una conexion (= una transaccion a la vez) con el dialecto ya resuelto."""

    def __init__(self, cruda, dialecto):
        self._cruda = cruda
        self.dialecto = dialecto

    def ejecutar(self, sql, parametros=()):
        if self.dialecto == "postgresql":
            sql = sql.replace("?", "%s")
        return self._cruda.execute(sql, tuple(parametros))

    def crearEsquema(self):
        for sentencia in ESQUEMA:
            self.ejecutar(sentencia)
        self.commit()

    def commit(self):
        self._cruda.commit()

    def rollback(self):
        self._cruda.rollback()

    def cerrar(self):
        self._cruda.close()


class BaseDeDatos:
    """Fabrica de conexiones a partir de una URL."""

    def __init__(self, url=None):
        self.url = url or os.environ.get("DATABASE_URL", URL_POR_DEFECTO)
        if self.url.startswith("sqlite"):
            self.dialecto = "sqlite"
        elif self.url.startswith(("postgresql", "postgres")):
            self.dialecto = "postgresql"
        else:
            raise ValueError(f"DATABASE_URL no soportada: {self.url}")

    def abrir(self) -> Conexion:
        if self.dialecto == "sqlite":
            ruta = self.url.split(":///", 1)[1]
            # Una conexion por peticion; FastAPI puede abrirla y usarla en hilos distintos.
            cruda = sqlite3.connect(ruta, check_same_thread=False)
            cruda.execute("PRAGMA foreign_keys = ON")
            return Conexion(cruda, "sqlite")
        try:
            import psycopg
        except ImportError as error:
            raise RuntimeError(
                'Para usar PostgreSQL instala el driver: pip install "psycopg[binary]"'
            ) from error
        return Conexion(psycopg.connect(self.url), "postgresql")