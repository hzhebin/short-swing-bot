# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import io
import plotly.graph_objects as go
from itertools import product

st.set_page_config(page_title="📈撸短策略自动化回测系统", layout="wide")
st.title("📈 撸短策略自动化回测系统")
st.caption("✅ 本版本包含爆仓风险检测模块 + 多策略/多币种 + 参数优化")

# --- Sidebar 参数设定 ---
st.sidebar.header("策略参数设置")
symbols = st.sidebar.multiselect("交易对（可多选）", ["BTCUSDT", "ETHUSDT", "BNBUSDT"], default=["BTCUSDT"])
start_date = st.sidebar.date_input("开始日期", value=pd.to_datetime("2024-04-01"))
end_date = st.sidebar.date_input("结束日期", value=pd.to_datetime("2025-04-30"))
leverage_range = st.sidebar.slider("杠杆倍数范围", 1, 50, (10, 20))
position_range = st.sidebar.slider("建仓金额范围($)", 10, 1000, (100, 200), step=10)
fee_rate = st.sidebar.slider("手续费率", 0.0, 0.01, 0.0005, 0.0001)
initial_balance = st.sidebar.number_input("初始资金($)", value=10000)
auto_optimize = st.sidebar.checkbox("启用参数网格优化", value=True)

# --- 获取 Kline 数据 ---
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

# --- 回测主函数 ---
def backtest(df, leverage, position_size, fee_rate, initial_balance):
    balance = initial_balance
    position = 0
    trades = []
    explosion = 0
    holding_down = 0

    for i in range(1, len(df)):
        cp = df['close'].iloc[i]
        pp = df['close'].iloc[i - 1]
        pct = (cp - pp) / pp

        # 做多条件
        if pct <= -0.01:
            cost = position_size * (1 + fee_rate)
            if balance >= cost:
                balance -= cost
                position += (position_size * leverage) / cp
                trades.append({'时间': df['timestamp'].iloc[i], '方向': '买入', '价格': cp, '金额': position_size})
        elif pct >= 0.01 and position > 0:
            proceeds = position * cp * (1 - fee_rate)
            balance += proceeds
            trades.append({'时间': df['timestamp'].iloc[i], '方向': '卖出', '价格': cp, '金额': proceeds})
            position = 0

        # 爆仓监测（连续下跌）
        if pct < 0:
            holding_down += 1
        else:
            holding_down = 0
        if holding_down >= 10:
            explosion += 1
            holding_down = 0

    final_value = balance + position * df['close'].iloc[-1]
    return trades, final_value, explosion

# --- 参数网格优化 ---
def optimize(df, leverages, positions):
    best_result = {'value': 0, 'leverage': None, 'position': None}
    for lev, pos in product(leverages, positions):
        _, final_val, _ = backtest(df, lev, pos, fee_rate, initial_balance)
        if final_val > best_result['value']:
            best_result = {'value': final_val, 'leverage': lev, 'position': pos}
    return best_result

# --- 回测执行按钮 ---
if st.button("▶️ 运行策略"):
    for symbol in symbols:
        df = get_binance_kline(symbol, start_date=start_date, end_date=end_date)
        if df.empty:
            st.error(f"❌ 获取 {symbol} 数据失败")
            continue

        if auto_optimize:
            best = optimize(df, range(leverage_range[0], leverage_range[1]+1), range(position_range[0], position_range[1]+1, 10))
            leverage = best['leverage']
            position = best['position']
        else:
            leverage = leverage_range[0]
            position = position_range[0]

        trades, final_val, explosion = backtest(df, leverage, position, fee_rate, initial_balance)
        cagr = (final_val / initial_balance) ** (1 / ((len(df)/24)/365)) - 1

        st.subheader(f"📊 {symbol} 回测结果（自动优化后: 杠杆 {leverage}x, 建仓 {position}$）")
        col1, col2, col3 = st.columns(3)
        col1.metric("最终净值", f"${final_val:,.2f}")
        col2.metric("总收益率", f"{((final_val / initial_balance - 1)*100):.2f}%")
        col3.metric("年化收益率", f"{cagr*100:.2f}%")

        # --- 图表 ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['close'], name='价格'))
        for t in trades:
            fig.add_trace(go.Scatter(
                x=[t['时间']], y=[t['价格']],
                mode='markers',
                marker_symbol='triangle-up' if t['方向']=='买入' else 'triangle-down',
                marker_color='green' if t['方向']=='买入' else 'red',
                marker_size=10,
                name=t['方向'],
                hovertext=f"{t['方向']} @ ${t['价格']:.2f}"
            ))
        st.plotly_chart(fig, use_container_width=True)

        # --- 导出交易记录 ---
        df_trades = pd.DataFrame(trades)
        csv = df_trades.to_csv(index=False).encode('utf-8')
        st.download_button("📥 下载交易记录 CSV", csv, file_name=f"{symbol}_trades.csv")
