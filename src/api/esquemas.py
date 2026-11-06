"""Esquemas de entrada (Pydantic) y vistas de salida de la API.

Las vistas son diccionarios simples: la API no expone los Aggregates tal cual.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from ..domain.servicio import TipoDeIncidencia


class EmitirCotizacionIn(BaseModel):
    folio: Optional[str] = Field(None, description="Si se omite, la API genera uno (COT-XXXXXXXX)")
    cliente_id: str
    ubicacion: str
    superficie: Decimal = Field(description="Unidad de superficie por definir (U2)")
    tipo_de_inmueble: str
    frecuencia: str
    extras: List[str] = Field(default_factory=list, description="Lista vacia = sin extras")
    duracion_horas: Decimal = Field(description="Duracion estimada")
    personal: int
    precio: Decimal = Field(description="Moneda por definir (U2)")


class AceptarCotizacionIn(BaseModel):
    cliente_id: str
    fecha: Optional[datetime] = Field(None, description="Fecha y hora del servicio")


class ConfirmarCuadrillaIn(BaseModel):
    cuadrilla_id: str
    coordinador_id: str


class ReportarAusenciaIn(BaseModel):
    empleado_id: str
    supervisor_id: str


class ReasignarPersonalIn(BaseModel):
    empleado_id: str
    sustituto_id: Optional[str] = Field(None, description="null = no hay reemplazo (servicio en riesgo)")
    admin_id: str


class RegistrarExtraIn(BaseModel):
    descripcion: str
    supervisor_id: str


class ConfirmarExtraIn(BaseModel):
    coordinador_id: str


class RegistrarInicioIn(BaseModel):
    supervisor_id: str
    momento: Optional[datetime] = None


class RegistrarTerminoIn(BaseModel):
    supervisor_id: str
    momento: Optional[datetime] = None


class DocumentarIncidenciaIn(BaseModel):
    tipo: TipoDeIncidencia
    descripcion: str
    supervisor_id: str
    empleado_id: Optional[str] = None


class RevisarIncidenciaIn(BaseModel):
    admin_id: str


class CerrarParaFacturacionIn(BaseModel):
    admin_id: str


class ErrorOut(BaseModel):
    codigo: str
    detalle: Any = ""


def _iso(valor):
    return valor.isoformat() if valor is not None else None


def vistaCotizacion(c) -> dict:
    return {
        "folio": c.folio.valor, "cliente_id": c.cliente_id, "estado": c.estado.value,
        "ubicacion": c.datos.ubicacion, "superficie": str(c.datos.superficie),
        "tipo_de_inmueble": c.datos.tipo_de_inmueble, "frecuencia": c.frecuencia.valor,
        "extras": list(c.extras),
        "estimacion": {"duracion_horas": c.estimacion.duracion.total_seconds() / 3600,
                       "personal": c.estimacion.personal,
                       "precio": str(c.estimacion.precio.monto)}}


def vistaServicio(s) -> dict:
    return {
        "folio": s.folio.valor, "estado": s.estado.value,
        "fecha": _iso(s.fecha.fecha_hora) if s.fecha else None,
        "cuadrilla_id": s.cuadrilla_id,
        "inicio": _iso(s.tiempo.inicio), "termino": _iso(s.tiempo.termino),
        "acciones_disponibles": [d.value for d in s.accionesDisponibles],
        "pendientes_por_documentar": s.pendientesPorDocumentar(),
        "incidencias": [{"id": i.id, "tipo": i.tipo.value, "descripcion": i.descripcion,
                         "hora": _iso(i.hora), "reportada_por": i.reportada_por,
                         "empleado_id": i.empleado_id, "estado": i.estado.value}
                        for i in s.incidencias],
        "extras": [{"id": e.id, "descripcion": e.descripcion,
                    "solicitado_por": e.solicitado_por, "estado": e.estado.value}
                   for e in s.extras],
        "asignaciones": [{"empleado_original": a.empleado_original,
                          "sustituto": a.sustituto, "realizada_por": a.realizada_por,
                          "cuando": _iso(a.cuando), "motivo": a.motivo.texto}
                         for a in s.asignaciones],
        "historial": [{"quien": h.quien, "cuando": _iso(h.cuando), "que": h.que,
                       "motivo": h.motivo} for h in s.historial]}
