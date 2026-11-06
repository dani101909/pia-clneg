"""Repository y Unit of Work sobre SQL (SQLite / PostgreSQL).

Cumplen las mismas interfaces que las versiones en memoria y pasan la misma
bateria de contrato (tests/test_persistencia_sql.py), asi que dominio y
aplicacion no cambian. Cada Aggregate se guarda en su tabla raiz mas sus tablas
hijas; al leer se reconstituye sin ejecutar reglas ni emitir eventos.
"""
import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from ..application.consultas import DisponibilidadDTO, DisponibilidadReadRepository
from ..application.unit_of_work import UnitOfWork
from ..domain.configuracion import ConfiguracionDePoliticas
from ..domain.cotizacion import Cotizacion, EstadoDeCotizacion
from ..domain.cuadrilla import Cuadrilla, Empleado
from ..domain.errores import NoEncontrado
from ..domain.estado_servicio import EstadoDeServicio
from ..domain.repositorios import (ConfiguracionRepository, CotizacionRepository,
                                   CuadrillaRepository, EmpleadoRepository,
                                   ServicioRepository)
from ..domain.servicio import (CambioRegistrado, EstadoDeExtra, EstadoDeIncidencia,
                               Extra, Incidencia, Servicio, TipoDeIncidencia)
from ..domain.valores import (AsignacionDePersonal, DatosDelInmueble, Dinero,
                              Estimacion, FechaDeServicio, Folio, Frecuencia, Motivo,
                              RegistroDeTiempo)

_FINALIZADOS_SIN_CUADRILLA = (EstadoDeServicio.CANCELADO.value,
                              EstadoDeServicio.NO_REALIZADO.value)


def _clave(folio):
    return getattr(folio, "valor", folio)


def _iso(momento):
    return momento.isoformat() if momento is not None else None


def _fecha_hora(texto):
    return datetime.fromisoformat(texto) if texto is not None else None


class UnitOfWorkSql(UnitOfWork):
    def __init__(self, conexion):
        self._conexion = conexion

    def commit(self):
        self._conexion.commit()

    def rollback(self):
        self._conexion.rollback()


class CotizacionRepositorySql(CotizacionRepository):
    def __init__(self, conexion):
        self._c = conexion

    def guardar(self, cotizacion):
        self._c.ejecutar(
            """INSERT INTO cotizaciones (folio, cliente_id, ubicacion, superficie,
                   tipo_de_inmueble, frecuencia, extras, duracion_segundos, personal,
                   precio, estado)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT (folio) DO UPDATE SET
                   cliente_id = excluded.cliente_id, ubicacion = excluded.ubicacion,
                   superficie = excluded.superficie,
                   tipo_de_inmueble = excluded.tipo_de_inmueble,
                   frecuencia = excluded.frecuencia, extras = excluded.extras,
                   duracion_segundos = excluded.duracion_segundos,
                   personal = excluded.personal, precio = excluded.precio,
                   estado = excluded.estado""",
            (_clave(cotizacion.folio), cotizacion.cliente_id,
             cotizacion.datos.ubicacion, str(cotizacion.datos.superficie),
             cotizacion.datos.tipo_de_inmueble, cotizacion.frecuencia.valor,
             json.dumps(list(cotizacion.extras)),
             int(cotizacion.estimacion.duracion.total_seconds()),
             cotizacion.estimacion.personal, str(cotizacion.estimacion.precio.monto),
             cotizacion.estado.value))

    def obtenerPorFolio(self, folio):
        fila = self._c.ejecutar(
            """SELECT folio, cliente_id, ubicacion, superficie, tipo_de_inmueble,
                      frecuencia, extras, duracion_segundos, personal, precio, estado
               FROM cotizaciones WHERE folio = ?""", (_clave(folio),)).fetchone()
        if fila is None:
            raise NoEncontrado(f"No existe la cotizacion {_clave(folio)}")
        (f, cliente, ubicacion, superficie, tipo, frecuencia, extras, segundos,
         personal, precio, estado) = fila
        cotizacion = Cotizacion(
            Folio(f), cliente,
            DatosDelInmueble(ubicacion, Decimal(superficie), tipo),
            Frecuencia(frecuencia), tuple(json.loads(extras)),
            Estimacion(timedelta(seconds=segundos), personal, Dinero(Decimal(precio))))
        cotizacion.estado = EstadoDeCotizacion(estado)
        return cotizacion


class ServicioRepositorySql(ServicioRepository):
    _HIJAS = ("incidencias", "extras_servicio", "asignaciones", "historial_servicio")

    def __init__(self, conexion):
        self._c = conexion

    # ---- escritura ----
    def guardar(self, servicio):
        folio = _clave(servicio.folio)
        fecha = servicio.fecha.fecha_hora if servicio.fecha is not None else None
        self._c.ejecutar(
            """INSERT INTO servicios (folio, fecha_hora, dia, estado, cuadrilla_id,
                   inicio, termino)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT (folio) DO UPDATE SET
                   fecha_hora = excluded.fecha_hora, dia = excluded.dia,
                   estado = excluded.estado, cuadrilla_id = excluded.cuadrilla_id,
                   inicio = excluded.inicio, termino = excluded.termino""",
            (folio, _iso(fecha), fecha.date().isoformat() if fecha else None,
             servicio.estado.value, servicio.cuadrilla_id,
             _iso(servicio.tiempo.inicio), _iso(servicio.tiempo.termino)))
        for tabla in self._HIJAS:
            self._c.ejecutar(f"DELETE FROM {tabla} WHERE servicio_folio = ?", (folio,))
        for orden, i in enumerate(servicio.incidencias):
            self._c.ejecutar(
                """INSERT INTO incidencias (servicio_folio, orden, id, tipo, descripcion,
                       hora, reportada_por, empleado_id, estado)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (folio, orden, i.id, i.tipo.value, i.descripcion, _iso(i.hora),
                 i.reportada_por, i.empleado_id, i.estado.value))
        for orden, e in enumerate(servicio.extras):
            self._c.ejecutar(
                """INSERT INTO extras_servicio (servicio_folio, orden, id, descripcion,
                       solicitado_por, estado) VALUES (?,?,?,?,?,?)""",
                (folio, orden, e.id, e.descripcion, e.solicitado_por, e.estado.value))
        for orden, a in enumerate(servicio.asignaciones):
            self._c.ejecutar(
                """INSERT INTO asignaciones (servicio_folio, orden, empleado_original,
                       sustituto, realizada_por, cuando, motivo)
                   VALUES (?,?,?,?,?,?,?)""",
                (folio, orden, a.empleado_original, a.sustituto, a.realizada_por,
                 _iso(a.cuando), a.motivo.texto))
        for orden, h in enumerate(servicio.historial):
            self._c.ejecutar(
                """INSERT INTO historial_servicio (servicio_folio, orden, quien, cuando,
                       que, motivo) VALUES (?,?,?,?,?,?)""",
                (folio, orden, h.quien, _iso(h.cuando), h.que, h.motivo))

    # ---- lectura ----
    def obtenerPorFolio(self, folio):
        clave = _clave(folio)
        fila = self._c.ejecutar(
            """SELECT fecha_hora, estado, cuadrilla_id, inicio, termino
               FROM servicios WHERE folio = ?""", (clave,)).fetchone()
        if fila is None:
            raise NoEncontrado(f"No existe el servicio {clave}")
        fecha_hora, estado, cuadrilla_id, inicio, termino = fila
        servicio = Servicio(Folio(clave),
                            FechaDeServicio(_fecha_hora(fecha_hora)) if fecha_hora else None)
        servicio.estado = EstadoDeServicio(estado)
        servicio.cuadrilla_id = cuadrilla_id
        servicio.tiempo = RegistroDeTiempo(_fecha_hora(inicio), _fecha_hora(termino))
        servicio.incidencias = [
            Incidencia(id=r[0], tipo=TipoDeIncidencia(r[1]), descripcion=r[2],
                       hora=_fecha_hora(r[3]), reportada_por=r[4], empleado_id=r[5],
                       estado=EstadoDeIncidencia(r[6]))
            for r in self._c.ejecutar(
                """SELECT id, tipo, descripcion, hora, reportada_por, empleado_id, estado
                   FROM incidencias WHERE servicio_folio = ? ORDER BY orden""",
                (clave,)).fetchall()]
        servicio.extras = [
            Extra(id=r[0], descripcion=r[1], solicitado_por=r[2],
                  estado=EstadoDeExtra(r[3]))
            for r in self._c.ejecutar(
                """SELECT id, descripcion, solicitado_por, estado FROM extras_servicio
                   WHERE servicio_folio = ? ORDER BY orden""", (clave,)).fetchall()]
        servicio.asignaciones = [
            AsignacionDePersonal(r[0], r[1], r[2], _fecha_hora(r[3]), Motivo(r[4]))
            for r in self._c.ejecutar(
                """SELECT empleado_original, sustituto, realizada_por, cuando, motivo
                   FROM asignaciones WHERE servicio_folio = ? ORDER BY orden""",
                (clave,)).fetchall()]
        servicio.historial = [
            CambioRegistrado(r[0], _fecha_hora(r[1]), r[2], r[3])
            for r in self._c.ejecutar(
                """SELECT quien, cuando, que, motivo FROM historial_servicio
                   WHERE servicio_folio = ? ORDER BY orden""", (clave,)).fetchall()]
        return servicio

    def obtenerConfirmadosPorFecha(self, fecha):
        filas = self._c.ejecutar(
            """SELECT folio FROM servicios
               WHERE dia = ? AND cuadrilla_id IS NOT NULL AND estado NOT IN (?, ?)
               ORDER BY folio""",
            (fecha.dia.isoformat(), *_FINALIZADOS_SIN_CUADRILLA)).fetchall()
        return [self.obtenerPorFolio(f[0]) for f in filas]


class CuadrillaRepositorySql(CuadrillaRepository):
    def __init__(self, conexion):
        self._c = conexion

    def agregar(self, cuadrilla):
        """Alta o actualizacion (datos de apoyo para la demo y las pruebas)."""
        self._c.ejecutar("INSERT INTO cuadrillas (id) VALUES (?) ON CONFLICT (id) DO NOTHING",
                         (cuadrilla.id,))
        self._c.ejecutar("DELETE FROM cuadrilla_integrantes WHERE cuadrilla_id = ?",
                         (cuadrilla.id,))
        for orden, empleado_id in enumerate(cuadrilla.integrantes):
            self._c.ejecutar(
                """INSERT INTO cuadrilla_integrantes (cuadrilla_id, orden, empleado_id)
                   VALUES (?,?,?)""", (cuadrilla.id, orden, empleado_id))

    def obtenerPorId(self, cuadrilla_id):
        if self._c.ejecutar("SELECT id FROM cuadrillas WHERE id = ?",
                            (cuadrilla_id,)).fetchone() is None:
            raise NoEncontrado(f"No existe la cuadrilla {cuadrilla_id}")
        integrantes = self._c.ejecutar(
            """SELECT empleado_id FROM cuadrilla_integrantes
               WHERE cuadrilla_id = ? ORDER BY orden""", (cuadrilla_id,)).fetchall()
        return Cuadrilla(cuadrilla_id, tuple(i[0] for i in integrantes))


class EmpleadoRepositorySql(EmpleadoRepository):
    def __init__(self, conexion):
        self._c = conexion

    def agregar(self, empleado):
        self._c.ejecutar(
            """INSERT INTO empleados (id, nombre, disponible_para_cubrir) VALUES (?,?,?)
               ON CONFLICT (id) DO UPDATE SET nombre = excluded.nombre,
                   disponible_para_cubrir = excluded.disponible_para_cubrir""",
            (empleado.id, empleado.nombre, 1 if empleado.disponible_para_cubrir else 0))

    def obtenerPorId(self, empleado_id):
        fila = self._c.ejecutar(
            "SELECT id, nombre, disponible_para_cubrir FROM empleados WHERE id = ?",
            (empleado_id,)).fetchone()
        if fila is None:
            raise NoEncontrado(f"No existe el empleado {empleado_id}")
        return Empleado(fila[0], fila[1], bool(fila[2]))


def _a_texto(valor):
    return json.dumps(valor, default=str) if valor is not None else None


def _de_texto(texto):
    return json.loads(texto) if texto is not None else None


class ConfiguracionRepositorySql(ConfiguracionRepository):
    """Politicas configurables (RNF-04): una sola fila vigente con su historial."""

    def __init__(self, conexion):
        self._c = conexion

    def guardar(self, politicas):
        self._c.ejecutar(
            """INSERT INTO politicas (id, version, tiempo_de_cortesia,
                   criterio_precio_significativo, politica_cobro_acceso_negado,
                   penalizacion_reprogramacion_tardia)
               VALUES (1,?,?,?,?,?)
               ON CONFLICT (id) DO UPDATE SET version = excluded.version,
                   tiempo_de_cortesia = excluded.tiempo_de_cortesia,
                   criterio_precio_significativo = excluded.criterio_precio_significativo,
                   politica_cobro_acceso_negado = excluded.politica_cobro_acceso_negado,
                   penalizacion_reprogramacion_tardia =
                       excluded.penalizacion_reprogramacion_tardia""",
            (politicas.version, _a_texto(politicas.tiempo_de_cortesia),
             _a_texto(politicas.criterio_precio_significativo),
             _a_texto(politicas.politica_cobro_acceso_negado),
             _a_texto(politicas.penalizacion_reprogramacion_tardia)))
        self._c.ejecutar("DELETE FROM politicas_catalogo")
        for descripcion in sorted(politicas.catalogo_de_extras):
            self._c.ejecutar("INSERT INTO politicas_catalogo (descripcion) VALUES (?)",
                             (descripcion,))
        self._c.ejecutar("DELETE FROM politicas_historial")
        for orden, (actor, cuando, campo, motivo) in enumerate(politicas.historial):
            self._c.ejecutar(
                """INSERT INTO politicas_historial (orden, actor, cuando, campo, motivo)
                   VALUES (?,?,?,?,?)""", (orden, actor, _iso(cuando), campo, motivo))

    def obtenerPoliticasVigentes(self):
        fila = self._c.ejecutar(
            """SELECT version, tiempo_de_cortesia, criterio_precio_significativo,
                      politica_cobro_acceso_negado, penalizacion_reprogramacion_tardia
               FROM politicas WHERE id = 1""").fetchone()
        if fila is None:
            return ConfiguracionDePoliticas()
        catalogo = frozenset(r[0] for r in self._c.ejecutar(
            "SELECT descripcion FROM politicas_catalogo").fetchall())
        historial = [(r[0], _fecha_hora(r[1]), r[2], r[3]) for r in self._c.ejecutar(
            "SELECT actor, cuando, campo, motivo FROM politicas_historial ORDER BY orden"
        ).fetchall()]
        return ConfiguracionDePoliticas(
            version=fila[0], tiempo_de_cortesia=_de_texto(fila[1]),
            catalogo_de_extras=catalogo,
            criterio_precio_significativo=_de_texto(fila[2]),
            politica_cobro_acceso_negado=_de_texto(fila[3]),
            penalizacion_reprogramacion_tardia=_de_texto(fila[4]),
            historial=historial)


class DisponibilidadReadRepositorySql(DisponibilidadReadRepository):
    """Lectura directa con SQL: arma el DTO sin ensamblar Aggregates (CQRS)."""

    def __init__(self, conexion):
        self._c = conexion

    def disponibilidadPorFecha(self, fecha: date):
        ocupadas = {r[0] for r in self._c.ejecutar(
            """SELECT DISTINCT cuadrilla_id FROM servicios
               WHERE dia = ? AND cuadrilla_id IS NOT NULL AND estado NOT IN (?, ?)""",
            (fecha.isoformat(), *_FINALIZADOS_SIN_CUADRILLA)).fetchall()}
        cuadrillas = [r[0] for r in self._c.ejecutar(
            "SELECT id FROM cuadrillas ORDER BY id").fetchall()]
        return [DisponibilidadDTO(c, c not in ocupadas) for c in cuadrillas]