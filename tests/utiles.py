"""Datos de ejemplo. Valores ilustrativos: la U2 no define tarifas ni catalogos."""
from datetime import datetime, timedelta
from decimal import Decimal

from src.domain.cotizacion import Cotizacion
from src.domain.cuadrilla import Cuadrilla, Empleado
from src.domain.servicio import Servicio
from src.domain.valores import (Actor, DatosDelInmueble, Dinero, Estimacion,
                                      FechaDeServicio, Folio, Frecuencia, Motivo, Rol)

FOLIO = Folio("COT-0001")
FECHA = FechaDeServicio(datetime(2026, 10, 20, 8, 0))
COORDINADOR = Actor("coord-1", Rol.COORDINADOR)
SUPERVISOR = Actor("sup-1", Rol.SUPERVISOR)
ADMIN = Actor("admin-1", Rol.ADMINISTRACION)


def cotizacionVigente(folio=FOLIO, cliente_id="cli-1"):
    return Cotizacion.emitir(
        folio, cliente_id,
        DatosDelInmueble("Monterrey, N.L.", Decimal("120"), "Casa"),
        Frecuencia("Semanal"), ("Ventanas",),
        Estimacion(timedelta(hours=4), 2, Dinero(Decimal("1500"))))


def servicioProgramado(fecha=FECHA):
    cot = cotizacionVigente()
    cot.aceptar()
    return Servicio.programarDesde(cot, fecha)


def servicioConCuadrilla():
    s = servicioProgramado()
    s.confirmarCuadrilla("cuad-1", True, COORDINADOR)
    return s


def servicioEnEjecucion():
    s = servicioConCuadrilla()
    s.registrarInicio(SUPERVISOR, datetime(2026, 10, 20, 8, 5))
    return s


def servicioTerminado():
    s = servicioEnEjecucion()
    s.registrarTermino(SUPERVISOR, datetime(2026, 10, 20, 12, 0))
    return s


def poblar(app):
    """Carga cuadrillas, empleados, catalogo de extras y una cotizacion Vigente."""
    bd = app.bd
    bd.cuadrillas["cuad-1"] = Cuadrilla("cuad-1", ("emp-1", "emp-2"))
    bd.cuadrillas["cuad-2"] = Cuadrilla("cuad-2", ("emp-3",))
    bd.empleados["emp-1"] = Empleado("emp-1", "Ana")
    bd.empleados["emp-2"] = Empleado("emp-2", "Luis")
    bd.empleados["emp-3"] = Empleado("emp-3", "Rosa")
    bd.empleados["emp-ocupado"] = Empleado("emp-ocupado", "Mario", False)
    bd.politicas.actualizarCatalogoDeExtras(
        {"Limpieza de ventanas"}, ADMIN, Motivo("Catalogo inicial de prueba"))
    bd.cotizaciones[FOLIO] = cotizacionVigente()
