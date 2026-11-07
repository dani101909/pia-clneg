"""Repository de usuarios sobre SQL (SQLite / PostgreSQL)."""
from ..domain.errores import NoEncontrado
from ..domain.repositorios import UsuarioRepository
from ..domain.usuario import Usuario
from ..domain.valores import Rol


class UsuarioRepositorySql(UsuarioRepository):
    def __init__(self, conexion):
        self._c = conexion

    def guardar(self, usuario):
        self._c.ejecutar(
            """INSERT INTO usuarios (nombre_de_usuario, nombre, rol, actor_id,
                                     clave_hash, activo)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT (nombre_de_usuario) DO UPDATE SET
                   nombre = excluded.nombre, rol = excluded.rol,
                   actor_id = excluded.actor_id, clave_hash = excluded.clave_hash,
                   activo = excluded.activo""",
            (usuario.nombre_de_usuario, usuario.nombre, usuario.rol.value,
             usuario.actor_id, usuario.clave_hash, 1 if usuario.activo else 0))

    def obtenerPorNombreDeUsuario(self, nombre_de_usuario):
        fila = self._c.ejecutar(
            """SELECT nombre_de_usuario, nombre, rol, actor_id, clave_hash, activo
               FROM usuarios WHERE nombre_de_usuario = ?""",
            (nombre_de_usuario,)).fetchone()
        if fila is None:
            raise NoEncontrado("No existe el usuario")
        usuario, nombre, rol, actor, clave_hash, activo = fila
        return Usuario(usuario, nombre, Rol(rol), actor, clave_hash, bool(activo))

    def contar(self):
        return self._c.ejecutar("SELECT COUNT(*) FROM usuarios").fetchone()[0]
