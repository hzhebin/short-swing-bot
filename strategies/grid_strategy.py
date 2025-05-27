from strategy_base import StrategyBase

class GridStrategy(StrategyBase):
    def __init__(self, grid_size_pct=0.01, leverage=10, base_qty=1.0):
        self.grid_size = grid_size_pct
        self.leverage = leverage
        self.base_qty = base_qty
        self.last_level = None

    def generate(self, ts, price):
        orders = []
        if self.last_level is None:
            self.last_level = price
            return orders
        diff = (price - self.last_level)/self.last_level
        if diff <= -self.grid_size:
            orders.append(('buy', self.base_qty*self.leverage))
            self.last_level = price
        elif diff >= self.grid_size:
            orders.append(('sell', self.base_qty*self.leverage))
            self.last_level = price
        return orders
