import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from datetime import datetime, date

from backtest_engine import BacktestEngine
from data_feed import BinanceDataFeed
from strategies.grid_strategy import GridStrategy
from strategies.breakout_strategy import BreakoutStrategy
from risk_analysis import RiskAnalyzer

# ---------- Streamlit Settings ----------
st.set_page_config(page_title='Crypto Backtest Engine', layout='wide')
st.title('📈 Professional Crypto Strategy Backtester')

# ---------- Sidebar ----------
st.sidebar.header('Configuration')
symbol = st.sidebar.text_input('Symbol (e.g. BTCUSDT)', value='BTCUSDT')
start_date = st.sidebar.date_input('Start Date', value=date(2024, 1, 1))
end_date = st.sidebar.date_input('End Date', value=date.today())
timeframe = st.sidebar.selectbox('Timeframe', ('10s', '1m', '5m', '1h'))

strategy_name = st.sidebar.selectbox('Strategy', ('Grid', 'Breakout'))

if strategy_name == 'Grid':
    grid_size_pct = st.sidebar.slider('Grid Size (%)', min_value=0.1, max_value=10.0, value=1.0, step=0.1)
    leverage = st.sidebar.slider('Leverage', min_value=1, max_value=50, value=10)
    decay = st.sidebar.slider('Decay Factor', min_value=0.1, max_value=1.0, value=0.5, step=0.05)
    params = {'grid_size_pct': grid_size_pct, 'leverage': leverage, 'decay': decay}
    strategy = GridStrategy(**params)
else:
    window = st.sidebar.slider('Breakout Window (bars)', min_value=20, max_value=200, value=50, step=5)
    threshold = st.sidebar.slider('Breakout Threshold (%)', min_value=0.1, max_value=5.0, value=1.0, step=0.1)
    strategy = BreakoutStrategy(window=window, threshold_pct=threshold)

initial_capital = st.sidebar.number_input('Initial Capital (USDT)', value=10000.0, step=100.0)
fee_pct = st.sidebar.number_input('Taker Fee (%)', value=0.04, step=0.01) / 100

run_btn = st.sidebar.button('🚀 Run Backtest')

# ---------- Main ----------
if run_btn:
    with st.spinner('Fetching data & running backtest...'):
        feed = BinanceDataFeed(symbol=symbol, interval=timeframe,
                               start=str(start_date), end=str(end_date))
        price_df = feed.get_data()

        engine = BacktestEngine(price_df,
                                strategy=strategy,
                                initial_capital=initial_capital,
                                fee_pct=fee_pct)
        trades, equity_curve = engine.run()

        # Metrics
        analyzer = RiskAnalyzer(equity_curve)
        metrics = analyzer.summary()

    st.subheader('Performance Metrics')
    st.table(metrics)

    st.subheader('Equity Curve')
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity_curve.index, y=equity_curve, name='Equity'))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader('Trades')
    st.dataframe(trades)
