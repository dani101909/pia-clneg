"""Exporta la especificacion OpenAPI a docs/api/openapi.json.

Ejecutar desde la raiz del proyecto:  python scripts/exportar_openapi.py
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.api.main import crear_app  # noqa: E402

destino = RAIZ / "docs" / "api" / "openapi.json"
destino.parent.mkdir(parents=True, exist_ok=True)
destino.write_text(json.dumps(crear_app("sqlite:///:memory:").openapi(),
                              indent=2, ensure_ascii=False), encoding="utf-8")
print(f"OpenAPI exportado a {destino}")
