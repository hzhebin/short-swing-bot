import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

class BacktestEngine:
    def __init__(self):
        pass

    def fetch_mock_data(self, days=30):
        # 生成伪价格数据（正弦波+噪声）
        dates = pd.date_range(datetime.today() - timedelta(days=days), periods=days * 24, freq='H')
        prices = np.sin(np.linspace(0, 12 * np.pi, len(dates))) * 100 + 1000
        noise = np.random.normal(0, 10, len(dates))
        prices += noise
        df = pd.DataFrame({'timestamp': dates, 'price': prices})
        return df

    def run_backtest(self, df, leverage=10, position_size=100, fee_rate=0.0005, initial_balance=10000):
        balance = initial_balance
        position = 0
        entry_price = 0
        trades = []
        capital_curve = []

        for i in range(1, len(df)):
            prev = df.iloc[i - 1]['price']
            curr = df.iloc[i]['price']
            pct_change = (curr - prev) / prev

            # 开仓
            if pct_change <= -0.01:
                units = (position_size * leverage) / curr
                cost = position_size * (1 + fee_rate)
                if balance >= cost:
                    position += units
                    entry_price = curr
                    balance -= cost
                    trades.append({'time': df.iloc[i]['timestamp'], 'price': curr, 'type': 'buy'})

            # 平仓
            elif pct_change >= 0.01 and position > 0:
                revenue = position * curr * (1 - fee_rate)
                balance += revenue
                trades.append({'time': df.iloc[i]['timestamp'], 'price': curr, 'type': 'sell'})
                position = 0

            net_value = balance + position * curr
            capital_curve.append(net_value)

        trades_df = pd.DataFrame(trades)
        df['net_value'] = capital_curve + [capital_curve[-1]] * (len(df) - len(capital_curve))
        return df, trades_df

    def render_ui(self):
        st.sidebar.subheader("策略参数设置")
        leverage = st.sidebar.slider("杠杆倍数", 1, 50, 10)
        position_size = st.sidebar.slider("每次建仓金额($)", 10, 1000, 100)
        fee_rate = st.sidebar.slider("手续费率", 0.0001, 0.01, 0.0005)
        initial_balance = st.sidebar.number_input("初始资金($)", value=10000)

        df = self.fetch_mock_data()
        df, trades = self.run_backtest(df, leverage, position_size, fee_rate, initial_balance)

        st.success(f"💰 最终净值：${df['net_value'].iloc[-1]:,.2f}")
        return df, trades

def plot_trades(df, trades):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['price'], mode='lines', name='价格'))

    buy = trades[trades['type'] == 'buy']
    sell = trades[trades['type'] == 'sell']
    fig.add_trace(go.Scatter(x=buy['time'], y=buy['price'], mode='markers', name='买入', marker=dict(color='green', size=8, symbol='triangle-up')))
    fig.add_trace(go.Scatter(x=sell['time'], y=sell['price'], mode='markers', name='卖出', marker=dict(color='red', size=8, symbol='triangle-down')))

    fig.update_layout(title='交易回测图', xaxis_title='时间', yaxis_title='价格', legend_title='图例')
    return fig
