from backtest_engine import BacktestEngine, plot_trades
import streamlit as st

st.set_page_config(page_title="📈 撸短策略自动化回测系统", layout="wide")
st.title("📈 撸短策略自动化回测系统")

# 初始化回测引擎
engine = BacktestEngine()

# 渲染界面并执行回测
df, trades = engine.render_ui()

# 若有交易记录则画图
if not trades.empty:
    fig = plot_trades(df, trades)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ 无交易记录，无法生成图表。")
