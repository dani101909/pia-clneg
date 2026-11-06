"""Unit of Work: define el alcance transaccional de cada caso de uso."""
from abc import ABC, abstractmethod


class UnitOfWork(ABC):
    @abstractmethod
    def commit(self): ...

    @abstractmethod
    def rollback(self): ...
