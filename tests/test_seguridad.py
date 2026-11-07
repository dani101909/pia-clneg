import os
import unittest
from unittest import mock

from src.infrastructure.seguridad import (ServicioDeTokens, TokenInvalido,
                                          hashearClave, verificarClave)

RAPIDO = 1000                      # pocas iteraciones: solo para que las pruebas corran rapido
SECRETO = "secreto-de-prueba-0123456789"


class ContrasenasTest(unittest.TestCase):
    def test_clave_correcta_se_verifica(self):
        almacenado = hashearClave("Cl4ve!", iteraciones=RAPIDO)
        self.assertTrue(verificarClave("Cl4ve!", almacenado))

    def test_clave_incorrecta_no_se_verifica(self):
        almacenado = hashearClave("Cl4ve!", iteraciones=RAPIDO)
        self.assertFalse(verificarClave("otra", almacenado))

    def test_dos_hashes_de_la_misma_clave_difieren_por_la_sal(self):
        self.assertNotEqual(hashearClave("x1", iteraciones=RAPIDO),
                            hashearClave("x1", iteraciones=RAPIDO))

    def test_no_guarda_la_clave_en_claro(self):
        self.assertNotIn("Cl4ve!", hashearClave("Cl4ve!", iteraciones=RAPIDO))

    def test_clave_vacia_se_rechaza(self):
        with self.assertRaises(ValueError):
            hashearClave("")

    def test_hash_mal_formado_o_de_otro_algoritmo_da_falso_sin_lanzar(self):
        for basura in ("", "abc", "md5$1$a$b", "pbkdf2_sha256$no$a$b", None):
            self.assertFalse(verificarClave("x", basura))

    def test_usa_las_iteraciones_guardadas_en_el_hash(self):
        almacenado = hashearClave("k", iteraciones=RAPIDO)
        self.assertIn(f"${RAPIDO}$", almacenado)
        self.assertTrue(verificarClave("k", almacenado))

    def test_iteraciones_por_defecto_son_altas(self):
        self.assertTrue(hashearClave("k").startswith("pbkdf2_sha256$600000$"))


class TokensTest(unittest.TestCase):
    def setUp(self):
        self.tokens = ServicioDeTokens(SECRETO, vigencia_segundos=60)

    def test_token_emitido_se_verifica(self):
        token = self.tokens.emitir("admin-1", "Administracion", ahora=1000)
        datos = self.tokens.verificar(token, ahora=1010)
        self.assertEqual((datos["sub"], datos["rol"], datos["exp"]),
                         ("admin-1", "Administracion", 1060))

    def test_token_vencido_se_rechaza(self):
        token = self.tokens.emitir("u", "Cliente", ahora=1000)
        with self.assertRaises(TokenInvalido):
            self.tokens.verificar(token, ahora=1060)

    def test_token_con_payload_alterado_se_rechaza(self):
        cuerpo, firma = self.tokens.emitir("cli-1", "Cliente", ahora=1000).split(".")
        falso = self.tokens.emitir("cli-1", "Administracion", ahora=1000).split(".")[0]
        with self.assertRaises(TokenInvalido):
            self.tokens.verificar(f"{falso}.{firma}", ahora=1010)

    def test_token_firmado_con_otro_secreto_se_rechaza(self):
        ajeno = ServicioDeTokens("otro-secreto-0123456789", 60)
        token = ajeno.emitir("u", "Cliente", ahora=1000)
        with self.assertRaises(TokenInvalido):
            self.tokens.verificar(token, ahora=1010)

    def test_tokens_mal_formados_se_rechazan(self):
        for basura in ("", "sin-punto", "a.b.c", None, "....", 123):
            with self.assertRaises(TokenInvalido):
                self.tokens.verificar(basura)

    def test_payload_sin_campos_obligatorios_se_rechaza(self):
        from src.infrastructure.seguridad import _b64
        cuerpo = _b64(b'{"sub":"u"}')
        token = f"{cuerpo}.{self.tokens._firmar(cuerpo)}"      # firma valida, contenido incompleto
        with self.assertRaises(TokenInvalido):
            self.tokens.verificar(token, ahora=1)

    def test_payload_que_no_es_json_se_rechaza(self):
        from src.infrastructure.seguridad import _b64
        cuerpo = _b64(b"no es json")
        token = f"{cuerpo}.{self.tokens._firmar(cuerpo)}"
        with self.assertRaises(TokenInvalido):
            self.tokens.verificar(token, ahora=1)

    def test_usa_el_reloj_real_si_no_se_da_ahora(self):
        token = self.tokens.emitir("u", "Cliente")
        self.assertEqual(self.tokens.verificar(token)["sub"], "u")

    def test_secreto_corto_o_vacio_se_rechaza(self):
        for secreto in ("", "corto", None):
            with self.assertRaises(ValueError):
                ServicioDeTokens(secreto)

    def test_desde_entorno_lee_la_variable(self):
        with mock.patch.dict(os.environ, {"CLEANPRO_SECRET": SECRETO}):
            self.assertIsInstance(ServicioDeTokens.desdeEntorno(), ServicioDeTokens)

    def test_desde_entorno_sin_variable_falla_claramente(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                ServicioDeTokens.desdeEntorno()


if __name__ == "__main__":
    unittest.main()
