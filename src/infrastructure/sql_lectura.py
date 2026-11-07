"""Lado de lectura del panel operativo (US-18): consultas directas, sin ensamblar Aggregates."""


class PanelReadRepositorySql:
    def __init__(self, conexion):
        self._c = conexion

    def resumen(self, cliente_id=None) -> dict:
        """Panel completo; con `cliente_id` solo sus cotizaciones y servicios."""
        c = self._c
        filtro = "WHERE cliente_id = ?" if cliente_id else ""
        filtro_q = "WHERE q.cliente_id = ?" if cliente_id else ""
        params = (cliente_id,) if cliente_id else ()
        cotizaciones = [
            {"folio": f, "cliente_id": cli, "ubicacion": ub, "tipo_de_inmueble": tipo,
             "frecuencia": frec, "precio": precio, "estado": estado}
            for f, cli, ub, tipo, frec, precio, estado in c.ejecutar(
                """SELECT folio, cliente_id, ubicacion, tipo_de_inmueble, frecuencia,
                          precio, estado FROM cotizaciones """ + filtro
                + " ORDER BY folio", params).fetchall()]
        servicios = [
            {"folio": f, "estado": estado, "fecha": fecha, "cuadrilla_id": cuadrilla,
             "cliente_id": cli, "ubicacion": ub, "pendientes": pend}
            for f, estado, fecha, cuadrilla, cli, ub, pend in c.ejecutar(
                """SELECT s.folio, s.estado, s.fecha_hora, s.cuadrilla_id,
                          q.cliente_id, q.ubicacion,
                          (SELECT COUNT(*) FROM incidencias i
                            WHERE i.servicio_folio = s.folio
                              AND i.estado = 'Pendiente de revision')
                        + (SELECT COUNT(*) FROM extras_servicio e
                            WHERE e.servicio_folio = s.folio
                              AND e.estado = 'Pendiente de confirmacion')
                   FROM servicios s JOIN cotizaciones q ON q.folio = s.folio """
                + filtro_q + " ORDER BY s.folio", params).fetchall()]
        if cliente_id:                       # el cliente no ve cuadrillas ni personal
            return {"cotizaciones": cotizaciones, "servicios": servicios,
                    "cuadrillas": [], "empleados": []}
        integrantes = {}
        for cuadrilla, empleado in c.ejecutar(
                """SELECT cuadrilla_id, empleado_id FROM cuadrilla_integrantes
                   ORDER BY cuadrilla_id, orden""").fetchall():
            integrantes.setdefault(cuadrilla, []).append(empleado)
        cuadrillas = [{"id": i, "integrantes": integrantes.get(i, [])} for (i,) in
                      c.ejecutar("SELECT id FROM cuadrillas ORDER BY id").fetchall()]
        empleados = [{"id": i, "nombre": n, "disponible_para_cubrir": bool(d)}
                     for i, n, d in c.ejecutar(
                         "SELECT id, nombre, disponible_para_cubrir FROM empleados ORDER BY id"
                     ).fetchall()]
        return {"cotizaciones": cotizaciones, "servicios": servicios,
                "cuadrillas": cuadrillas, "empleados": empleados}
