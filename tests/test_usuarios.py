"""Repository de usuarios y usuarios de demostracion.

La bateria `UsuariosContrato` se ejecuta sobre SQLite aqui y sobre PostgreSQL en
tests/test_postgres.py (mismo contrato, solo cambia la conexion).
"""
import unittest

from src.domain.errores import NoEncontrado
from src.domain.usuario import Usuario
from src.domain.valores import Actor, Rol
from src.infrastructure.base_de_datos import BaseDeDatos
from src.infrastructure.datos_demo import USUARIOS_DEMO, cargarUsuarios
from src.infrastructure.seguridad import verificarClave
from src.infrastructure.sql_usuarios import UsuarioRepositorySql

RAPIDO = 1000                      # pocas iteraciones: solo para que las pruebas corran rapido


class UsuariosContrato:
    def abrirConexion(self):
        raise NotImplementedError

    def setUp(self):
        self.conexion = self.abrirConexion()
        self.repo = UsuarioRepositorySql(self.conexion)

    def tearDown(self):
        self.conexion.cerrar()

    def nuevo(self, **cambios):
        datos = dict(nombre_de_usuario="sup1", nombre="Supervisor", rol=Rol.SUPERVISOR,
                     actor_id="sup-1", clave_hash="hash-de-prueba", activo=True)
        datos.update(cambios)
        return Usuario(**datos)

    def test_guardar_y_leer(self):
        self.repo.guardar(self.nuevo())
        u = self.repo.obtenerPorNombreDeUsuario("sup1")
        self.assertEqual((u.nombre, u.rol, u.actor_id, u.activo),
                         ("Supervisor", Rol.SUPERVISOR, "sup-1", True))
        self.assertEqual(u.actor, Actor("sup-1", Rol.SUPERVISOR))

    def test_usuario_inexistente_lanza_no_encontrado(self):
        with self.assertRaises(NoEncontrado):
            self.repo.obtenerPorNombreDeUsuario("nadie")

    def test_guardar_dos_veces_actualiza_en_lugar_de_duplicar(self):
        self.repo.guardar(self.nuevo())
        self.repo.guardar(self.nuevo(activo=False, nombre="Otro nombre"))
        u = self.repo.obtenerPorNombreDeUsuario("sup1")
        self.assertEqual((u.activo, u.nombre), (False, "Otro nombre"))
        self.assertEqual(self.repo.contar(), 1)

    def test_contar(self):
        self.assertEqual(self.repo.contar(), 0)
        self.repo.guardar(self.nuevo())
        self.repo.guardar(self.nuevo(nombre_de_usuario="admin1", actor_id="admin-1",
                                     rol=Rol.ADMINISTRACION))
        self.assertEqual(self.repo.contar(), 2)

    def test_usuarios_de_demo_se_crean_una_sola_vez_y_su_clave_verifica(self):
        self.assertTrue(cargarUsuarios(self.conexion, clave="Demo-1234", iteraciones=RAPIDO))
        self.assertFalse(cargarUsuarios(self.conexion, clave="otra", iteraciones=RAPIDO))
        self.assertEqual(self.repo.contar(), len(USUARIOS_DEMO))
        admin = self.repo.obtenerPorNombreDeUsuario("admin1")
        self.assertEqual((admin.rol, admin.actor_id), (Rol.ADMINISTRACION, "admin-1"))
        self.assertTrue(verificarClave("Demo-1234", admin.clave_hash))
        self.assertFalse(verificarClave("otra", admin.clave_hash))

    def test_el_actor_de_cada_usuario_demo_coincide_con_los_datos_de_demo(self):
        cargarUsuarios(self.conexion, clave="x", iteraciones=RAPIDO)
        actores = {u: self.repo.obtenerPorNombreDeUsuario(u).actor_id
                   for u, *_ in USUARIOS_DEMO}
        self.assertEqual(actores["cliente1"], "cli-1")       # dueno de COT-0001
        self.assertEqual(actores["coord1"], "coord-1")

    def test_repr_no_expone_el_hash(self):
        self.assertNotIn("hash-de-prueba", repr(self.nuevo()))


class UsuariosSqlite(UsuariosContrato, unittest.TestCase):
    def abrirConexion(self):
        conexion = BaseDeDatos("sqlite:///:memory:").abrir()
        conexion.crearEsquema()
        return conexion


if __name__ == "__main__":
    unittest.main()
