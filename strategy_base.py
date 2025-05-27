
class StrategyBase:
    def generate_signals(self, data):
        raise NotImplementedError("Must implement generate_signals")
