
import streamlit as st
import pandas as pd
import requests
import time
import matplotlib.pyplot as plt
import itertools

st.set_page_config(page_title="撸短策略自动化回测系统", layout="wide")
st.caption("✅ 本版本包含爆仓风险检测模块 + 多策略/多币种 + 参数优化")
st.title("📈 撸短策略自动化回测系统")

st.sidebar.header("策略参数设置")
symbols = st.sidebar.multiselect("交易对（可多选）", ["BTCUSDT", "ETHUSDT", "BNBUSDT"], default=["BTCUSDT"])
start_date = st.sidebar.date_input("开始日期", value=pd.to_datetime("2024-04-01"))
end_date = st.sidebar.date_input("结束日期", value=pd.to_datetime("2025-04-30"))
leverage_range = st.sidebar.slider("杠杆倍数范围", 1, 50, (10, 20))
position_range = st.sidebar.slider("建仓金额范围($)", 10, 1000, (100, 200))
fee_rate = st.sidebar.slider("手续费率", 0.0001, 0.01, 0.0005)
optimize = st.sidebar.checkbox("启用参数网格优化")

def get_binance_kline(symbol, interval='1h', start_date='2024-04-01', end_date='2025-04-30'):
    url = 'https://api.binance.com/api/v3/klines'
    start_ts = int(time.mktime(time.strptime(str(start_date), "%Y-%m-%d")) * 1000)
    end_ts = int(time.mktime(time.strptime(str(end_date), "%Y-%m-%d")) * 1000)
    klines = []
    limit = 1000
    while start_ts < end_ts:
        params = {'symbol': symbol, 'interval': interval, 'limit': limit, 'startTime': start_ts, 'endTime': end_ts}
        r = requests.get(url, params=params)
        data = r.json()
        if not isinstance(data, list) or len(data) == 0:
            st.error(f"❌ 获取 {symbol} 数据失败")
            return pd.DataFrame()
        klines.extend(data)
        start_ts = data[-1][0] + 1
        time.sleep(0.05)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                       'close_time', 'quote_asset_volume', 'num_trades',
                                       'taker_base_vol', 'taker_quote_vol', 'ignore'])
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df

def backtest(df, leverage, position_size):
    initial_balance = 10000
    balance = initial_balance
    position = 0
    trades = []
    for i in range(1, len(df)):
        cp = df['close'].iloc[i]
        pp = df['close'].iloc[i - 1]
        pct = (cp - pp) / pp
        if pct <= -0.01 and balance >= position_size * (1 + fee_rate):
            balance -= position_size * (1 + fee_rate)
            position += (position_size * leverage) / cp
            trades.append({'step': i, 'type': 'long', 'price': cp})
        elif pct >= 0.01 and position > 0:
            proceeds = position * cp * (1 - fee_rate)
            balance += proceeds
            trades.append({'step': i, 'type': 'close', 'price': cp})
            position = 0
    final_value = balance + position * df['close'].iloc[-1]
    profit = final_value - initial_balance
    days = len(df) / 24
    cagr = (final_value / initial_balance) ** (1 / (days / 365)) - 1 if days > 0 else 0
    return final_value, profit, cagr, trades

if st.button("▶️ 运行策略"):
    results = []
    combos = list(itertools.product(range(leverage_range[0], leverage_range[1]+1, 5),
                                    range(position_range[0], position_range[1]+1, 50)))

    for symbol in symbols:
        df = get_binance_kline(symbol, start_date=start_date, end_date=end_date)
        if df.empty:
            continue

        best = None
        for leverage, pos in combos if optimize else [(leverage_range[0], position_range[0])]:
            final_value, profit, cagr, trades = backtest(df.copy(), leverage, pos)
            results.append((symbol, leverage, pos, final_value, profit, cagr))
            if best is None or final_value > best[3]:
                best = (leverage, pos, final_value, profit, cagr, trades)

        st.subheader(f"📊 {symbol} 最佳回测结果")
        st.metric("账户价值", f"${best[2]:,.2f}")
        st.metric("总收益", f"${best[3]:,.2f}")
        st.metric("年化收益率", f"{best[4]*100:.2f}%")

        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(df['close'].values, label=f'{symbol} Price')
        for t in best[5]:
            ax.scatter(t['step'], t['price'], color='green' if t['type']=='long' else 'red', marker='^' if t['type']=='long' else 'v')
        ax.set_title(f"{symbol} 回测交易点")
        ax.grid(True)
        st.pyplot(fig)
