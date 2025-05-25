
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="专业量化回测仪表盘", layout="wide")
st.title("📈 策略回测仪表盘")

# 模拟数据（后期可通过后端注入）
initial_capital = 10000
df = pd.DataFrame({
    "time": pd.date_range("2024-04-01", periods=6, freq="5D"),
    "equity": [10000, 10750, 10300, 10980, 11400, 12200]
})
trades = pd.DataFrame({
    "time": ["2024-04-02", "2024-04-08", "2024-04-11", "2024-04-22"],
    "type": ["Buy", "Sell", "Buy", "Sell"],
    "price": [30000, 32000, 31000, 34000],
    "size": [0.01, 0.01, 0.01, 0.01],
    "pnl": [None, 200, None, 300]
})

# 指标计算
final_value = df['equity'].iloc[-1]
cagr = (final_value / initial_capital) ** (1 / (25 / 365)) - 1
max_drawdown = 0.12
sharpe_ratio = 1.83

# 概览指标
col1, col2, col3, col4 = st.columns(4)
col1.metric("初始资金", f"${initial_capital:,.2f}")
col2.metric("最终净值", f"${final_value:,.2f}")
col3.metric("年化收益率", f"{cagr * 100:.2f}%")
col4.metric("最大回撤", f"{max_drawdown * 100:.2f}%")

# 净值曲线图
st.subheader("📊 净值曲线图（含策略对比）")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["time"], y=df["equity"],
    mode="lines+markers",
    name="策略A", line=dict(color="blue"),
    hovertemplate="日期: %{x|%Y-%m-%d}<br>净值: $%{y:.2f}<extra></extra>"
))
fig.update_layout(height=400, hovermode="x unified", xaxis_title="时间", yaxis_title="净值 ($)")
st.plotly_chart(fig, use_container_width=True)

# 交易明细
st.subheader("📋 交易明细")
st.dataframe(trades)

# 导出按钮占位
st.download_button("📥 下载交易记录 CSV", data=trades.to_csv(index=False), file_name="trades.csv")
