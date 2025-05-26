# 📈 撸短策略自动化回测系统 - 升级版（含爆仓检测 + 盈利提款机制）

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import io
import plotly.graph_objects as go

# ---------------------- 页面配置 ----------------------
st.set_page_config(page_title="撸短策略自动化回测系统", layout="wide")
st.caption("✅ 本版本包含爆仓风险检测模块 + 多币种 + 参数优化")
st.title("📈 撸短策略自动化回测系统")

# ---------------------- 参数输入 ----------------------
st.sidebar.header("策略参数设置")
symbols = st.sidebar.multiselect("交易对（可多选）", ["BTCUSDT", "ETHUSDT", "BNBUSDT"], default=["BTCUSDT"])
start_date = st.sidebar.date_input("开始日期", value=pd.to_datetime("2024-04-01"))
end_date = st.sidebar.date_input("结束日期", value=pd.to_datetime("2025-04-30"))
leverage_range = st.sidebar.slider("杠杆倍数范围", 1, 50, (10, 20))
position_range = st.sidebar.slider("建仓金额范围($)", 10, 1000, (100, 200))
fee_rate = st.sidebar.slider("手续费率", 0.0, 0.01, 0.0005, 0.0001)
initial_balance = st.sidebar.number_input("初始资金($)", value=10000)
use_optimization = st.sidebar.checkbox("启用参数网格优化", value=True)

# ---------------------- 功能函数：获取K线数据 ----------------------
def get_binance_kline(symbol, interval='1h', start_date='2024-04-01', end_date='2025-04-30'):
    url = 'https://api.binance.com/api/v3/klines'
    start_ts = int(time.mktime(time.strptime(str(start_date), "%Y-%m-%d")) * 1000)
    end_ts = int(time.mktime(time.strptime(str(end_date), "%Y-%m-%d")) * 1000)
    klines = []
    while start_ts < end_ts:
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': 1000,
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
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                       'close_time', 'quote_asset_volume', 'num_trades',
                                       'taker_base_vol', 'taker_quote_vol', 'ignore'])
    df = df[['timestamp', 'open', 'high', 'low', 'close']]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
    return df

# ---------------------- 回测核心函数 ----------------------
def backtest(df, leverage, position_size, fee, init_balance, auto_take_profit=True, take_profit_pct=0.5):
    balance = init_balance
    position = 0
    trades = []
    explosion = 0
    equity_curve = []

    for i in range(1, len(df)):
        cp = df['close'].iloc[i]
        pp = df['close'].iloc[i - 1]
        pct = (cp - pp) / pp

        # 模拟爆仓逻辑（10根K线下跌幅超过20%）
        if i >= 10:
            recent_drops = df['close'].iloc[i-10:i].pct_change().fillna(0)
            if recent_drops.sum() < -0.2:
                explosion += 1
                balance = 0
                break

        # 模拟买入
        if pct <= -0.02 and balance > position_size:
            cost = position_size * (1 + fee)
            quantity = (position_size * leverage) / cp
            position += quantity
            balance -= cost
            trades.append({'type': 'buy', 'price': cp, 'step': i})

        # 模拟卖出（达到止盈）
        if pct >= 0.02 and position > 0:
            sell_amt = position * cp
            proceeds = sell_amt * (1 - fee)
            position = 0
            balance += proceeds
            trades.append({'type': 'sell', 'price': cp, 'step': i})

        # 盈利 50% 自动提款
        if auto_take_profit and balance > init_balance * (1 + take_profit_pct):
            st.info(f"💰 盈利超过 {take_profit_pct * 100:.0f}%，提款保护收益")
            balance = init_balance

        equity_curve.append(balance + position * cp)

    final = balance + position * df['close'].iloc[-1]
    total_return = (final / init_balance - 1) * 100
    years = len(df) / (365 * 24)
    cagr = ((final / init_balance) ** (1 / years) - 1) * 100 if years > 0 else 0

    return {
        'final': final,
        'total_return': total_return,
        'cagr': cagr,
        'explosions': explosion,
        'trades': trades,
        'equity_curve': equity_curve
    }

# ---------------------- 回测按钮 ----------------------
if st.button("▶️ 运行策略"):
    for symbol in symbols:
        df = get_binance_kline(symbol, start_date=start_date, end_date=end_date)
        if df.empty:
            st.error(f"❌ 获取 {symbol} 数据失败")
            continue

        if use_optimization:
            best_result = None
            for lv in range(leverage_range[0], leverage_range[1]+1):
                for ps in range(position_range[0], position_range[1]+1, 50):
                    result = backtest(df, lv, ps, fee_rate, initial_balance)
                    if not best_result or result['final'] > best_result['final']:
                        best_result = result
                        best_lv, best_ps = lv, ps
            stats = best_result
            opt_msg = f"（自动优化后: 杠杆 {best_lv}x, 建仓 {best_ps}$）"
        else:
            stats = backtest(df, leverage_range[0], position_range[0], fee_rate, initial_balance)
            opt_msg = ""

        st.subheader(f"📊 {symbol} 回测结果 {opt_msg}")
        col1, col2, col3 = st.columns(3)
        col1.metric("最终净值", f"${stats['final']:,.2f}")
        col2.metric("总收益率", f"{stats['total_return']:.2f}%")
        col3.metric("年化收益率", f"{stats['cagr']:.2f}%")

        # Plotly 画图
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=stats['equity_curve'], mode='lines', name='净值曲线'))
        for t in stats['trades']:
            fig.add_trace(go.Scatter(x=[t['step']], y=[t['price']],
                                     mode='markers',
                                     marker=dict(color='green' if t['type']=='buy' else 'red', size=8),
                                     name='买入' if t['type']=='buy' else '卖出'))
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # 下载交易数据
        trades_df = pd.DataFrame(stats['trades'])
        csv_buf = io.StringIO()
        trades_df.to_csv(csv_buf, index=False)
        st.download_button("📥 下载交易记录 CSV", csv_buf.getvalue(), file_name=f"{symbol}_trades.csv", mime="text/csv")
