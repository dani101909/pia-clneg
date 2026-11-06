"""Adaptadores de los puertos. Aqui iria el correo/SMS o el sistema contable."""
from ..application.puertos import FacturacionPort, NotificacionPort


class NotificacionAdapter(NotificacionPort):
    def __init__(self):
        self.enviadas = []

    def notificar(self, evento):
        self.enviadas.append(evento)


class FacturacionEventAdapter(FacturacionPort):
    """Publica ServicioCerradoParaFacturacion; no modela la Factura (fuera de alcance)."""

    def __init__(self):
        self.publicados = []

    def publicar(self, evento):
        self.publicados.append(evento)
