import pandas as pd
import numpy as np

class BinanceDataFeed:
    def __init__(self, symbol='BTCUSDT', interval='10s', start=None, end=None):
        self.symbol = symbol
        self.interval = interval
        self.start = pd.to_datetime(start) if start else pd.Timestamp.utcnow() - pd.Timedelta(days=3)
        self.end = pd.to_datetime(end) if end else pd.Timestamp.utcnow()

    def get_data(self):
        rng = pd.date_range(self.start, self.end, freq=self.interval)
        price = pd.Series(np.random.lognormal(mean=0, sigma=0.002, size=len(rng))).cumprod()*30000
        return pd.DataFrame({'close': price.values}, index=rng)
