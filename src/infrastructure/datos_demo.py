"""Datos de demostracion de CleanPro (valores ilustrativos; la U2 no define tarifas).

Uso manual:  python -m src.infrastructure.datos_demo
En la API:   CLEANPRO_DEMO=1 (se cargan al arrancar, solo si la BD esta vacia).
"""
from datetime import datetime, timedelta
from decimal import Decimal

from ..domain.cotizacion import Cotizacion
from ..domain.cuadrilla import Cuadrilla, Empleado
from ..domain.valores import (Actor, DatosDelInmueble, Dinero, Estimacion, Folio,
                              Frecuencia, Motivo, Rol)
from .sql_repositorios import (ConfiguracionRepositorySql, CotizacionRepositorySql,
                               CuadrillaRepositorySql, EmpleadoRepositorySql)


def cargar(conexion):
    if conexion.ejecutar("SELECT COUNT(*) FROM cuadrillas").fetchone()[0]:
        return False                                     # ya hay datos
    cuadrillas = CuadrillaRepositorySql(conexion)
    cuadrillas.agregar(Cuadrilla("cuad-1", ("emp-1", "emp-2")))
    cuadrillas.agregar(Cuadrilla("cuad-2", ("emp-3", "emp-4")))
    empleados = EmpleadoRepositorySql(conexion)
    for id_, nombre, libre in (("emp-1", "Ana Torres", True), ("emp-2", "Luis Garza", True),
                               ("emp-3", "Rosa Medina", True), ("emp-4", "Mario Cantu", True),
                               ("emp-5", "Elena Ruiz", True), ("emp-6", "Pablo Leal", False)):
        empleados.agregar(Empleado(id_, nombre, libre))
    configuracion = ConfiguracionRepositorySql(conexion)
    politicas = configuracion.obtenerPoliticasVigentes()
    politicas.actualizarCatalogoDeExtras(
        {"Limpieza de ventanas", "Lavado de alfombra", "Limpieza de cocina profunda"},
        Actor("admin-1", Rol.ADMINISTRACION), Motivo("Catalogo inicial de demostracion"))
    configuracion.guardar(politicas)
    cotizaciones = CotizacionRepositorySql(conexion)
    for folio, cliente, lugar, m2, tipo, frecuencia, horas, personal, precio in (
            ("COT-0001", "cli-1", "Monterrey, N.L.", "120", "Casa", "Semanal", 4, 2, "1500"),
            ("COT-0002", "cli-2", "San Pedro, N.L.", "450", "Oficina", "Diaria", 6, 3, "4200"),
            ("COT-0003", "cli-3", "Apodaca, N.L.", "80", "Departamento", "Unica", 3, 2, "950")):
        cotizaciones.guardar(Cotizacion.emitir(
            Folio(folio), cliente, DatosDelInmueble(lugar, Decimal(m2), tipo),
            Frecuencia(frecuencia), ("Limpieza de ventanas",),
            Estimacion(timedelta(hours=horas), personal, Dinero(Decimal(precio)))))
    conexion.commit()
    return True


if __name__ == "__main__":
    from .base_de_datos import BaseDeDatos
    c = BaseDeDatos().abrir()
    c.crearEsquema()
    print("Datos cargados" if cargar(c) else "La base ya tenia datos")
    c.cerrar()
