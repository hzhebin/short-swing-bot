import math
from strategy_base import StrategyBase

class GridStrategy(StrategyBase):
    """Weighted grid strategy inspired by provided volatility weights."""

    def __init__(self, grid_size_pct=0.01, leverage=10, decay=0.5, base_qty=1.0):
        self.grid_size = grid_size_pct
        self.leverage = leverage
        self.decay = decay
        self.base_qty = base_qty
        self.last_level = None

    def _weights(self):
        raw = [0.36,0.32,0.21,0.09] + [0]*6
        s = sum(raw)
        return [w/s for w in raw]

    def generate(self, ts, price):
        """Simple grid: buy when price drops by grid_size from last level, sell on rise."""
        orders = []
        if self.last_level is None:
            self.last_level = price
            return orders

        diff = (price - self.last_level) / self.last_level
        if diff <= -self.grid_size:
            # price dropped -> buy
            qty = self.base_qty * self.leverage
            orders.append(('buy', qty))
            self.last_level = price
        elif diff >= self.grid_size:
            # price rose -> sell
            qty = self.base_qty * self.leverage
            orders.append(('sell', qty))
            self.last_level = price
        return orders
