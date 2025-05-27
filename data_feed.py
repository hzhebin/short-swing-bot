
import pandas as pd
import numpy as np
import datetime

def get_data(symbol, start_date, end_date):
    # Simulated data loader
    dates = pd.date_range(start=start_date, end=end_date, freq="10S")
    prices = np.cumsum(np.random.randn(len(dates))) + 30000
    df = pd.DataFrame(data={"close": prices}, index=dates)
    return df
