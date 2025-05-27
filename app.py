
import streamlit as st
from backtest_engine import BacktestEngine
from data_feed import get_data
from strategies.grid_strategy import GridStrategy
from strategies.breakout_strategy import BreakoutStrategy
from risk_analysis import compute_risk_metrics
from optimization import optimize_parameters

st.set_page_config(page_title="Quant Backtest Engine", layout="wide")
st.title("📈 Quant Backtest Engine")

symbol = st.sidebar.text_input("📊 Symbol", value="BTCUSDT")
strategy_type = st.sidebar.selectbox("⚙️ Strategy", ["Grid", "Breakout"])
start_date = st.sidebar.date_input("📅 Start Date")
end_date = st.sidebar.date_input("📅 End Date")

if st.sidebar.button("▶️ Run Backtest"):
    with st.spinner("Fetching data and running backtest..."):
        data = get_data(symbol, start_date, end_date)
        strategy = GridStrategy() if strategy_type == "Grid" else BreakoutStrategy()
        engine = BacktestEngine(data=data, strategy=strategy, initial_capital=10000)
        result = engine.run()
        st.subheader("📍 Trades and Performance")
        st.plotly_chart(result["plot"], use_container_width=True)
        st.subheader("📊 Risk Metrics")
        st.json(compute_risk_metrics(result["trades"]))
        st.subheader("📁 Export")
        st.download_button("Download Trades CSV", result["trades"].to_csv().encode(), file_name="trades.csv", mime="text/csv")
