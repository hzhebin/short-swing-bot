
from backtest_engine import BacktestEngine
import streamlit as st

st.set_page_config(page_title="📈 撸短策略自动化回测系统", layout="wide")
st.title("📈 撸短策略自动化回测系统")

engine = BacktestEngine()
engine.render_ui()
