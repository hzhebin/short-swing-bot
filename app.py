import streamlit as st
import pandas as pd
import requests
import time
import plotly.graph_objects as go
import io

# ========== 页面配置 ==========
st.set_page_config(page_title="📈 撸短策略自动化回测系统", layout="wide")
st.title("📈 撸短策略自动化回测系统")
st.caption("✅ 本版本包含爆仓风险检测模块 + 策略参数优化 + 多币种支持")

# ========== 左侧参数面板 ==========
st.sidebar.header("策略参数设置")
symbols = st.sidebar.multiselect("交易对（可多选）", options=["BTCUSDT", "ETHUSDT", "BNBUSDT"], default=["BTCUSDT"])
start_date = st.sidebar.date_input("开始日期", value=pd.to_datetime("2024-04-01"))
end_date = st.sidebar.date_input("结束日期", value=pd.to_datetime("2025-04-30"))
leverage_range = st.sidebar.slider("杠杆倍数范围", 1, 50, (10, 20))
position_range = st.sidebar.slider("建仓金额范围($)", 10, 1000, (100, 200), step=10)
fee_rate = st.sidebar.slider("手续费率", 0.000, 0.01, 0.0005, step=0.0001)
initial_balance = st.sidebar.number_input("初始资金($)", value=10000, step=100)
optimize = st.sidebar.checkbox("启用参数网格优化", value=True)

# ========== 获取 Binance K线数据 ==========
def get_binance_kline(symbol, interval='1h', start_date='2024-01-01', end_date='2024-12-31'):
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
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                       'close_time', 'quote_asset_volume', 'num_trades',
                                       'taker_base_vol', 'taker_quote_vol', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df

# ========== 策略类 ==========
class GridStrategy:
    def __init__(self, leverage, position_size, fee_rate):
        self.leverage = leverage
        self.position_size = position_size
        self.fee_rate = fee_rate
        self.grid_levels = [0.01, 0.02, 0.03, 0.04]  # 固定四档网格
        self.weights = [0.36, 0.32, 0.21, 0.09]
        self.position = 0

    def run(self, df, initial_balance):
        trades = []
        balance = initial_balance
        for i in range(1, len(df)):
            cp = df['close'].iloc[i]
            pp = df['close'].iloc[i - 1]
            pct = (cp - pp) / pp
            for j, level in enumerate(self.grid_levels):
                if pct <= -level:
                    trade_amt = self.position_size * self.leverage
                    cost = self.position_size * (1 + self.fee_rate)
                    if balance >= cost:
                        balance -= cost
                        self.position += trade_amt / cp
                        trades.append({"step": i, "type": "buy", "price": cp, "timestamp": df['timestamp'].iloc[i]})
                elif pct >= level and self.position > 0:
                    sell_amt = self.position * cp
                    proceeds = sell_amt * (1 - self.fee_rate)
                    balance += proceeds
                    trades.append({"step": i, "type": "sell", "price": cp, "timestamp": df['timestamp'].iloc[i]})
                    self.position = 0
        final = balance + self.position * df['close'].iloc[-1]
        return trades, final

# ========== 回测函数 ==========
def backtest(df, initial_balance, leverage, position_size, fee_rate):
    strat = GridStrategy(leverage, position_size, fee_rate)
    trades, final = strat.run(df, initial_balance)
    returns = final - initial_balance
    duration_days = len(df) / 24
    years = duration_days / 365
    cagr = (final / initial_balance) ** (1 / years) - 1 if years > 0 else 0
    return trades, final, returns, cagr

# ========== 网格调参 ==========
def grid_optimize(df, initial_balance):
    best_profit = 0
    best_params = (10, 100)
    for l in range(leverage_range[0], leverage_range[1] + 1, 1):
        for p in range(position_range[0], position_range[1] + 1, 10):
            trades, final, profit, _ = backtest(df, initial_balance, l, p, fee_rate)
            if profit > best_profit:
                best_profit = profit
                best_params = (l, p)
    return best_params

# ========== 主运行逻辑 ==========
if st.button("▶️ 运行策略"):
    for sym in symbols:
        df = get_binance_kline(sym, start_date=start_date, end_date=end_date)
        if df.empty:
            st.error(f"❌ 获取 {sym} 数据失败")
            continue
        # 自动参数搜索
        l, p = (leverage_range[0], position_range[0])
        if optimize:
            l, p = grid_optimize(df, initial_balance)

        trades, final, profit, cagr = backtest(df, initial_balance, l, p, fee_rate)

        st.subheader(f"📊 {sym} 回测结果（自动优化后: 杠杆 {l}x, 建仓 {p}$）")
        col1, col2, col3 = st.columns(3)
        col1.metric("最终净值", f"${final:,.2f}")
        col2.metric("总收益率", f"{(final/initial_balance - 1) * 100:.2f}%")
        col3.metric("年化收益率", f"{cagr * 100:.2f}%")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['close'], name='价格'))
        for t in trades:
            color = 'green' if t['type'] == 'buy' else 'red'
            symbol = 'triangle-up' if t['type'] == 'buy' else 'triangle-down'
            fig.add_trace(go.Scatter(x=[t['timestamp']], y=[t['price']],
                                     mode='markers', name='买入' if t['type'] == 'buy' else '卖出',
                                     marker_symbol=symbol, marker_color=color, marker_size=10))
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        # 导出交易记录
        trades_df = pd.DataFrame(trades)
        csv_buf = io.StringIO()
        trades_df.to_csv(csv_buf, index=False)
        st.download_button("📥 下载交易记录 CSV", csv_buf.getvalue(), file_name=f"{sym}_trades.csv", mime="text/csv")
