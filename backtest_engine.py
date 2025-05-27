import pandas as pd
from broker_simulator import BrokerSimulator

class BacktestEngine:
    """Core engine orchestrating strategy signals, broker execution and equity tracking."""

    def __init__(self, price_df: pd.DataFrame, strategy, initial_capital: float = 10000,
                 fee_pct: float = 0.0004):
        self.price_df = price_df
        self.strategy = strategy
        self.broker = BrokerSimulator(initial_capital=initial_capital, fee_pct=fee_pct)

    def run(self):
        """Iterate over price dataframe, feed to strategy, execute orders."""
        for ts, row in self.price_df.iterrows():
            price = row['close']
            orders = self.strategy.generate(ts, price)
            for side, qty in orders:
                self.broker.execute(side, price, qty)
        trades = self.broker.trades
        equity = self.broker.equity_curve
        return trades, equity
