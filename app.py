# app.py — Streamlit + Optuna Auto‑Optimization
"""
点击“🧠 自动优化”按钮后，系统自动搜索参数组合（Optuna TPE），
输出最佳策略并展示图表 / CSV；同时保留“▶️ 手动回测”按钮。
"""

from __future__ import annotations
import streamlit as st, pandas as pd, numpy as np, requests, time, plotly.graph_objects as go
from datetime import datetime
import vectorbt as vbt, optuna

# ─── Sidebar UI ──────────────────────────────────────────────────────────
st.set_page_config(page_title="Auto‑Opt Backtest", layout="wide")
st.title("📈 Advanced Quant Backtest w/ Auto‑Opt")

sb = st.sidebar
sb.header("参数面板")
symbol   = sb.selectbox("交易对", ["BTCUSDT","ETHUSDT","BNBUSDT"], index=0)
start_dt = sb.date_input("开始日期", pd.to_datetime("2024-04-01"))
end_dt   = sb.date_input("结束日期", pd.to_datetime("2025-04-30"))
init_bal = sb.number_input("初始资金($)", 1000, 1_000_000, 10_000, 1000)

# 搜索空间范围
lev_min,lev_max = sb.slider("杠杆范围", 1,50,(5,20))
long_min,long_max = sb.slider("做多阈值%范围",0.5,5.0,(0.5,2.0),0.1)
short_min,short_max = sb.slider("做空阈值%范围",0.5,5.0,(0.5,2.0),0.1)
trial_num = sb.slider("优化试验次数",10,200,50,10)

# 固定参数
tp_pct  = sb.slider("止盈%",0.5,10.0,2.0,0.1)/100
sl_pct  = sb.slider("止损%",0.5,10.0,3.0,0.1)/100
slip_pct= sb.slider("滑点‰",0.0,5.0,1.0,0.1)/1000

# ─── 数据获取 ───────────────────────────────────────────────────────────
@st.cache_data
def fetch_price(sym:str,start,end):
    url="https://api.binance.com/api/v3/klines"
    s=int(time.mktime(time.strptime(str(start),"%Y-%m-%d"))*1000)
    e=int(time.mktime(time.strptime(str(end),"%Y-%m-%d"))*1000)
    kl=[]
    while s<e:
        r=requests.get(url,params={"symbol":sym,"interval":"1h","startTime":s,"endTime":e,"limit":1000})
        d=r.json();
        if not isinstance(d,list) or not d: break
        kl+=d; s=d[-1][0]+1; time.sleep(0.04)
    df=pd.DataFrame(kl,columns=["ts","o","h","l","c","v","ct","q","n","tb","tq","ig"])
    df["ts"]=pd.to_datetime(df["ts"],unit="ms")
    return df.set_index("ts")["c"].astype(float)

price_series = fetch_price(symbol,start_dt,end_dt)
if price_series.empty:
    st.error("数据下载失败，无法继续。"); st.stop()

# ─── 回测函数（vectorbt） ────────────────────────────────────────────

def run_backtest(price, lev, long_th, short_th):
    pct = price.pct_change()
    e_long  = pct<=-long_th
    x_long  = pct>= long_th
    e_short = pct>= short_th
    x_short = pct<=-short_th
    pf = vbt.Portfolio.from_signals(price,
        e_long|e_short, x_long|x_short,
        short_entries=e_short,
        fees=0.0005, slippage=slip_pct,
        init_cash=init_bal,
        size=np.where(e_long|e_short, lev, np.nan)
    )
    equity = pf.value
    final  = equity.iloc[-1]
    mdd    = pf.max_drawdown
    years  = len(price)/(24*365)
    cagr   = (final/init_bal)**(1/years)-1 if years>0 else 0
    return final,cagr,mdd,pf,trades_df(pf)

def trades_df(pf):
    rec = pf.trades.records_readable
    return rec if isinstance(rec,pd.DataFrame) else pd.DataFrame(rec)

# ─── 自动优化 ───────────────────────────────────────────────────────────

def objective(trial):
    lev  = trial.suggest_int("lev", lev_min, lev_max)
    l_th = trial.suggest_float("long", long_min/100, long_max/100)
    s_th = trial.suggest_float("short", short_min/100, short_max/100)
    final,cagr,mdd,_,_ = run_backtest(price_series, lev, l_th, s_th)
    score = cagr - mdd   # 单目标：收益-回撤
    return score

# ─── UI 按钮 ───────────────────────────────────────────────────────────
colA,colB = st.columns(2)
if colA.button("🧠 自动优化"):
    with st.spinner("Optuna 正在搜索最佳参数..."):
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=trial_num)
        params = params = study.best_params
    best_score = study.best_value
    # 生成策略描述文本
    strategy_txt = (
        f"策略说明
"
        f"----------------------
"
        f"• 杠杆倍数: {params['lev']}x
"
        f"• 做多条件: 下跌 {params['long']*100:.2f}% 开多
"
        f"• 做空条件: 上涨 {params['short']*100:.2f}% 开空
"
        f"• 止盈: {tp_pct*100:.2f}%，止损: {sl_pct*100:.2f}%
"
        f"• 滑点假设: {slip_pct*1000:.2f}‰
"
        f"评分 (CAGR-MaxDD): {best_score:.4f}
"
    )
    st.code(strategy_txt, language='markdown')
    # 下载策略 JSON
    st.download_button(
        "💾 下载策略 JSON",
        (json.dumps(params, indent=2)).encode('utf-8'),
        file_name=f"best_strategy_{symbol}_{ts_tag}.json",
        mime='application/json'
    )
    # 复跑生成图表 & 导出
    final,cagr,mdd,pf,tr = run_backtest(price_series, params['lev'], params['long'], params['short'])(price_series, lev, long_th, short_th)
    equity = pf.value
    st.metric("最终净值",f"${final:,.2f}")
    st.metric("CAGR",f"{cagr*100:.2f}%")
    st.metric("最大回撤",f"{mdd*100:.2f}%")
    fig=go.Figure([go.Scatter(x=equity.index,y=equity.values,mode='lines',name='净值')])
    st.plotly_chart(fig,use_container_width=True)
    st.dataframe(tr)
"
