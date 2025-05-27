from abc import ABC, abstractmethod

class StrategyBase(ABC):
    @abstractmethod
    def generate(self, timestamp, price):
        pass
