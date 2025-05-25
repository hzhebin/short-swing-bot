# app.py — 完整量化回测仪表盘（含爆仓统计 & 全量数据导出）
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="策略回测仪表盘", layout="wide")
st.title("📈 撸短策略自动化回测系统")

# ============== ⬇️ 侧边栏参数 =================
st.sidebar.header("策略参数设置")
symbols = st.sidebar.multiselect("交易对（可多选）", ["BTCUSDT", "ETHUSDT", "BNBUSDT"], default=["BTCUSDT"])
start_date = st.sidebar.date_input("开始日期", value=pd.to_datetime("2024-04-01"))
end_date = st.sidebar.date_input("结束日期", value=pd.to_datetime("2025-04-30"))
leverage_range = st.sidebar.slider("杠杆倍数范围", 1, 50, (10, 20))
position_range = st.sidebar.slider("建仓金额范围($)", 10, 1000, (100, 200), step=50)
fee_rate = st.sidebar.slider("手续费率", 0.0000, 0.01, 0.0005, step=0.0001)
initial_balance = st.sidebar.number_input("初始资金 ($)", value=10000)
explosion_drawdown = st.sidebar.slider("爆仓触发回撤(%)", 10, 90, 50)

# ============== ⬇️ 获取数据 =================
@st.cache_data
def get_data(symbol: str, interval: str = "1h", start=None, end=None):
    url = "https://api.binance.com/api/v3/klines"
    start_ts = int(time.mktime(time.strptime(str(start), "%Y-%m-%d")) * 1000)
    end_ts = int(time.mktime(time.strptime(str(end), "%Y-%m-%d")) * 1000)
    klines = []
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
        klines.extend(d)
        start_ts = d[-1][0] + 1
        time.sleep(0.05)  # 避免触发频控
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_base_vol", "taker_quote_vol", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df[["timestamp", "close"]]

# ============== ⬇️ 回测函数 =================

def backtest(df: pd.DataFrame, leverage: int, pos_size: float, fee: float, init_bal: float, exp_dd: float):
    bal = init_bal
    pos = 0.0
    trades = []
    equity_curve = []
    peak = init_bal
    max_dd = 0
    explosions = 0

    for i in range(1, len(df)):
        price = df["close"].iloc[i]
        prev = df["close"].iloc[i-1]
        pct = (price - prev) / prev

        # 建仓：下跌 1%以上
        if pct <= -0.01 and bal >= pos_size:
            qty = (pos_size * leverage) / price
            pos += qty
            bal -= pos_size * (1 + fee)
            trades.append({"时间": df["timestamp"].iloc[i], "价格": price, "方向": "long", "类型": "buy", "本金": pos_size, "杠杆": leverage, "数量": qty})
        # 平仓：上涨 1%以上
        elif pct >= 0.01 and pos > 0:
            proceeds = pos * price * (1 - fee)
            bal += proceeds
            trades.append({"时间": df["timestamp"].iloc[i], "价格": price, "方向": "long", "类型": "sell", "本金": None, "杠杆": leverage, "数量": pos})
            pos = 0

        total = bal + pos * price
        equity_curve.append({"时间": df["timestamp"].iloc[i], "净值": total})
        peak = max(peak, total)
        dd = (peak - total) / peak
        max_dd = max(max_dd, dd)
        # 爆仓判定：如果回撤大于设定阈值
        if dd >= exp_dd / 100:
            explosions += 1
            pos = 0  # 强平
            bal = total
            peak = bal  # 重置峰值

    final_val = bal + pos * df["close"].iloc[-1]
    duration_years = len(df) / (24 * 365)
    cagr = (final_val / init_bal) ** (1/ duration_years) - 1 if duration_years>0 else 0
    return final_val, cagr, max_dd, explosions, pd.DataFrame(trades), pd.DataFrame(equity_curve)

# ============== ⬇️ 主逻辑 =================
if st.button("▶️ 开始回测"):
    for symbol in symbols:
        st.subheader(f"🔹 {symbol} 回测结果")
        df = get_data(symbol, start=start_date, end=end_date)
        if df.empty:
            st.error(f"获取 {symbol} 数据失败")
            continue

        best = None
        results = []
        for lv in range(leverage_range[0], leverage_range[1]+1, 5):
            for ps in range(position_range[0], position_range[1]+1, 50):
                fin, cagr, mdd, exp, trades_df, equity_df = backtest(df.copy(), lv, ps, fee_rate, initial_balance, explosion_drawdown)
                results.append([lv, ps, fin, cagr, mdd, exp])
                if best is None or fin > best["final_val"]:
                    best = {
                        "lev": lv, "pos": ps, "final_val": fin,
                        "cagr": cagr, "mdd": mdd, "exp": exp,
                        "trades": trades_df, "equity": equity_df
                    }

        # ---- 指标卡片 ----
        k1,k2,k3,k4 = st.columns(4)
        k1.metric("最终净值", f"${best['final_val']:,.2f}")
        k2.metric("年化收益率", f"{best['cagr']*100:.2f}%")
        k3.metric("最大回撤", f"{best['mdd']*100:.2f}%")
        k4.metric("爆仓次数", best['exp'])

        # ---- 交互图表 ----
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=best['equity']['时间'], y=best['equity']['净值'], mode="lines", name="净值"))
        for _, row in best['trades'].iterrows():
            marker = dict(color=('green' if row['类型']=='buy' else 'red'), size=8)
            text = '▲' if row['类型']=='buy' else '▼'
            fig.add_trace(go.Scatter(x=[row['时间']], y=[row['价格']], mode="markers+text", marker=marker, text=[text], name=row['类型'], textposition="top center"))
        fig.update_layout(title=f"{symbol} 策略交易图", height=450, xaxis_title="时间", yaxis_title="价格", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # ---- 结果表格 & 导出 ----
        res_df = pd.DataFrame(results, columns=["杠杆", "建仓金额", "最终净值", "CAGR", "MaxDD", "爆仓次数"])
        st.dataframe(res_df)
        st.download_button("📥 下载回测结果 CSV", res_df.to_csv(index=False).encode('utf-8-sig'), file_name=f"{symbol}_results_{timestamp}.csv")

        # 导出交易明细/净值
        st.download_button("📥 下载交易明细 CSV", best['trades'].to_csv(index=False
