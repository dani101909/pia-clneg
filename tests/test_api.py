"""Pruebas de integracion de la API REST (HTTP -> casos de uso -> SQL).

Requiere fastapi y httpx. Cada prueba usa su propia base SQLite temporal.
"""
import os
import tempfile
import unittest

try:
    from fastapi.testclient import TestClient
    from src.api.main import crear_app
    HAY_FASTAPI = True
except ImportError:                                   # pragma: no cover
    HAY_FASTAPI = False

FECHA = "2026-11-20T08:00:00"


@unittest.skipUnless(HAY_FASTAPI, "fastapi/httpx no instalados")
class ApiTest(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        url = "sqlite:///" + os.path.join(self.carpeta.name, "api.db")
        self.cliente = TestClient(crear_app(url, cargar_demo=True))
        self.cliente.__enter__()                      # ejecuta el arranque (esquema + demo)

    def tearDown(self):
        self.cliente.__exit__(None, None, None)
        self.carpeta.cleanup()

    def post(self, ruta, cuerpo):
        return self.cliente.post(ruta, json=cuerpo)

    def aceptar_y_confirmar(self):
        self.post("/cotizaciones/COT-0001/aceptacion", {"cliente_id": "cli-1", "fecha": FECHA})
        return self.post("/servicios/COT-0001/cuadrilla",
                         {"cuadrilla_id": "cuad-1", "coordinador_id": "coord-1"})

    def test_salud_y_openapi(self):
        self.assertEqual(self.cliente.get("/salud").json(), {"estado": "ok"})
        rutas = self.cliente.get("/openapi.json").json()["paths"]
        self.assertIn("/servicios/{folio}/cierre", rutas)
        self.assertEqual(self.cliente.get("/docs").status_code, 200)

    def test_flujo_completo_hasta_el_cierre(self):
        r = self.post("/cotizaciones/COT-0001/aceptacion",
                      {"cliente_id": "cli-1", "fecha": FECHA})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["servicio"]["estado"], "Programado")
        self.assertEqual(self.post("/servicios/COT-0001/cuadrilla",
                         {"cuadrilla_id": "cuad-1", "coordinador_id": "coord-1"}
                         ).json()["servicio"]["estado"], "CuadrillaConfirmada")
        self.post("/servicios/COT-0001/inicio", {"supervisor_id": "sup-1"})
        self.post("/servicios/COT-0001/termino", {"supervisor_id": "sup-1"})
        cierre = self.post("/servicios/COT-0001/cierre", {"admin_id": "admin-1"})
        self.assertEqual(cierre.status_code, 200)
        self.assertEqual(cierre.json()["servicio"]["estado"], "CerradoParaFacturacion")
        self.assertEqual(cierre.json()["eventos"], ["ServicioCerradoParaFacturacion"])

    def test_emitir_cotizacion_genera_folio_y_responde_201(self):
        r = self.post("/cotizaciones", {
            "cliente_id": "cli-9", "ubicacion": "Monterrey", "superficie": "60",
            "tipo_de_inmueble": "Casa", "frecuencia": "Unica", "extras": [],
            "duracion_horas": "2", "personal": 2, "precio": "800"})
        self.assertEqual(r.status_code, 201)
        folio = r.json()["cotizacion"]["folio"]
        self.assertTrue(folio.startswith("COT-"))
        self.assertEqual(self.cliente.get(f"/cotizaciones/{folio}").status_code, 200)

    def test_panel_y_pagina_principal(self):
        panel = self.cliente.get("/panel").json()
        self.assertEqual(len(panel["cotizaciones"]), 3)
        self.assertEqual(panel["servicios"], [])
        self.aceptar_y_confirmar()
        servicios = self.cliente.get("/panel").json()["servicios"]
        self.assertEqual((servicios[0]["folio"], servicios[0]["estado"]),
                         ("COT-0001", "CuadrillaConfirmada"))
        pagina = self.cliente.get("/")
        self.assertEqual(pagina.status_code, 200)
        self.assertIn("CleanPro", pagina.text)

    def test_404_cuando_no_existe(self):
        r = self.cliente.get("/servicios/NO-EXISTE")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["codigo"], "NO_ENCONTRADO")

    def test_403_si_otro_cliente_intenta_aceptar(self):
        r = self.post("/cotizaciones/COT-0001/aceptacion", {"cliente_id": "cli-2"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["codigo"], "SIN_PERMISO")

    def test_409_cotizacion_ya_aceptada_y_folio_duplicado(self):
        self.post("/cotizaciones/COT-0001/aceptacion", {"cliente_id": "cli-1", "fecha": FECHA})
        r = self.post("/cotizaciones/COT-0001/aceptacion", {"cliente_id": "cli-1"})
        self.assertEqual((r.status_code, r.json()["codigo"]), (409, "COTIZACION_NO_VIGENTE"))
        r = self.post("/cotizaciones", {
            "folio": "COT-0002", "cliente_id": "x", "ubicacion": "x", "superficie": "1",
            "tipo_de_inmueble": "x", "frecuencia": "x", "duracion_horas": "1",
            "personal": 1, "precio": "1"})
        self.assertEqual((r.status_code, r.json()["codigo"]), (409, "FOLIO_DUPLICADO"))

    def test_409_cuadrilla_ocupada_en_la_misma_fecha(self):
        self.aceptar_y_confirmar()
        self.post("/cotizaciones/COT-0002/aceptacion", {"cliente_id": "cli-2", "fecha": FECHA})
        r = self.post("/servicios/COT-0002/cuadrilla",
                      {"cuadrilla_id": "cuad-1", "coordinador_id": "coord-1"})
        self.assertEqual((r.status_code, r.json()["codigo"]), (409, "CUADRILLA_NO_DISPONIBLE"))
        libres = {d["cuadrilla_id"]: d["libre"]
                  for d in self.cliente.get("/disponibilidad?fecha=2026-11-20").json()}
        self.assertEqual(libres, {"cuad-1": False, "cuad-2": True})

    def test_409_cierre_bloqueado_explica_que_falta(self):
        self.aceptar_y_confirmar()
        self.post("/servicios/COT-0001/inicio", {"supervisor_id": "sup-1"})
        self.post("/servicios/COT-0001/incidencias", {
            "tipo": "MaterialEspecial", "descripcion": "Piso delicado", "supervisor_id": "sup-1"})
        self.post("/servicios/COT-0001/termino", {"supervisor_id": "sup-1"})
        r = self.post("/servicios/COT-0001/cierre", {"admin_id": "admin-1"})
        self.assertEqual((r.status_code, r.json()["codigo"]), (409, "CIERRE_BLOQUEADO"))
        self.assertIn("INC-1", r.json()["detalle"][0])
        self.post("/servicios/COT-0001/incidencias/INC-1/revision", {"admin_id": "admin-1"})
        self.assertEqual(self.post("/servicios/COT-0001/cierre",
                                   {"admin_id": "admin-1"}).status_code, 200)

    def test_422_datos_invalidos(self):
        r = self.post("/cotizaciones", {"cliente_id": "x"})          # faltan campos
        self.assertEqual(r.status_code, 422)
        r = self.post("/cotizaciones", {
            "cliente_id": "x", "ubicacion": "x", "superficie": "0",
            "tipo_de_inmueble": "x", "frecuencia": "x", "duracion_horas": "1",
            "personal": 1, "precio": "1"})                           # superficie invalida
        self.assertEqual((r.status_code, r.json()["codigo"]), (422, "DATOS_INCOMPLETOS"))

    def test_extra_en_catalogo_y_fuera_de_catalogo(self):
        self.aceptar_y_confirmar()
        self.post("/servicios/COT-0001/inicio", {"supervisor_id": "sup-1"})
        r = self.post("/servicios/COT-0001/extras",
                      {"descripcion": "Lavado de alfombra", "supervisor_id": "sup-1"})
        self.assertEqual((r.status_code, r.json()["resultado"]), (201, "Aceptado"))
        r = self.post("/servicios/COT-0001/extras",
                      {"descripcion": "Pulido de marmol", "supervisor_id": "sup-1"})
        self.assertEqual(r.json()["resultado"], "Pendiente de confirmacion")
        r = self.post("/servicios/COT-0001/extras/EXT-2/confirmacion",
                      {"coordinador_id": "coord-1"})
        self.assertEqual(r.json()["resultado"], "Confirmado")


if __name__ == "__main__":
    unittest.main()