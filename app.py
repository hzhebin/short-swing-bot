
import streamlit as st
import pandas as pd
import requests
import time
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
from zipfile import ZipFile
from datetime import datetime

st.set_page_config(page_title="策略回测仪表盘", layout="wide")
st.title("📈 撸短策略自动化回测系统")

st.sidebar.header("策略参数设置")
symbols = st.sidebar.multiselect("交易对（可多选）", ["BTCUSDT", "ETHUSDT", "BNBUSDT"], default=["BTCUSDT"])
start_date = st.sidebar.date_input("开始日期", value=pd.to_datetime("2024-04-01"))
end_date = st.sidebar.date_input("结束日期", value=pd.to_datetime("2025-04-30"))
leverage_range = st.sidebar.slider("杠杆倍数范围", 1, 50, (10, 20))
position_range = st.sidebar.slider("建仓金额范围($)", 10, 1000, (100, 200), step=50)
fee_rate = st.sidebar.slider("手续费率", 0.0000, 0.01, 0.0005, step=0.0001)
initial_balance = st.sidebar.number_input("初始资金 ($)", value=10000)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

@st.cache_data
def get_data(symbol, interval="1h", start=None, end=None):
    url = "https://api.binance.com/api/v3/klines"
    start_ts = int(time.mktime(time.strptime(str(start), "%Y-%m-%d")) * 1000)
    end_ts = int(time.mktime(time.strptime(str(end), "%Y-%m-%d")) * 1000)
    all_data = []
    while start_ts < end_ts:
        r = requests.get(url, params={
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ts,
            "endTime": end_ts,
            "limit": 1000
        })
        d = r.json()
        if not isinstance(d, list) or len(d) == 0:
            return pd.DataFrame()
        all_data.extend(d)
        start_ts = d[-1][0] + 1
        time.sleep(0.05)
    df = pd.DataFrame(all_data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_base_vol", "taker_quote_vol", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df[["timestamp", "close"]]

def backtest(df, leverage, position_size, fee_rate, initial_balance):
    balance = initial_balance
    position = 0
    trades = []
    equity_curve = []
    peak = initial_balance
    max_dd = 0

    for i in range(1, len(df)):
        price = df["close"].iloc[i]
        prev = df["close"].iloc[i - 1]
        change = (price - prev) / prev

        if change <= -0.01 and balance >= position_size:
            units = (position_size * leverage) / price
            position += units
            balance -= position_size * (1 + fee_rate)
            trades.append((df["timestamp"].iloc[i], price, "buy"))
        elif change >= 0.01 and position > 0:
            proceeds = position * price * (1 - fee_rate)
            balance += proceeds
            trades.append((df["timestamp"].iloc[i], price, "sell"))
            position = 0

        total = balance + position * price
        peak = max(peak, total)
        dd = (peak - total) / peak
        max_dd = max(max_dd, dd)
        equity_curve.append((df["timestamp"].iloc[i], total))

    final_value = balance + position * df["close"].iloc[-1]
    days = len(df) / 24
    cagr = (final_value / initial_balance) ** (1 / (days / 365)) - 1
    return final_value, trades, cagr, max_dd, equity_curve

if st.button("▶️ 开始回测"):
    for symbol in symbols:
        st.subheader(f"📊 {symbol} 回测结果")
        df = get_data(symbol, start=start_date, end=end_date)
        if df.empty:
            st.error(f"❌ 获取 {symbol} 数据失败")
            continue

        best = {"value": 0}
        result_table = []
        equity_data = []
        best_trades = []

        for lev in range(leverage_range[0], leverage_range[1]+1, 5):
            for pos in range(position_range[0], position_range[1]+1, 50):
                final_value, trades, cagr, max_dd, eq = backtest(df.copy(), lev, pos, fee_rate, initial_balance)
                result_table.append((lev, pos, final_value, cagr, max_dd))
                if final_value > best["value"]:
                    best.update({
                        "value": final_value, "trades": trades, "cagr": cagr,
                        "max_dd": max_dd, "eq": eq, "lev": lev, "pos": pos
                    })
                    equity_data = eq
                    best_trades = trades

        col1, col2, col3 = st.columns(3)
        col1.metric("最终净值", f"${best['value']:,.2f}")
        col2.metric("年化收益率", f"{best['cagr']*100:.2f}%")
        col3.metric("最大回撤", f"{best['max_dd']*100:.2f}%")

        # 图表
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[x[0] for x in equity_data], y=[x[1] for x in equity_data],
                                 mode="lines", name="净值"))
        for t in best_trades:
            color = "green" if t[2] == "buy" else "red"
            symbol_txt = "▲" if t[2] == "buy" else "▼"
            fig.add_trace(go.Scatter(
                x=[t[0]], y=[t[1]], mode="markers+text", text=[symbol_txt],
                marker=dict(color=color, size=10), name=t[2], textposition="top center"
            ))
        fig.update_layout(title=f"{symbol} 策略交易图", height=500, xaxis_title="时间", yaxis_title="价格", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # 结果导出
        result_df = pd.DataFrame(result_table, columns=["杠杆", "建仓金额", "最终净值", "CAGR", "Max DD"])
        st.dataframe(result_df)
        st.download_button("📥 下载回测结果 CSV", result_df.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"{symbol}_results_{timestamp}.csv")

        trade_df = pd.DataFrame(best_trades, columns=["时间", "价格", "类型"])
        st.download_button("📥 下载交易明细 CSV", trade_df.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"{symbol}_trades_{timestamp}.csv")

        equity_df = pd.DataFrame(equity_data, columns=["时间", "账户价值"])
        st.download_button("📥 下载净值曲线 CSV", equity_df.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"{symbol}_equity_{timestamp}.csv")
