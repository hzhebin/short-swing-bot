import itertools
import pandas as pd
from backtest_engine import BacktestEngine
from risk_analysis import RiskAnalyzer

def grid_search(price_df, StrategyClass, param_grid: dict, metric: str = 'Total Return'):
    """Simple grid search over parameter grid for given strategy."""
    keys, values = zip(*param_grid.items())
    best = None
    records = []
    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        strat = StrategyClass(**params)
        engine = BacktestEngine(price_df, strat)
        _, equity = engine.run()
        metrics = RiskAnalyzer(equity).summary()
        val = metrics.loc[metric,'Value']
        records.append({**params, metric: val})
        if best is None or val > best[metric]:
            best = {**params, metric: val}
    return pd.DataFrame(records), best
