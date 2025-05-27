
def compute_risk_metrics(trades_df):
    if trades_df.empty:
        return {}
    profits = trades_df["price"].diff().dropna()
    return {
        "total_return": float(profits.sum()),
        "max_drawdown": float(profits.cumsum().min()),
        "sharpe_ratio": float(profits.mean() / profits.std() if profits.std() != 0 else 0)
    }
