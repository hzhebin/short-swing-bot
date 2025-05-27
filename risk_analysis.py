import pandas as pd
import numpy as np

class RiskAnalyzer:
    def __init__(self, equity_curve: pd.Series):
        self.eq = equity_curve.dropna()

    def summary(self):
        if len(self.eq) < 2:
            return pd.DataFrame({
                'Metric': ['Total Return', 'Annual Return', 'Max Drawdown', 'Sharpe', 'Sortino'],
                'Value': [0]*5
            }).set_index('Metric')
        returns = self.eq.pct_change().dropna()
        cum_ret = self.eq.iloc[-1] / self.eq.iloc[0] - 1
        annual_ret = (1 + cum_ret) ** (365 / len(returns)) - 1
        max_dd = self._max_drawdown(self.eq)
        sharpe = np.sqrt(365) * returns.mean() / returns.std()
        sortino = np.sqrt(365) * returns.mean() / returns[returns<0].std()
        return pd.DataFrame({
            'Metric': ['Total Return','Annual Return','Max Drawdown','Sharpe','Sortino'],
            'Value': [cum_ret, annual_ret, max_dd, sharpe, sortino]
        }).set_index('Metric')

    @staticmethod
    def _max_drawdown(series):
        roll_max = series.cummax()
        dd = series / roll_max - 1.0
        return dd.min()
