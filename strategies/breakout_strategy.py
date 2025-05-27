import collections
from strategy_base import StrategyBase

class BreakoutStrategy(StrategyBase):
    """Simple breakout: buy when price > max(window) * (1+threshold), sell on reverse."""

    def __init__(self, window=50, threshold_pct=0.01, qty=1.0):
        self.window = window
        self.threshold = threshold_pct
        self.prices = collections.deque(maxlen=window)
        self.in_position = False
        self.qty = qty

    def generate(self, ts, price):
        orders = []
        self.prices.append(price)

        if len(self.prices) < self.window:
            return orders

        high = max(self.prices)
        low = min(self.prices)

        if not self.in_position and price >= high * (1 + self.threshold):
            orders.append(('buy', self.qty))
            self.in_position = True
        elif self.in_position and price <= low * (1 - self.threshold):
            orders.append(('sell', self.qty))
            self.in_position = False
        return orders
