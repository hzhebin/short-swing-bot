import pandas as pd

class BrokerSimulator:
    """Simplified broker with mark‑to‑market equity tracking and fee handling."""
    def __init__(self, initial_capital=10000, fee_pct=0.0004):
        self.cash = initial_capital
        self.position = 0.0
        self.fee_pct = fee_pct
        self.trades = []
        ts0 = pd.Timestamp.utcnow()
        self.equity_curve = pd.Series([initial_capital], index=[ts0])

    def mark_to_market(self, price, ts):
        equity = self.cash + self.position * price
        self.equity_curve.loc[ts] = equity

    def execute(self, side, price, qty, ts):
        cost = price * qty
        fee = cost * self.fee_pct
        if side == 'buy':
            self.cash -= cost + fee
            self.position += qty
        else:
            self.cash += cost - fee
            self.position -= qty
        self.mark_to_market(price, ts)
        self.trades.append({'time': ts, 'side': side, 'qty': qty, 'price': price})
