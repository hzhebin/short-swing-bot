
class BrokerSimulator:
    def __init__(self, initial_capital):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position = 0
        self.trade_log = []

    def execute_trades(self, trades, data):
        for trade in trades:
            if trade["type"] == "buy":
                self.position += 1
                self.cash -= trade["price"]
            elif trade["type"] == "sell" and self.position > 0:
                self.position -= 1
                self.cash += trade["price"]
            self.trade_log.append(trade)
