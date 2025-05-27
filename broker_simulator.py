import pandas as pd

class BrokerSimulator:
    """Very simplified broker with market order fills and fee handling."""
    def __init__(self, initial_capital=10000, fee_pct=0.0004):
        self.cash = initial_capital
        self.position = 0.0
        self.fee_pct = fee_pct
        self.trades = []
        self.equity_curve = pd.Series(dtype=float)

    def execute(self, side, price, qty):
        cost = price * qty
        fee = cost * self.fee_pct
        if side == 'buy':
            self.cash -= cost + fee
            self.position += qty
        else:
            self.cash += cost - fee
            self.position -= qty
        equity = self.cash + self.position * price
        ts = pd.Timestamp.utcnow()
        self.equity_curve.loc[ts] = equity
        self.trades.append({'time': ts, 'side': side, 'qty': qty, 'price': price, 'equity': equity})
