from backtest_engine import BacktestEngine, plot_trades
import streamlit as st

st.set_page_config(page_title="📈 撸短策略自动化回测系统", layout="wide")
st.title("📈 撸短策略自动化回测系统")

engine = BacktestEngine()
df, trades = engine.render_ui()

if not trades.empty:
    fig = plot_trades(df, trades)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ 无交易记录，无法生成图表。")
