# Quant Backtest Engine

A professional-grade cryptocurrency strategy backtesting framework built with **Python** and **Streamlit**.

## Features
- ⏱️ **High‑granularity data**: Supports 10‑second synthetic bars (extend to Binance aggTrades).
- ⚙️ **Modular architecture**: Strategies plug into a unified `StrategyBase`.
- 🛡️ **Risk analytics**: Max drawdown, Sharpe, Sortino, Calmar (extendable).
- 📊 **Interactive UI**: Plotly equity curves & Streamlit widgets.
- 🔍 **Parameter search**: Simple grid search (Optuna-ready hook).
- 💼 **Broker simulator**: Fee, leverage, basic slippage placeholder.
- 🚀 **Ready for live trading**: Broker abstraction can swap to paper / real.

## Quick start
```bash
git clone <repo>
cd quant_backtest_engine
pip install -r requirements.txt
streamlit run app.py
```

## Directory structure
```
quant_backtest_engine/
├── app.py
├── backtest_engine.py
├── data_feed.py
├── strategy_base.py
├── strategies/
│   ├── __init__.py
│   ├── grid_strategy.py
│   └── breakout_strategy.py
├── risk_analysis.py
├── optimization.py
├── broker_simulator.py
├── utils.py
├── requirements.txt
└── README.md
```

## TODO
- Implement real Binance aggTrades fetching.
- Add slippage / latency models.
- Add Optuna hyperparameter optimization interface.
- Integrate with OKX / Binance trading APIs for paper & live.
