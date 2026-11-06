"""Pruebas de contrato de los Repository y la Unit of Work (hallazgo SOLID, LSP).

Cada clase *Contrato describe lo que la capa de aplicacion espera de una
interfaz, sin importar su implementacion. Hoy solo existe la version en
memoria; una version SQL se probaria heredando el mismo contrato y
sobrescribiendo crearRepositorio() (o crearUnidad()). Si la nueva
implementacion no pasa la bateria, no es sustituible (Liskov).
"""
import unittest

from src.domain.errores import NoEncontrado
from src.domain.valores import FechaDeServicio
from src.infrastructure.en_memoria import (BaseDeDatosEnMemoria,
                                                 CotizacionRepositoryEnMemoria,
                                                 ServicioRepositoryEnMemoria,
                                                 UnitOfWorkEnMemoria)

from .utiles import FECHA, FOLIO, cotizacionVigente, servicioConCuadrilla, servicioProgramado


class ServicioRepositoryContrato:
    def crearRepositorio(self):
        raise NotImplementedError

    def test_guarda_y_recupera_el_aggregate_completo_por_folio(self):
        repo = self.crearRepositorio()
        repo.guardar(servicioConCuadrilla())
        recuperado = repo.obtenerPorFolio(FOLIO)
        self.assertEqual(recuperado.folio, FOLIO)
        self.assertEqual(recuperado.cuadrilla_id, "cuad-1")

    def test_folio_inexistente_se_informa_con_error_de_negocio(self):
        with self.assertRaises(NoEncontrado):
            self.crearRepositorio().obtenerPorFolio(FOLIO)

    def test_confirmados_por_fecha_excluye_servicios_sin_cuadrilla(self):
        repo = self.crearRepositorio()
        repo.guardar(servicioProgramado())
        self.assertEqual(repo.obtenerConfirmadosPorFecha(FECHA), [])
        repo.guardar(servicioConCuadrilla())
        self.assertEqual(len(repo.obtenerConfirmadosPorFecha(FECHA)), 1)


class CotizacionRepositoryContrato:
    def crearRepositorio(self):
        raise NotImplementedError

    def test_guarda_y_recupera_la_cotizacion_por_folio(self):
        repo = self.crearRepositorio()
        repo.guardar(cotizacionVigente())
        self.assertEqual(repo.obtenerPorFolio(FOLIO).folio, FOLIO)

    def test_folio_inexistente_se_informa_con_error_de_negocio(self):
        with self.assertRaises(NoEncontrado):
            self.crearRepositorio().obtenerPorFolio(FOLIO)


class UnitOfWorkContrato:
    def crearUnidad(self):
        """Debe devolver (unidad, repositorio de servicios) sobre el mismo almacen."""
        raise NotImplementedError

    def test_rollback_descarta_lo_guardado_y_commit_lo_conserva(self):
        uow, repo = self.crearUnidad()
        repo.guardar(servicioProgramado())
        uow.rollback()
        with self.assertRaises(NoEncontrado):
            repo.obtenerPorFolio(FOLIO)
        repo.guardar(servicioProgramado())
        uow.commit()
        uow.rollback()   # tras commit ya no hay nada que revertir
        self.assertEqual(repo.obtenerPorFolio(FOLIO).folio, FOLIO)


class ServicioRepositoryEnMemoriaTest(ServicioRepositoryContrato, unittest.TestCase):
    def crearRepositorio(self):
        return ServicioRepositoryEnMemoria(BaseDeDatosEnMemoria())


class CotizacionRepositoryEnMemoriaTest(CotizacionRepositoryContrato, unittest.TestCase):
    def crearRepositorio(self):
        return CotizacionRepositoryEnMemoria(BaseDeDatosEnMemoria())


class UnitOfWorkEnMemoriaTest(UnitOfWorkContrato, unittest.TestCase):
    def crearUnidad(self):
        bd = BaseDeDatosEnMemoria()
        return UnitOfWorkEnMemoria(bd), ServicioRepositoryEnMemoria(bd)


if __name__ == "__main__":
    unittest.main()
