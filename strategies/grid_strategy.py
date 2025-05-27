
from strategy_base import StrategyBase

class GridStrategy(StrategyBase):
    def generate_signals(self, data):
        trades = []
        for i in range(1, len(data)):
            if data["close"].iloc[i] < data["close"].iloc[i-1]:
                trades.append({"type": "buy", "time": data.index[i], "price": data["close"].iloc[i]})
            elif data["close"].iloc[i] > data["close"].iloc[i-1]:
                trades.append({"type": "sell", "time": data.index[i], "price": data["close"].iloc[i]})
        return trades
