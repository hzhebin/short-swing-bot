from abc import ABC, abstractmethod

class StrategyBase(ABC):
    """Abstract strategy interface."""

    @abstractmethod
    def generate(self, timestamp, price):
        """Return list of tuples (side, quantity). side in {'buy','sell'}"""
        pass
