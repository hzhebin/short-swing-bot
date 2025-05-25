import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go

st.set_page_config(page_title="撸短策略自动化回测系统", layout="wide")
st.caption("✅ 本版本包含爆仓风险检测模块 + 多策略/多币种 + 参数优化")
st.title("📈 撸短策略自动化回测系统")

with st.sidebar:
    st.header("策略参数设置")
    symbols = st.multiselect("交易对（可多选）", ["BTCUSDT", "ETHUSDT", "BNBUSDT"], default=["BTCUSDT"])
    start_date = st.date_input("开始日期", value=pd.to_datetime("2024-04-01"))
    end_date = st.date_input("结束日期", value=pd.to_datetime("2025-04-30"))
    leverage_range = st.slider("杠杆倍数范围", 1, 50, (10, 20))
    position_range = st.slider("建仓金额范围($)", 10, 1000, (100, 200))
    fee_rate = st.slider("手续费率", 0.0000, 0.01, 0.0005, 0.0001)
    optimize = st.checkbox("启用参数网格优化", value=True)
    initial_balance = st.number_input("初始资金($)", value=10000)

def get_binance_kline(symbol, interval='1h', start_date='2024-04-01', end_date='2025-04-30'):
    url = 'https://api.binance.com/api/v3/klines'
    start_ts = int(time.mktime(time.strptime(str(start_date), "%Y-%m-%d")) * 1000)
    end_ts = int(time.mktime(time.strptime(str(end_date), "%Y-%m-%d")) * 1000)
    klines = []
    while start_ts < end_ts:
        params = {'symbol': symbol, 'interval': interval, 'limit': 1000, 'startTime': start_ts, 'endTime': end_ts}
        r = requests.get(url, params=params)
        data = r.json()
        if not isinstance(data, list) or len(data) == 0:
            return pd.DataFrame()
        klines.extend(data)
        start_ts = data[-1][0] + 1
        time.sleep(0.05)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                       'quote_asset_volume', 'num_trades', 'taker_base_vol',
                                       'taker_quote_vol', 'ignore'])
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df

def backtest(df, leverage, position_size, fee_rate, initial_balance):
    balance = initial_balance
    position = 0
    trades = []
    explosion = 0
    holding = 0
    max_drawdown = 0
    peak_value = initial_balance

    for i in range(1, len(df)):
        cp = df['close'].iloc[i]
        pp = df['close'].iloc[i - 1]
        pct = (cp - pp) / pp

        if pct <= -0.01:
            trade_amt = position_size * leverage
            cost = position_size * (1 + fee_rate)
            if balance >= cost:
                balance -= cost
                position += trade_amt / cp
                trades.append({'step': i, 'type': 'buy', 'price': cp})

        elif pct >= 0.01 and position > 0:
            sell_amt = position * cp
            proceeds = sell_amt * (1 - fee_rate)
            balance += proceeds
            trades.append({'step': i, 'type': 'sell', 'price': cp})
            position = 0

        value = balance + position * cp
        if value > peak_value:
            peak_value = value
        dd = (peak_value - value) / peak_value
        if dd > max_drawdown:
            max_drawdown = dd

        if position * cp < initial_balance * 0.1:
            holding += 1
        else:
            holding = 0
        if holding > 10:
            explosion += 1
            holding = 0

    final_value = balance + position * df['close'].iloc[-1]
    return final_value, trades, explosion, max_drawdown

if st.button("▶️ 运行策略"):
    with st.spinner("正在回测..."):
        results = []
        for symbol in symbols:
            df = get_binance_kline(symbol, start_date=start_date, end_date=end_date)
            if df.empty:
                st.error(f"❌ 获取 {symbol} 数据失败")
                continue
            best_result = {}
            for lv in range(leverage_range[0], leverage_range[1]+1):
                for pos in range(position_range[0], position_range[1]+1, 50):
                    final_value, trades, explosion, max_dd = backtest(
                        df, lv, pos, fee_rate, initial_balance
                    )
                    if not best_result or final_value > best_result['final']:
                        best_result = {'symbol': symbol, 'final': final_value, 'trades': trades, 'leverage': lv,
                                       'position': pos, 'explosion': explosion, 'max_dd': max_dd}
            results.append(best_result)

    for res in results:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(f"💰 {res['symbol']} 账户价值", f"${res['final']:,.2f}")
        col2.metric("杠杆倍数", res['leverage'])
        col3.metric("建仓金额", res['position'])
        col4.metric("爆仓次数", res['explosion'])
        st.caption(f"📉 最大回撤：{res['max_dd']*100:.2f}%")

        df = get_binance_kline(res['symbol'], start_date=start_date, end_date=end_date)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['close'], mode='lines', name='价格'))
        for t in res['trades']:
            marker = dict(size=8, symbol='triangle-up' if t['type']=='buy' else 'triangle-down',
                          color='green' if t['type']=='buy' else 'red')
            fig.add_trace(go.Scatter(x=[df['timestamp'].iloc[t['step']]], y=[t['price']],
                                     mode='markers', marker=marker,
                                     name='买入' if t['type']=='buy' else '卖出'))
        fig.update_layout(title=f"📊 {res['symbol']} 交易图", height=500, xaxis_title="时间", yaxis_title="价格")
        st.plotly_chart(fig, use_container_width=True)
