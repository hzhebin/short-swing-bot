
import streamlit as st
import pandas as pd
import requests
import time
import matplotlib.pyplot as plt

st.set_page_config(page_title="撸短策略自动化回测系统", layout="wide")
st.title("📈 撸短策略自动化回测系统")

st.sidebar.header("策略参数设置")
symbol = st.sidebar.text_input("交易对", value="BTCUSDT")
start_date = st.sidebar.date_input("开始日期", value=pd.to_datetime("2024-04-01"))
end_date = st.sidebar.date_input("结束日期", value=pd.to_datetime("2025-04-30"))
leverage = st.sidebar.slider("杠杆倍数", 1, 50, 10)
position_size = st.sidebar.slider("每次建仓金额($)", 10, 1000, 100, 10)
decay_factor = st.sidebar.slider("衰减因子", 0.1, 1.0, 0.5, 0.1)
fee_rate = st.sidebar.slider("手续费率", 0.0001, 0.01, 0.0005, 0.0001)

def get_binance_kline(symbol, interval='1h', start_date='2024-04-01', end_date='2025-04-30'):
    url = 'https://api.binance.com/api/v3/klines'
    start_ts = int(time.mktime(time.strptime(str(start_date), "%Y-%m-%d")) * 1000)
    end_ts = int(time.mktime(time.strptime(str(end_date), "%Y-%m-%d")) * 1000)
    klines = []
    limit = 1000
    while start_ts < end_ts:
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit,
            'startTime': start_ts,
            'endTime': end_ts
        }
        r = requests.get(url, params=params)
        data = r.json()
        if not isinstance(data, list) or len(data) == 0:
            st.error("❌ 获取 Binance 数据失败：可能是交易对错误、时间区间无效或包含未来日期。")
            return pd.DataFrame()
        klines.extend(data)
        start_ts = data[-1][0] + 1
        time.sleep(0.05)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_base_vol', 'taker_quote_vol', 'ignore'])
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df

if st.button("▶️ 运行策略"):
    with st.spinner("正在下载数据并回测..."):
        df = get_binance_kline(symbol, start_date=start_date, end_date=end_date)
        if df.empty:
            st.warning("⚠️ 数据为空，已终止执行。请检查时间范围或交易对设置。")
            st.stop()

        initial_balance = 10000
        balance = initial_balance
        position = 0
        grid_levels = [0.01, 0.02, 0.03, 0.04]
        weights = [0.36, 0.32, 0.21, 0.09]
        trades = []

        for i in range(1, len(df)):
            cp = df['close'].iloc[i]
            pp = df['close'].iloc[i - 1]
            pct = (cp - pp) / pp

            for j, level in enumerate(grid_levels):
                if pct <= -level:
                    trade_amt = position_size * leverage
                    cost = position_size * (1 + fee_rate)
                    if balance >= cost:
                        balance -= cost
                        position += trade_amt / cp
                        trades.append({'step': i, 'type': 'long', 'price': cp})
                elif pct >= level and position > 0:
                    sell_amt = position * cp
                    proceeds = sell_amt * (1 - fee_rate)
                    balance += proceeds
                    trades.append({'step': i, 'type': 'close', 'price': cp})
                    position = 0

        final_value = balance + position * df['close'].iloc[-1]
        profit = final_value - initial_balance
        days = len(df) / 24
        years = days / 365
        cagr = (final_value / initial_balance) ** (1 / years) - 1 if years > 0 else 0

        explosion = 0
        holding = 0
        for i in range(1, len(df)):
            pct = (df['close'].iloc[i] - df['close'].iloc[i-1]) / df['close'].iloc[i-1]
            if pct <= -0.01:
                holding += 1
            else:
                holding = 0
            if holding >= 10:
                explosion += 1
                holding = 0

        st.success(f"💰 最终账户价值：${final_value:,.2f}")
        st.metric("总盈利", f"${profit:,.2f}")
        st.metric("年化收益率 (CAGR)", f"{cagr * 100:.2f}%")
        st.metric("爆仓风险事件数", explosion)
        st.metric("爆仓频率", f"{(explosion / len(df)) * 100:.4f}%")

        fig, ax = plt.subplots(figsize=(12,5))
        ax.plot(df['close'].values, label='BTC Price')
        for t in trades:
            if t['type'] == 'long':
                ax.scatter(t['step'], t['price'], color='green', marker='^')
            elif t['type'] == 'close':
                ax.scatter(t['step'], t['price'], color='red', marker='v')
        ax.set_title("交易点图")
        ax.set_xlabel("K线步数")
        ax.set_ylabel("价格")
        ax.grid(True)
        st.pyplot(fig)
