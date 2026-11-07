"""Login, lectura del token y bloqueo por intentos fallidos (paso 3).

Aun no se protegen los endpoints de negocio (paso 4): aqui solo se prueba /auth/*.
"""
import os
import tempfile
import unittest
from unittest import mock

try:
    from fastapi.testclient import TestClient
    from src.api.autenticacion import LimitadorDeIntentos
    from src.api.main import crear_app
    HAY_FASTAPI = True
except ImportError:                                   # pragma: no cover
    HAY_FASTAPI = False

from src.domain.usuario import Usuario
from src.domain.valores import Rol
from src.infrastructure.seguridad import ServicioDeTokens
from src.infrastructure.sql_usuarios import UsuarioRepositorySql

SECRETO = "secreto-de-prueba-0123456789"
CLAVE = "Demo-1234"
RAPIDO = 1000


class RelojFalso:
    def __init__(self):
        self.ahora = 1000.0

    def __call__(self):
        return self.ahora


@unittest.skipUnless(HAY_FASTAPI, "fastapi/httpx no instalados")
class LimitadorTest(unittest.TestCase):
    def setUp(self):
        self.reloj = RelojFalso()
        self.limitador = LimitadorDeIntentos(maximo=3, segundos=60, reloj=self.reloj)

    def test_bloquea_al_llegar_al_maximo_y_libera_al_vencer(self):
        for _ in range(2):
            self.limitador.registrarFallo("u")
        self.assertEqual(self.limitador.segundosRestantes("u"), 0)
        self.limitador.registrarFallo("u")
        self.assertGreater(self.limitador.segundosRestantes("u"), 0)
        self.reloj.ahora += 61
        self.assertEqual(self.limitador.segundosRestantes("u"), 0)

    def test_un_acierto_reinicia_la_cuenta(self):
        self.limitador.registrarFallo("u")
        self.limitador.registrarFallo("u")
        self.limitador.registrarAcierto("u")
        self.limitador.registrarFallo("u")
        self.assertEqual(self.limitador.segundosRestantes("u"), 0)

    def test_cada_usuario_lleva_su_propia_cuenta(self):
        for _ in range(3):
            self.limitador.registrarFallo("a")
        self.assertGreater(self.limitador.segundosRestantes("a"), 0)
        self.assertEqual(self.limitador.segundosRestantes("b"), 0)

    def test_tras_vencer_el_bloqueo_se_empieza_de_cero(self):
        for _ in range(3):
            self.limitador.registrarFallo("u")
        self.reloj.ahora += 61
        self.limitador.registrarFallo("u")             # primer fallo del nuevo ciclo
        self.assertEqual(self.limitador.segundosRestantes("u"), 0)


@unittest.skipUnless(HAY_FASTAPI, "fastapi/httpx no instalados")
class AutenticacionApiTest(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        url = "sqlite:///" + os.path.join(self.carpeta.name, "auth.db")
        self.app = crear_app(url, cargar_demo=True, secreto=SECRETO, iteraciones_clave=RAPIDO)
        with mock.patch.dict(os.environ, {"CLEANPRO_CLAVE_DEMO": CLAVE}):
            self.http = TestClient(self.app)
            self.http.__enter__()                     # arranque: esquema + demo + usuarios
        self.reloj = RelojFalso()
        self.app.state.limitador = LimitadorDeIntentos(reloj=self.reloj)

    def tearDown(self):
        self.http.__exit__(None, None, None)
        self.carpeta.cleanup()

    def login(self, usuario="sup1", clave=CLAVE):
        return self.http.post("/auth/login", json={"usuario": usuario, "clave": clave})

    def token(self, usuario="sup1"):
        return self.login(usuario).json()["access_token"]

    def yo(self, token=None):
        cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
        return self.http.get("/auth/yo", headers=cabeceras)

    def cambiar_usuario(self, usuario, **cambios):
        conexion = self.app.state.bd.abrir()
        try:
            repo = UsuarioRepositorySql(conexion)
            actual = repo.obtenerPorNombreDeUsuario(usuario)
            datos = dict(nombre_de_usuario=actual.nombre_de_usuario, nombre=actual.nombre,
                         rol=actual.rol, actor_id=actual.actor_id,
                         clave_hash=actual.clave_hash, activo=actual.activo)
            datos.update(cambios)
            repo.guardar(Usuario(**datos))
            conexion.commit()
        finally:
            conexion.cerrar()

    # ---- login ----
    def test_login_correcto_devuelve_token_y_usuario(self):
        r = self.login()
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        self.assertEqual(cuerpo["token_type"], "bearer")
        self.assertEqual(cuerpo["usuario"], {"usuario": "sup1", "nombre": "Supervisor demo",
                                             "rol": "Supervisor", "actor_id": "sup-1"})
        self.assertGreater(cuerpo["expira_en"], 0)
        datos = ServicioDeTokens(SECRETO).verificar(cuerpo["access_token"])
        self.assertEqual(datos["sub"], "sup1")

    def test_clave_incorrecta_y_usuario_inexistente_dan_la_misma_respuesta(self):
        mala = self.login(clave="otra")
        nadie = self.login(usuario="nadie")
        self.assertEqual((mala.status_code, nadie.status_code), (401, 401))
        self.assertEqual(mala.json(), nadie.json())
        self.assertEqual(mala.json()["codigo"], "CREDENCIALES_INVALIDAS")
        self.assertEqual(mala.headers["www-authenticate"], "Bearer")

    def test_usuario_desactivado_no_puede_iniciar_sesion(self):
        self.cambiar_usuario("sup1", activo=False)
        self.assertEqual(self.login().status_code, 401)

    def test_login_sin_campos_es_422(self):
        self.assertEqual(self.http.post("/auth/login", json={}).status_code, 422)

    def test_bloqueo_tras_cinco_fallos_aun_con_la_clave_correcta(self):
        for _ in range(5):
            self.assertEqual(self.login(clave="x").status_code, 401)
        r = self.login()                               # clave correcta, pero bloqueado
        self.assertEqual((r.status_code, r.json()["codigo"]), (429, "DEMASIADOS_INTENTOS"))
        self.reloj.ahora += 61
        self.assertEqual(self.login().status_code, 200)

    def test_un_login_correcto_reinicia_los_fallos(self):
        for _ in range(4):
            self.login(clave="x")
        self.assertEqual(self.login().status_code, 200)
        for _ in range(4):
            self.login(clave="x")
        self.assertEqual(self.login().status_code, 200)    # sigue sin bloquearse

    # ---- lectura del token ----
    def test_yo_con_token_valido(self):
        r = self.yo(self.token("admin1"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json()["rol"], r.json()["actor_id"]), ("Administracion", "admin-1"))

    def test_yo_sin_token_o_con_token_basura_es_401(self):
        for token in (None, "basura", "a.b"):
            r = self.yo(token)
            self.assertEqual((r.status_code, r.json()["codigo"]), (401, "NO_AUTENTICADO"))
            self.assertEqual(r.headers["www-authenticate"], "Bearer")

    def test_token_vencido_o_de_otro_secreto_es_401(self):
        vencido = ServicioDeTokens(SECRETO, vigencia_segundos=-10).emitir("sup1", "Supervisor")
        ajeno = ServicioDeTokens("otro-secreto-0123456789").emitir("sup1", "Supervisor")
        self.assertEqual(self.yo(vencido).status_code, 401)
        self.assertEqual(self.yo(ajeno).status_code, 401)

    def test_token_de_usuario_inexistente_es_401(self):
        fantasma = ServicioDeTokens(SECRETO).emitir("fantasma", "Administracion")
        self.assertEqual(self.yo(fantasma).status_code, 401)

    def test_desactivar_al_usuario_invalida_su_token_al_instante(self):
        token = self.token()
        self.assertEqual(self.yo(token).status_code, 200)
        self.cambiar_usuario("sup1", activo=False)
        self.assertEqual(self.yo(token).status_code, 401)

    def test_el_rol_sale_de_la_base_no_del_token(self):
        # Token de un supervisor, pero el token AFIRMA ser Administracion: se ignora.
        falso = ServicioDeTokens(SECRETO).emitir("sup1", "Administracion")
        self.assertEqual(self.yo(falso).json()["rol"], "Supervisor")
        # Y si el rol cambia en la base, el mismo token ya refleja el nuevo.
        token = self.token()
        self.cambiar_usuario("sup1", rol=Rol.COORDINADOR)
        self.assertEqual(self.yo(token).json()["rol"], "Coordinador")

    # ---- documentacion y arranque ----
    def test_openapi_documenta_login_y_el_esquema_bearer(self):
        spec = self.http.get("/openapi.json").json()
        self.assertIn("/auth/login", spec["paths"])
        self.assertIn("HTTPBearer", spec["components"]["securitySchemes"])

    def test_sin_secreto_configurado_arranca_con_uno_aleatorio(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            app = crear_app("sqlite:///:memory:", iteraciones_clave=RAPIDO)
        self.assertIsNotNone(app.state.tokens)

    def test_el_secreto_se_lee_de_cleanpro_secret(self):
        with mock.patch.dict(os.environ, {"CLEANPRO_SECRET": SECRETO}):
            app = crear_app("sqlite:///:memory:", iteraciones_clave=RAPIDO)
        token = app.state.tokens.emitir("u", "Cliente")
        self.assertEqual(ServicioDeTokens(SECRETO).verificar(token)["sub"], "u")


if __name__ == "__main__":
    unittest.main()
