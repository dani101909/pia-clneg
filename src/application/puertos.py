"""Puertos hacia el exterior. La infraestructura los implementa (DIP)."""
from abc import ABC, abstractmethod


class NotificacionPort(ABC):
    @abstractmethod
    def notificar(self, evento): ...


class FacturacionPort(ABC):
    """La facturacion es externa: solo se publica el evento de cierre."""

    @abstractmethod
    def publicar(self, evento): ...
