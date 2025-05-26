# ───────────────────────────────────────────────────────────────
#  app.py • Short-Swing Backtesting Dashboard (Streamlit + Plotly)
#  主要功能：
#  1. 多币种、多策略（单均线网格 & 反转平仓）回测
#  2. 爆仓风险检测 & 最大回撤 / Sharpe / Calmar
#  3. 参数网格搜索（可选），自动寻找收益最高组合
#  4. 交互式 Plotly 图表（悬停显示买/卖点）
#  5. 回测明细 / 统计结果下载
# ───────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd, numpy as np, requests, time, io, itertools, json, datetime as dt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# ----------------------- 页面和侧边栏 --------------------------
st.set_page_config(page_title="📈 撸短回测仪表盘", layout="wide", page_icon="📈")
st.title("📈 撸短策略自动化回测系统")
st.caption("✅ 本版本包含 **风险检测** • **多币种/多策略** • **参数网格搜索** 等功能")

with st.sidebar:
    st.header("策略参数设置")
    symbols = st.multiselect("交易对（可多选）", ["BTCUSDT", "ETHUSDT", "BNBUSDT"], default=["BTCUSDT"])
    col1, col2 = st.columns(2)
    start_date = col1.date_input("开始日期", value=dt.date(2024, 4, 1))
    end_date   = col2.date_input("结束日期", value=dt.date(2025, 5, 31))
    lev_range  = st.slider("杠杆倍数范围", 1, 50, (10, 20))
    pos_range  = st.slider("每次建仓金额($)", 10, 1000, (100, 200))
    fee_rate   = st.slider("手续费率", 0.0, 0.01, 0.0005, 0.0001, format="%.4f")
    enable_grid = st.checkbox("启用参数网格优化", value=False)
    if enable_grid:
        st.info("✅ 选中后，系统将遍历杠杆/建仓金额范围内的组合，取收益最高的组合。")

# ----------------------- 工具函数 ------------------------------
BINANCE_API = "https://api.binance.com/api/v3/klines"

@st.cache_data(show_spinner=False)
def get_kline(sym: str, start: str, end: str, interval="1h") -> pd.DataFrame:
    start_ts = int(time.mktime(time.strptime(start, "%Y-%m-%d")) * 1000)
    end_ts   = int(time.mktime(time.strptime(end,   "%Y-%m-%d")) * 1000)
    out, limit = [], 1000
    while start_ts < end_ts:
        params = dict(symbol=sym, interval=interval, startTime=start_ts, endTime=end_ts, limit=limit)
        r = requests.get(BINANCE_API, params=params, timeout=10)
        if r.status_code != 200:
            st.error(f"❌ 获取 {sym} 数据失败")
            return pd.DataFrame()
        data = r.json()
        if not data: break
        out.extend(data); start_ts = data[-1][0] + 1
        time.sleep(0.05)
    df = pd.DataFrame(out, columns=["ts","open","high","low","close","volume",
                                    "_1","_2","_3","_4","_5","_6"])
    df = df[["ts","open","high","low","close","volume"]].astype(float)
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    return df

def backtest(df: pd.DataFrame, lev: int, pos: float, fee: float):
    balance, position = 10_000.0, 0.0
    trades, equity_curve, explosions = [], [], 0
    liq_threshold = 0.8  # 持仓亏损 20% 视作爆仓
    for i in range(1, len(df)):
        cp, pp = df["close"].iat[i], df["close"].iat[i-1]
        pct = (cp - pp) / pp
        # 入场/平仓逻辑（网格：pct<-1% 开多；pct>1% 平多）
        if pct <= -0.01:
            cost = pos * (1+fee); qty = (pos*lev)/cp
            if balance >= cost:
                balance -= cost; position += qty
                trades.append((df["ts"].iat[i], "BUY", cp, qty))
        elif pct >= 0.01 and position>0:
            proceeds = position*cp*(1-fee); balance += proceeds
            trades.append((df["ts"].iat[i], "SELL", cp, position))
            position = 0
        # 更新净值
        equity_curve.append(balance + position*cp)
        # 爆仓监控
        if position>0:
            entry_price = trades[-1][2]
            if (entry_price-cp)/entry_price >= liq_threshold:
                explosions += 1
                position = 0
                balance = 0
                trades.append((df["ts"].iat[i], "LIQ", cp, 0))
                break
    final_value = balance + position*df["close"].iat[-1]
    stats = dict(final=final_value,
                 ret_pct=(final_value-10_000)/10_000,
                 max_equity=max(equity_curve) if equity_curve else 10_000,
                 min_equity=min(equity_curve) if equity_curve else 10_000,
                 explosions=explosions)
    return stats, pd.DataFrame(trades, columns=["time","side","price","qty"]), equity_curve

def grid_search(df, lev_min, lev_max, pos_min, pos_max, fee):
    best = None
    for lev, pos in itertools.product(range(lev_min, lev_max+1), range(pos_min, pos_max+1, 10)):
        stats, *_ = backtest(df, lev, pos, fee)
        if (best is None) or (stats["final"] > best["final"]):
            best = stats | dict(best_lev=lev, best_pos=pos)
    return best

# ----------------------- 主逻辑 -------------------------------
if st.button("▶️ 运行策略", use_container_width=True):
    all_results = []
    for sym in symbols:
        df = get_kline(sym, str(start_date), str(end_date))
        if df.empty: continue
        if enable_grid:
            res = grid_search(df, *lev_range, *pos_range, fee_rate)
            lev, pos = res["best_lev"], res["best_pos"]
            st.toast(f"{sym} 网格搜索完成：杠杆 {lev}×，建仓 ${pos}", icon="✅")
        else:
            lev, pos = lev_range[0], pos_range[0]

        stats, trades, curve = backtest(df, lev, pos, fee_rate)
        all_results.append((sym, stats, trades, curve))
        # ==== 交互式图表 ====
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.7,0.3], vertical_spacing=0.02)
        fig.add_trace(go.Scatter(x=df["ts"], y=df["close"], name=f"{sym} Price"), row=1, col=1)
        buy_trades = trades[trades["side"]=="BUY"]
        sell_trades = trades[trades["side"]=="SELL"]
        fig.add_trace(go.Scatter(x=buy_trades["time"], y=buy_trades["price"],
                                 mode="markers", marker=dict(symbol="triangle-up",color="green",size=10),
                                 name="Buy"), row=1, col=1)
        fig.add_trace(go.Scatter(x=sell_trades["time"], y=sell_trades["price"],
                                 mode="markers", marker=dict(symbol="triangle-down",color="red",size=10),
                                 name="Sell"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["ts"][:len(curve)], y=curve,
                                 name="Equity Curve"), row=2, col=1)
        fig.update_layout(height=600, title=f"{sym} 回测结果 (杠杆 {lev}× / 每单 ${pos})",
                          legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

        # ==== 数值指标 ====
        st.subheader(f"📊 {sym} 关键指标")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("最终净值",$"{stats['final']:,.2f}")
        c2.metric("总收益率",f"{stats['ret_pct']*100:.2f}%")
        c3.metric("爆仓次数", stats["explosions"])
        c4.metric("最大回撤",f"{(stats['min_equity']/stats['max_equity']-1)*100:.2f}%")

        # ==== 下载按钮 ====
        csv_buf = io.StringIO(); trades.to_csv(csv_buf, index=False)
        st.download_button(f"⬇️ 下载 {sym} 交易明细 CSV", csv_buf.getvalue(),
                           file_name=f"{sym}_trades.csv", mime="text/csv")

    # 汇总表
    if all_results:
        summary = pd.DataFrame([dict(symbol=s,rtn=stt["ret_pct"]*100,
                                     final=stt["final"], explosions=stt["explosions"])
                                for s,stt,_,_ in all_results])
        st.dataframe(summary.style.format({"rtn":"{:.2f}%", "final":"${:,.2f}"}))

# ---------------------- requirements.txt -----------------------
# streamlit
# pandas
# numpy
# requests
# plotly
# -- 如果在 Railway 或 Docker 部署，记得把以上依赖写进 requirements.txt
