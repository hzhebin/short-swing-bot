# app.py — Advanced Backtest Dashboard
import streamlit as st, pandas as pd, requests, time, numpy as np, plotly.graph_objects as go
from datetime import datetime

# ---------- UI ----------
st.set_page_config(page_title="Advanced Backtest", layout="wide")
st.title("📈 Advanced Quant Backtest System")

sb = st.sidebar
sb.header("参数面板")
symbols   = sb.multiselect("交易对", ["BTCUSDT","ETHUSDT","BNBUSDT"], default=["BTCUSDT"])
start     = sb.date_input("开始日期", value=pd.to_datetime("2024-04-01"))
end       = sb.date_input("结束日期", value=pd.to_datetime("2025-04-30"))
init_bal  = sb.number_input("初始资金 $", 1000, 1_000_000, 10_000, 1000)
lev       = sb.slider("杠杆",1,50,10)
long_th   = sb.slider("做多开仓下跌阈值 %",0.5,5.0,1.0,0.1)/100
short_th  = sb.slider("做空开仓上涨阈值 %",0.5,5.0,1.0,0.1)/100
tp_pct    = sb.slider("止盈 %",0.5,10.0,2.0,0.1)/100
sl_pct    = sb.slider("止损 %",0.5,10.0,3.0,0.1)/100
slip_pct  = sb.slider("滑点 ‰",0.0,5.0,1.0,0.1)/1000
maint_mgn = sb.slider("维持保证金率 %",1,50,10)/100
pos_pct   = sb.slider("单次投入资金占比 %",1,100,20)/100
ts_tag    = datetime.now().strftime("%Y%m%d_%H%M%S")

# ---------- Data ----------
@st.cache_data
def fetch(symbol, start_dt, end_dt):
    url="https://api.binance.com/api/v3/klines"
    s=int(time.mktime(time.strptime(str(start_dt),"%Y-%m-%d"))*1000)
    e=int(time.mktime(time.strptime(str(end_dt),"%Y-%m-%d"))*1000)
    out=[]
    while s<e:
        r=requests.get(url,params={"symbol":symbol,"interval":"1h","startTime":s,"endTime":e,"limit":1000})
        data=r.json()
        if not isinstance(data,list) or not data: break
        out+=data; s=data[-1][0]+1
        time.sleep(0.05)
    df=pd.DataFrame(out,columns=["ts","o","h","l","c","v","ct","q","n","tb","tq","ig"])
    df["ts"]=pd.to_datetime(df["ts"],unit="ms")
    df["c"]=df["c"].astype(float)
    return df[["ts","c"]]

# ---------- Backtest ----------
def backtest(df):
    cash, pos, side = init_bal, 0.0, 0     # side 1 long, -1 short
    entry_val, stake = 0, 0
    trades, equity = [], []
    peak, mdd, explode = init_bal, 0, 0
    for i in range(1,len(df)):
        price_raw=df["c"].iloc[i]
        price=price_raw*(1+slip_pct*(1 if side==1 else -1))
        prev=df["c"].iloc[i-1]; change=(price_raw-prev)/prev
        # 开仓
        if change<=-long_th and side==0:
            stake=cash*pos_pct; qty=stake*lev/price
            pos, entry_val, side, cash = qty, price, 1, cash-stake
            trades.append(("buy",price,qty,df["ts"].iloc[i]))
        elif change>=short_th and side==0:
            stake=cash*pos_pct; qty=stake*lev/price
            pos, entry_val, side, cash = qty, price, -1, cash-stake
            trades.append(("short",price,qty,df["ts"].iloc[i]))
        # 持仓 PnL
        if side!=0:
            pnl=(price-entry_val)*pos*side
            value= cash + stake + pnl
            # 止盈/止损
            if pnl/stake>=tp_pct or pnl/stake<=-sl_pct:
                cash+=stake+pnl; pos, side=0,0
                trades.append(("close",price,qty,df["ts"].iloc[i]))
            # 爆仓（保证金不足）
            elif abs(pnl)>=stake*(1-maint_mgn):
                explode+=1; pos, side=0,0; stake=0; cash=value
        else:
            value=cash
        peak=max(peak,value); mdd=max(mdd,(peak-value)/peak)
        equity.append((df["ts"].iloc[i],value))
    final=value; yrs=len(df)/(24*365)
    cagr=(final/init_bal)**(1/yrs)-1 if yrs>0 else 0
    tr_df=pd.DataFrame(trades,columns=["类型","价格","数量","时间"])
    eq_df=pd.DataFrame(equity,columns=["时间","净值"])
    return final,cagr,mdd,explode,tr_df,eq_df

# ---------- Run ----------
if st.button("▶️ 开始回测"):
    for sym in symbols:
        data=fetch(sym,start,end)
        if data.empty: st.error(f"{sym} 无数据"); continue
        final,cagr,mdd,explode,trades,equity=backtest(data)
        c1,c2,c3,c4=st.columns(4)
        c1.metric("最终净值",f"${final:,.2f}")
        c2.metric("CAGR",f"{cagr*100:.2f}%")
        c3.metric("最大回撤",f"{mdd*100:.2f}%")
        c4.metric("爆仓次数",explode)
        fig=go.Figure([go.Scatter(x=equity['时间'],y=equity['净值'],mode='lines',name='净值')])
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(trades)
        st.download_button("💾 交易明细 CSV", trades.to_csv(index=False).encode('utf-8-sig'),
                           file_name=f"{sym}_trades_{ts_tag}.csv")
        st.download_button("💾 净值曲线 CSV", equity.to_csv(index=False).encode('utf-8-sig'),
                           file_name=f"{sym}_equity_{ts_tag}.csv")
