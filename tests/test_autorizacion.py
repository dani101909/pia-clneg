"""Autorizacion por rol (paso 4): quien puede hacer que, y que cada quien ve solo lo suyo."""
import os
import tempfile
import unittest
from unittest import mock

try:
    from fastapi.testclient import TestClient
    from src.api.main import crear_app
    HAY_FASTAPI = True
except ImportError:                                   # pragma: no cover
    HAY_FASTAPI = False

from src.domain.usuario import Usuario
from src.domain.valores import Rol
from src.infrastructure.sql_usuarios import UsuarioRepositorySql

CLAVE = "Demo-1234"
FECHA = "2026-11-20T08:00:00"
CLIENTE, COORD, SUP, ADMIN = "cliente1", "coord1", "sup1", "admin1"
POR_ROL = {CLIENTE: Rol.CLIENTE, COORD: Rol.COORDINADOR, SUP: Rol.SUPERVISOR,
           ADMIN: Rol.ADMINISTRACION}
COTIZACION = {"cliente_id": "cli-9", "ubicacion": "Monterrey", "superficie": "60",
              "tipo_de_inmueble": "Casa", "frecuencia": "Unica", "extras": [],
              "duracion_horas": "2", "personal": 2, "precio": "800"}

# (metodo, ruta, cuerpo, roles permitidos). El folio no existe: para un rol permitido
# la respuesta es 404/422/201..., nunca 401 ni 403 (el permiso se revisa antes).
ENDPOINTS_POR_ROL = (
    ("POST", "/cotizaciones", COTIZACION, {Rol.COORDINADOR, Rol.ADMINISTRACION}),
    ("POST", "/cotizaciones/COT-9999/aceptacion", {}, {Rol.CLIENTE}),
    ("POST", "/servicios/COT-9999/cuadrilla", {"cuadrilla_id": "cuad-1"}, {Rol.COORDINADOR}),
    ("POST", "/servicios/COT-9999/inicio", None, {Rol.SUPERVISOR}),
    ("POST", "/servicios/COT-9999/termino", None, {Rol.SUPERVISOR}),
    ("POST", "/servicios/COT-9999/ausencias", {"empleado_id": "emp-1"}, {Rol.SUPERVISOR}),
    ("POST", "/servicios/COT-9999/reasignaciones",
     {"empleado_id": "emp-1", "sustituto_id": None}, {Rol.ADMINISTRACION}),
    ("POST", "/servicios/COT-9999/extras", {"descripcion": "x"}, {Rol.SUPERVISOR}),
    ("POST", "/servicios/COT-9999/extras/EXT-1/confirmacion", None, {Rol.COORDINADOR}),
    ("POST", "/servicios/COT-9999/incidencias",
     {"tipo": "DanioReportado", "descripcion": "x"}, {Rol.SUPERVISOR}),
    ("POST", "/servicios/COT-9999/incidencias/INC-1/revision", None, {Rol.ADMINISTRACION}),
    ("POST", "/servicios/COT-9999/cierre", None, {Rol.ADMINISTRACION}),
    ("GET", "/disponibilidad?fecha=2026-11-20", None,
     {Rol.COORDINADOR, Rol.SUPERVISOR, Rol.ADMINISTRACION}),
)
SOLO_AUTENTICADOS = (("GET", "/panel"), ("GET", "/cotizaciones/COT-0001"),
                     ("GET", "/servicios/COT-0001"), ("GET", "/auth/yo"))


@unittest.skipUnless(HAY_FASTAPI, "fastapi/httpx no instalados")
class AutorizacionTest(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        url = "sqlite:///" + os.path.join(self.carpeta.name, "aut.db")
        self.app = crear_app(url, cargar_demo=True, iteraciones_clave=1000,
                             secreto="secreto-de-prueba-0123456789")
        self.http = TestClient(self.app)
        with mock.patch.dict(os.environ, {"CLEANPRO_CLAVE_DEMO": CLAVE}):
            self.http.__enter__()
        self.tokens = {}

    def tearDown(self):
        self.http.__exit__(None, None, None)
        self.carpeta.cleanup()

    def cabeceras(self, como):
        if como not in self.tokens:
            r = self.http.post("/auth/login", json={"usuario": como, "clave": CLAVE})
            self.tokens[como] = r.json()["access_token"]
        return {"Authorization": f"Bearer {self.tokens[como]}"}

    def llamar(self, metodo, ruta, cuerpo=None, como=None):
        cabeceras = self.cabeceras(como) if como else {}
        if cuerpo is None:
            return self.http.request(metodo, ruta, headers=cabeceras)
        return self.http.request(metodo, ruta, json=cuerpo, headers=cabeceras)

    def programar(self):
        self.llamar("POST", "/cotizaciones/COT-0001/aceptacion", {"fecha": FECHA}, CLIENTE)
        self.llamar("POST", "/servicios/COT-0001/cuadrilla", {"cuadrilla_id": "cuad-1"}, COORD)

    def cambiar_usuario(self, usuario, **cambios):
        conexion = self.app.state.bd.abrir()
        try:
            repo = UsuarioRepositorySql(conexion)
            u = repo.obtenerPorNombreDeUsuario(usuario)
            datos = dict(nombre_de_usuario=u.nombre_de_usuario, nombre=u.nombre, rol=u.rol,
                         actor_id=u.actor_id, clave_hash=u.clave_hash, activo=u.activo)
            datos.update(cambios)
            repo.guardar(Usuario(**datos))
            conexion.commit()
        finally:
            conexion.cerrar()

    # ---- sin token ----
    def test_sin_token_todo_endpoint_protegido_responde_401(self):
        peticiones = [(m, r, c) for m, r, c, _ in ENDPOINTS_POR_ROL] + \
                     [(m, r, None) for m, r in SOLO_AUTENTICADOS]
        for metodo, ruta, cuerpo in peticiones:
            with self.subTest(f"{metodo} {ruta}"):
                r = self.llamar(metodo, ruta, cuerpo)
                self.assertEqual((r.status_code, r.json()["codigo"]), (401, "NO_AUTENTICADO"))

    def test_lo_publico_sigue_publico(self):
        for ruta in ("/salud", "/", "/docs", "/openapi.json"):
            self.assertEqual(self.http.get(ruta).status_code, 200, ruta)

    # ---- matriz de roles ----
    def test_cada_endpoint_solo_acepta_los_roles_permitidos(self):
        for metodo, ruta, cuerpo, permitidos in ENDPOINTS_POR_ROL:
            for usuario, rol in POR_ROL.items():
                with self.subTest(f"{metodo} {ruta} como {rol.value}"):
                    r = self.llamar(metodo, ruta, cuerpo, usuario)
                    if rol in permitidos:
                        self.assertNotIn(r.status_code, (401, 403), r.text)
                    else:
                        self.assertEqual((r.status_code, r.json()["codigo"]),
                                         (403, "SIN_PERMISO"), r.text)

    def test_la_respuesta_403_dice_que_roles_pueden(self):
        r = self.llamar("POST", "/servicios/COT-0001/cierre", None, SUP)
        self.assertIn("Administracion", r.json()["detalle"])

    # ---- el actor sale del token ----
    def test_ids_de_actor_en_el_cuerpo_se_ignoran(self):
        self.programar()
        self.llamar("POST", "/servicios/COT-0001/inicio", None, SUP)
        r = self.llamar("POST", "/servicios/COT-0001/incidencias",
                        {"tipo": "DanioReportado", "descripcion": "Vidrio roto",
                         "supervisor_id": "admin-1"}, SUP)          # intento de suplantar
        self.assertEqual(r.status_code, 201)
        incidencia = r.json()["servicio"]["incidencias"][0]
        self.assertEqual(incidencia["reportada_por"], "sup-1")      # el del token, no el del cuerpo

    def test_un_cliente_no_acepta_la_cotizacion_de_otro_aunque_mande_su_id(self):
        r = self.llamar("POST", "/cotizaciones/COT-0001/aceptacion",
                        {"cliente_id": "cli-1"}, "cliente2")
        self.assertEqual((r.status_code, r.json()["codigo"]), (403, "SIN_PERMISO"))

    # ---- cada cliente ve solo lo suyo ----
    def test_cliente_solo_consulta_sus_cotizaciones(self):
        self.assertEqual(self.llamar("GET", "/cotizaciones/COT-0001", None, CLIENTE).status_code, 200)
        r = self.llamar("GET", "/cotizaciones/COT-0002", None, CLIENTE)
        self.assertEqual((r.status_code, r.json()["codigo"]), (403, "SIN_PERMISO"))
        self.assertEqual(self.llamar("GET", "/cotizaciones/COT-0002", None, COORD).status_code, 200)

    def test_cliente_solo_consulta_su_servicio(self):
        self.programar()
        self.assertEqual(self.llamar("GET", "/servicios/COT-0001", None, CLIENTE).status_code, 200)
        self.assertEqual(self.llamar("GET", "/servicios/COT-0001", None, "cliente2").status_code, 403)
        self.assertEqual(self.llamar("GET", "/servicios/COT-0001", None, SUP).status_code, 200)

    def test_panel_del_cliente_solo_trae_lo_suyo_y_sin_cuadrillas_ni_personal(self):
        self.programar()
        panel = self.llamar("GET", "/panel", None, CLIENTE).json()
        self.assertEqual([c["folio"] for c in panel["cotizaciones"]], ["COT-0001"])
        self.assertEqual([s["folio"] for s in panel["servicios"]], ["COT-0001"])
        self.assertEqual((panel["cuadrillas"], panel["empleados"]), ([], []))
        otro = self.llamar("GET", "/panel", None, "cliente2").json()
        self.assertEqual(otro["servicios"], [])
        self.assertEqual([c["folio"] for c in otro["cotizaciones"]], ["COT-0002"])

    def test_panel_del_personal_interno_trae_todo(self):
        self.programar()
        for usuario in (COORD, SUP, ADMIN):
            panel = self.llamar("GET", "/panel", None, usuario).json()
            self.assertEqual(len(panel["cotizaciones"]), 3)
            self.assertEqual(len(panel["cuadrillas"]), 2)
            self.assertEqual(len(panel["empleados"]), 6)

    def test_una_cotizacion_nueva_solo_la_ve_su_cliente(self):
        r = self.llamar("POST", "/cotizaciones", {**COTIZACION, "cliente_id": "cli-1"}, COORD)
        folio = r.json()["cotizacion"]["folio"]
        self.assertEqual(self.llamar("GET", f"/cotizaciones/{folio}", None, CLIENTE).status_code, 200)
        self.assertEqual(self.llamar("GET", f"/cotizaciones/{folio}", None, "cliente3").status_code, 403)

    # ---- el rol manda la base de datos ----
    def test_cambiar_el_rol_en_la_base_cambia_los_permisos_del_mismo_token(self):
        self.programar()
        self.assertEqual(self.llamar("POST", "/servicios/COT-0001/inicio", None, SUP).status_code, 200)
        self.cambiar_usuario(SUP, rol=Rol.CLIENTE)                  # mismo token, otro rol
        r = self.llamar("POST", "/servicios/COT-0001/termino", None, SUP)
        self.assertEqual((r.status_code, r.json()["codigo"]), (403, "SIN_PERMISO"))

    def test_desactivar_al_usuario_le_quita_el_acceso_al_instante(self):
        self.programar()
        self.assertEqual(self.llamar("GET", "/panel", None, ADMIN).status_code, 200)
        self.cambiar_usuario(ADMIN, activo=False)
        self.assertEqual(self.llamar("GET", "/panel", None, ADMIN).status_code, 401)

    # ---- documentacion ----
    def test_openapi_ya_no_pide_ids_de_actor_en_los_cuerpos(self):
        esquemas = self.http.get("/openapi.json").json()["components"]["schemas"]
        for nombre, esquema in esquemas.items():
            campos = set(esquema.get("properties", {}))
            with self.subTest(nombre):
                self.assertFalse(campos & {"supervisor_id", "coordinador_id", "admin_id"})
        self.assertNotIn("cliente_id", esquemas["AceptarCotizacionIn"]["properties"])


if __name__ == "__main__":
    unittest.main()
