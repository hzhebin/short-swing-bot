
import pandas as pd
from broker_simulator import BrokerSimulator
import plotly.graph_objects as go

class BacktestEngine:
    def __init__(self, data, strategy, initial_capital):
        self.data = data
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.simulator = BrokerSimulator(initial_capital)

    def run(self):
        trades = self.strategy.generate_signals(self.data)
        self.simulator.execute_trades(trades, self.data)
        return {
            "trades": pd.DataFrame(self.simulator.trade_log),
            "plot": self._generate_plot(trades)
        }

    def _generate_plot(self, trades):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self.data.index, y=self.data["close"], name="Price"))
        for trade in trades:
            color = "green" if trade["type"] == "buy" else "red"
            fig.add_trace(go.Scatter(x=[trade["time"]], y=[trade["price"]],
                                     mode="markers", marker=dict(color=color, size=10),
                                     name=trade["type"].capitalize()))
        return fig
