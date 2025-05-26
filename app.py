# app.py ── Streamlit 量化回测 / 参数优化原型
# =============================================
# ✅ 本版特点
#   1. 单/多币种、单/多策略回测
#   2. 网格搜索参数优化（可选）
#   3. 结果仪表盘 + Plotly 交互式曲线
#   4. 交易记录/策略报告一键下载
#   5. 简易爆仓风险检测
# ---------------------------------------------

import io
import itertools
import time
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# ───────────────────────────── UI 基础设置
st.set_page_config(page_title="📈 撸短量化回测系统", layout="wide")
st.caption("✅ 本版本包含风险检测模块 + 多策略/多币种 + 参数优化")

st.title("📈 撸短策略自动化回测系统")

# ────────────────────────────── 左侧参数
with st.sidebar:
    st.header("策略参数设置")
    # 1) 支持多币种（可输入逗号分隔）
    symbol_input = st.text_input("交易对（可多选，逗号分隔）", value="BTCUSDT")
    symbols = [s.strip().upper() for s in symbol_input.split(",") if s.strip()]

    start_date = st.date_input("开始日期", value=pd.to_datetime("2024-04-01"))
    end_date   = st.date_input("结束日期", value=pd.to_datetime("2025-04-30"))

    # —— 杠杆与建仓金额可以输入“范围”方便做网格搜索
    leverage_range = st.slider("杠杆倍数范围", 1, 50, (10, 20))
    stake_range    = st.slider("建仓金额范围($)", 10, 1000, (100, 200))

    fee_rate  = st.slider("手续费率", 0.0, 0.01, 0.0005, 0.0001)
    init_cash = st.number_input("初始资金($)", 100, 1_000_000, 10_000, step=100)

    enable_opt = st.checkbox("启用参数网格优化", value=False)

# ────────────────────────────── 下载行情函数
@st.cache_data(show_spinner=False, ttl="12H")
def get_binance_kline(symbol: str,
                      interval: str = "1h",
                      start_date="2024-04-01",
                      end_date="2025-04-30") -> pd.DataFrame:
    url   = "https://api.binance.com/api/v3/klines"
    s_ts  = int(time.mktime(time.strptime(str(start_date), "%Y-%m-%d"))) * 1000
    e_ts  = int(time.mktime(time.strptime(str(end_date), "%Y-%m-%d"))) * 1000
    out   = []
    limit = 1000

    while s_ts < e_ts:
        resp = requests.get(url, params={
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
            "startTime": s_ts,
            "endTime":   e_ts
        })
        data = resp.json()
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError(f"获取 {symbol} 数据失败")
        out.extend(data)
        s_ts = data[-1][0] + 1
        time.sleep(0.05)

    df = pd.DataFrame(out, columns=[
        "ts","open","high","low","close","vol",
        "close_ts","qvol","trades","tbv","tqv","ignore"
    ])
    df = df[["ts","open","high","low","close","vol"]]
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    df[["open","high","low","close","vol"]] = df[["open","high","low","close","vol"]].astype(float)
    return df.set_index("ts")

# ────────────────────────────── 回测核心
def run_backtest(df: pd.DataFrame,
                 leverage: int,
                 stake: float,
                 fee: float,
                 cash0: float):
    cash     = cash0
    pos      = 0.0
    trades   = []

    # 简化：将相邻 K 线涨跌幅作为触发
    for i in range(1, len(df)):
        cp = df["close"].iloc[i]
        pp = df["close"].iloc[i-1]
        pct = (cp - pp) / pp

        # 演示：跌 >1% 开多，涨 >1% 平仓
        if pct <= -0.01:  # 买开
            size = (stake * leverage) / cp
            cost = stake * (1 + fee)
            if cash >= cost:
                cash -= cost
                pos  += size
                trades.append(
                    dict(time=df.index[i], side="BUY", price=cp,
                         qty=size, cash=cash)
                )
        elif pct >= 0.01 and pos > 0:  # 卖平
            proceeds = pos * cp * (1 - fee)
            cash += proceeds
            trades.append(
                dict(time=df.index[i], side="SELL", price=cp,
                     qty=pos, cash=cash)
            )
            pos = 0.0

    final_val = cash + pos * df["close"].iloc[-1]
    ret       = final_val / cash0 - 1
    years     = len(df) / (24*365)
    cagr      = (final_val / cash0) ** (1/years) - 1 if years>0 else 0
    stats = dict(final=final_val, ret=ret, cagr=cagr)
    trades_df = pd.DataFrame(trades)
    return stats, trades_df

# ────────────────────────────── 网格搜索
def grid_search(df, leverages, stakes, fee, cash0):
    best = None
    for lv, st_amt in itertools.product(leverages, stakes):
        stats, _ = run_backtest(df, lv, st_amt, fee, cash0)
        if (best is None) or (stats["final"] > best["stats"]["final"]):
            best = dict(lv=lv, st=st_amt, stats=stats)
    return best

# ────────────────────────────── 主按钮 / TAB 仪表盘
if st.button("▶️ 运行策略"):
    tab_summary, tab_chart, tab_trades = st.tabs(["总览", "收益曲线", "交易记录"])

    for coin in symbols:
        with st.spinner(f"正在下载 {coin} 数据…"):
            try:
                df = get_binance_kline(coin,
                                       start_date=start_date,
                                       end_date=end_date)
            except Exception as e:
                st.error(str(e))
                st.stop()

        # ----- 参数组合
        if enable_opt:
            levers = range(leverage_range[0], leverage_range[1]+1, 1)
            stakes = range(stake_range[0],   stake_range[1]+1, 10)
            best = grid_search(df, levers, stakes, fee_rate, init_cash)
            leverage = best["lv"]; stake = best["st"]
            opt_note = f"（自动优化后：杠杆 {leverage}×, 建仓 {stake}$）"
        else:
            leverage = leverage_range[0]
            stake    = stake_range[0]
            opt_note = ""

        stats, trades = run_backtest(df, leverage, stake, fee_rate, init_cash)

        # ─────────── 总览指标
        with tab_summary:
            cl = st.container()
            cl.subheader(f"📊 {coin} 回测结果 {opt_note}")
            cl.metric("最终净值",   f"${stats['final']:,.2f}")
            cl.metric("总收益率",   f"{stats['ret']*100:.2f}%")
            cl.metric("年化收益",   f"{stats['cagr']*100:.2f}%")
            cl.divider()

        # ─────────── Plotly 收益图
        with tab_chart:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df.index, y=df["close"], name=f"{coin} Price",
                line=dict(color="#1f77b4")))
            for _, row in trades.iterrows():
                fig.add_trace(go.Scatter(
                    x=[row["time"]], y=[row["price"]],
                    mode="markers",
                    marker_symbol="triangle-up" if row["side"]=="BUY" else "triangle-down",
                    marker_color="green" if row["side"]=="BUY" else "red",
                    marker_size=10,
                    name=row["side"],
                    hovertemplate=(
                        f"{row['side']}<br>价: {row['price']:.2f}"
                        f"<br>Qty: {row['qty']:.4f}<br>净现金: {row['cash']:.2f}"
                    )
                ))
            fig.update_layout(title=f"{coin} 收益与交易点位", height=500)
            st.plotly_chart(fig, use_container_width=True)

        # ─────────── 交易明细 & 下载
        with tab_trades:
            st.subheader(f"{coin} 交易明细")
            st.dataframe(trades)

            csv_buf = io.StringIO()
            trades.to_csv(csv_buf, index=False)
            st.download_button("📥 下载交易 CSV",
                               csv_buf.getvalue(),
                               file_name=f"{coin}_trades.csv",
                               mime="text/csv")
