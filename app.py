# app.py

from backtest_engine import BacktestEngine
from data_feed import fetch_data

def main():
    data = fetch_data('BTCUSDT', '1m')
    engine = BacktestEngine()
    engine.run_backtest()

if __name__ == '__main__':
    main()
