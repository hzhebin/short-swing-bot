# backtest_engine.py
# 专业回测引擎：支持滑点、爆仓、成交延迟、限价/市价、保证金逻辑

import pandas as pd

class BacktestEngine:
    def __init__(self, df, strategy, initial_balance=10000, leverage=10, fee_taker=0.0004, fee_maker=0.0002,
                 slippage_pct=0.002, delay_ticks=0, order_type='market'):
        self.df = df.reset_index(drop=True)
        self.strategy = strategy
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.position = 0
        self.entry_price = 0
        self.trades = []
        self.leverage = leverage
        self.slippage_pct = slippage_pct
        self.delay_ticks = delay_ticks
        self.order_type = order_type
        self.fee_taker = fee_taker
        self.fee_maker = fee_maker
        self.pending_orders = []
        self.liquidations = []
        self.equity_curve = []

    def get_fee(self, side):
        return self.fee_taker if side == 'market' else self.fee_maker

    def apply_slippage(self, price, side):
        return price * (1 + self.slippage_pct) if side == 'buy' else price * (1 - self.slippage_pct)

    def check_liquidation(self, current_price):
        if self.position == 0:
            return False
        liq_price = self.entry_price * (1 - 1 / self.leverage)
        if current_price <= liq_price:
            self.liquidations.append({"price": current_price, "time": self.df['T'].iloc[self.current_step]})
            self.close_position(current_price, liquidated=True)
            return True
        return False

    def execute_order(self, signal):
        delay_index = self.current_step + self.delay_ticks
        if delay_index >= len(self.df):
            return
        price = self.df['close'].iloc[delay_index]
        fill_price = self.apply_slippage(price, signal['side']) if self.order_type == 'market' else price
        fee = self.get_fee(signal['side'])

        if signal['side'] == 'buy' and self.balance > 0:
            margin = self.balance
            qty = (margin * self.leverage) / fill_price
            self.position = qty
            self.entry_price = fill_price
            self.balance = 0
            self.trades.append({"time": self.df['T'].iloc[self.current_step], "type": "buy", "price": fill_price})

        elif signal['side'] == 'sell' and self.position > 0:
            pnl = self.position * (fill_price - self.entry_price)
            gross = pnl + self.position * self.entry_price
            cost = gross * fee
            self.balance += gross - cost
            self.trades.append({"time": self.df['T'].iloc[self.current_step], "type": "sell", "price": fill_price})
            self.position = 0
            self.entry_price = 0

    def close_position(self, price, liquidated=False):
        if self.position == 0:
            return
        if liquidated:
            self.position = 0
            self.entry_price = 0
            return
        self.execute_order({'side': 'sell'})

    def run(self):
        for i in range(len(self.df)):
            self.current_step = i
            row = self.df.iloc[i]
            current_price = row['close']

            if self.check_liquidation(current_price):
                break

            signal = self.strategy.generate_signal(i, self.df)
            if signal:
                self.execute_order(signal)

            equity_now = self.balance + self.position * current_price
            self.equity_curve.append(equity_now)

        if self.position > 0:
            self.close_position(self.df['close'].iloc[-1])

        final_equity = self.balance
        return {
            'final': final_equity,
            'trades': self.trades,
            'liq_events': self.liquidations,
            'equity_curve': self.equity_curve
        }