import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date

from data_feed import BinanceDataFeed
from backtest_engine import BacktestEngine
from strategies.grid_strategy import GridStrategy
from strategies.breakout_strategy import BreakoutStrategy
from risk_analysis import RiskAnalyzer

st.set_page_config(page_title='Crypto Backtest', layout='wide')
st.title('📈 Professional Crypto Strategy Backtester')

st.sidebar.header('Configuration')
symbol = st.sidebar.text_input('Symbol', 'BTCUSDT')
start_date = st.sidebar.date_input('Start', value=date(2024,1,1))
end_date = st.sidebar.date_input('End', value=date.today())
timeframe = st.sidebar.selectbox('Interval', ('10s','1m','5m'))

strat_name = st.sidebar.selectbox('Strategy', ('Grid','Breakout'))
if strat_name=='Grid':
    grid = st.sidebar.slider('Grid %',0.1,5.0,1.0,0.1)/100
    strat = GridStrategy(grid_size_pct=grid)
else:
    window = st.sidebar.slider('Win',20,200,50,5)
    thr = st.sidebar.slider('Thr %',0.1,5.0,1.0,0.1)/100
    strat = BreakoutStrategy(window=window, threshold_pct=thr)
init_cap = st.sidebar.number_input('Initial USDT',10000.0)
run = st.sidebar.button('Run')

if run:
    feed = BinanceDataFeed(symbol, timeframe, start_date, end_date)
    df = feed.get_data()
    engine = BacktestEngine(df, strat, init_cap)
    trades, equity = engine.run()
    metrics = RiskAnalyzer(equity).summary()

    st.subheader('Metrics')
    st.table(metrics)

    st.subheader('Equity Curve')
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity.index, y=equity, name='Equity'))
    st.plotly_chart(fig,use_container_width=True)

    st.subheader('Trades')
    st.dataframe(trades)
