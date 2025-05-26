# data_feed.py
# 拉取 Binance 秒级 aggTrades 并聚合为伪K线（默认10秒）

import requests
import pandas as pd
import time
from datetime import datetime, timedelta

def fetch_agg_trades(symbol: str, start_time: int, end_time: int) -> list:
    url = "https://api.binance.com/api/v3/aggTrades"
    all_trades = []
    last_id = None
    while True:
        params = {
            "symbol": symbol,
            "startTime": start_time,
            "endTime": end_time,
            "limit": 1000
        }
        if last_id:
            params["fromId"] = last_id + 1

        r = requests.get(url, params=params)
        data = r.json()

        if not data or not isinstance(data, list):
            break

        all_trades.extend(data)
        last_id = data[-1]["a"]

        # 超出时间范围或返回数量不足1000说明抓完了
        if len(data) < 1000 or data[-1]["T"] >= end_time:
            break

        time.sleep(0.1)

    return all_trades

def aggregate_to_kline(trades: list, interval_secs: int = 10) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()

    df = pd.DataFrame(trades)
    df["T"] = pd.to_datetime(df["T"], unit="ms")
    df.set_index("T", inplace=True)

    ohlc = df.resample(f"{interval_secs}S").agg({
        "p": ["first", "max", "min", "last"],
        "q": "sum"
    })
    ohlc.columns = ["open", "high", "low", "close", "volume"]
    ohlc.dropna(inplace=True)
    ohlc.reset_index(inplace=True)
    return ohlc

def get_aggregated_kline(symbol: str, start_dt: str, end_dt: str, interval_secs: int = 10) -> pd.DataFrame:
    start_ts = int(datetime.strptime(start_dt, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
    end_ts = int(datetime.strptime(end_dt, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
    all_trades = fetch_agg_trades(symbol, start_ts, end_ts)
    return aggregate_to_kline(all_trades, interval_secs)

# 示例用法：
# df = get_aggregated_kline("BTCUSDT", "2025-04-01 00:00:00", "2025-04-01 00:30:00")
# print(df.head())
