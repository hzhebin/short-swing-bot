
from strategy_base import StrategyBase

class BreakoutStrategy(StrategyBase):
    def generate_signals(self, data):
        trades = []
        for i in range(1, len(data)):
            if data["close"].iloc[i] > max(data["close"].iloc[max(0,i-5):i]):
                trades.append({"type": "buy", "time": data.index[i], "price": data["close"].iloc[i]})
            elif data["close"].iloc[i] < min(data["close"].iloc[max(0,i-5):i]):
                trades.append({"type": "sell", "time": data.index[i], "price": data["close"].iloc[i]})
        return trades
