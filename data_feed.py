import pandas as pd
from datetime import datetime, timedelta
import numpy as np

class BinanceDataFeed:
    """Fetches data from Binance (or local cache) and provides uniform DataFrame."""

    def __init__(self, symbol: str, interval: str = '10s', start: str = None, end: str = None):
        self.symbol = symbol.upper()
        self.interval = interval
        self.start = pd.to_datetime(start) if start else pd.Timestamp.utcnow() - pd.Timedelta(days=30)
        self.end = pd.to_datetime(end) if end else pd.Timestamp.utcnow()

    def get_data(self) -> pd.DataFrame:
        # NOTE: Offline stub - random walk in absence of API connectivity.
        rng = pd.date_range(self.start, self.end, freq=self.interval)
        price = pd.Series(np.random.lognormal(mean=0, sigma=0.002, size=len(rng))).cumprod() * 30000
        df = pd.DataFrame({'close': price.values}, index=rng)
        return df
