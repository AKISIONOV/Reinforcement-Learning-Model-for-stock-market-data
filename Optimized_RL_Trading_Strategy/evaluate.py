"""
Standalone Backtesting and Evaluation Script (Milestone 4)
---------------------------------------------------------
Loads `optimal_trading_model.zip` and `custom_env.py` on the test slice
('2016-01-01' to '2020-05-08'), calculates performance metrics:
  - Total Return (%)
  - Annualized Return (%)
  - Annualized Volatility (%)
  - Sharpe Ratio
  - Sortino Ratio
  - Max Drawdown (%)
  - Win Rate (%)
  - Total Transaction Fees ($)
Compares the Optimized RL Strategy against DJIA Equal-Weighted / Buy-and-Hold Baseline,
and outputs clean metric tables.
"""

import os
import sys
import numpy as np
import pandas as pd
from stable_baselines3 import PPO

from custom_env import StockTradingEnv

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


def calculate_metrics(portfolio_values: np.ndarray, daily_returns: np.ndarray, trading_days: int) -> dict:
    """Calculates quantitative performance metrics for a portfolio history."""
    initial_val = portfolio_values[0]
    final_val = portfolio_values[-1]

    # Total Return (%)
    total_return = ((final_val - initial_val) / initial_val) * 100.0

    # Annualized Return (%) [CAGR]
    ann_return = (((final_val / initial_val) ** (252.0 / max(1, trading_days))) - 1.0) * 100.0

    # Annualized Volatility (%)
    ann_vol = (np.std(daily_returns, ddof=1) * np.sqrt(252.0)) * 100.0 if trading_days > 1 else 0.0

    # Sharpe Ratio
    mean_ret = np.mean(daily_returns)
    std_ret = np.std(daily_returns, ddof=1)
    sharpe = (mean_ret * 252.0) / (std_ret * np.sqrt(252.0) + 1e-8) if std_ret > 1e-12 else 0.0

    # Sortino Ratio
    neg_ret = np.minimum(0.0, daily_returns)
    downside_std = np.sqrt(np.mean(neg_ret ** 2))
    sortino = (mean_ret * 252.0) / (downside_std * np.sqrt(252.0) + 1e-8) if downside_std > 1e-12 else 0.0

    # Maximum Drawdown (%)
    peak_series = np.maximum.accumulate(portfolio_values)
    drawdowns = (peak_series - portfolio_values) / (peak_series + 1e-8)
    max_drawdown = np.max(drawdowns) * 100.0

    # Win Rate (%)
    win_rate = (np.sum(daily_returns > 0) / max(1, trading_days)) * 100.0

    return {
        "Initial Value ($)": initial_val,
        "Final Value ($)": final_val,
        "Total Return (%)": total_return,
        "Annualized Return (%)": ann_return,
        "Annualized Volatility (%)": ann_vol,
        "Sharpe Ratio": sharpe,
        "Sortino Ratio": sortino,
        "Max Drawdown (%)": max_drawdown,
        "Win Rate (%)": win_rate
    }


def compute_equal_weight_baseline(test_df: pd.DataFrame, initial_amount: float = 1e6, buy_cost_pct: float = 0.001) -> tuple:
    """
    Computes DJIA Equal-Weighted Buy-and-Hold baseline trajectory on test dataset.
    Allocates initial amount equally across all tickers on day 0 (subject to transaction fee) and holds.
    """
    test_df = test_df.copy()
    test_df['date'] = test_df['date'].astype(str)
    test_df = test_df.sort_values(['date', 'tic']).reset_index(drop=True)

    dates = sorted(test_df['date'].unique())
    tickers = sorted(test_df['tic'].unique())
    stock_dim = len(tickers)

    price_pivot = test_df.pivot(index='date', columns='tic', values='adj_close').ffill().bfill()
    price_matrix = price_pivot.values

    # Equal allocation per stock
    cash_per_stock = initial_amount / stock_dim
    # Deduct 10 bps transaction fee on day 0 buys
    fee_per_stock = cash_per_stock * (buy_cost_pct / (1.0 + buy_cost_pct))
    buy_val_per_stock = cash_per_stock - fee_per_stock

    p0 = price_matrix[0]
    shares = buy_val_per_stock / p0

    baseline_values = []
    for day in range(len(dates)):
        val = np.sum(shares * price_matrix[day])
        baseline_values.append(val)

    baseline_values = np.array(baseline_values, dtype=np.float64)
    baseline_returns = np.zeros(len(baseline_values), dtype=np.float64)
    baseline_returns[1:] = (baseline_values[1:] - baseline_values[:-1]) / (baseline_values[:-1] + 1e-8)

    return dates, baseline_values, baseline_returns, float(fee_per_stock * stock_dim)


def evaluate_strategy(
    model_path: str = "optimal_trading_model.zip",
    data_path: str = "data/processed_market_dynamics.csv",
    test_start_date: str = "2016-01-01",
    test_end_date: str = "2020-05-08"
) -> dict:
    """
    Main evaluation pipeline.
    Loads dataset and model, runs out-of-sample backtest, calculates performance metrics,
    and returns metrics, portfolio trajectories, and regime dataframes.
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}")

    print(f"Loading test dataset from {data_path}...")
    df = pd.read_csv(data_path)
    df['date'] = df['date'].astype(str)

    # Filter test slice
    test_mask = (df['date'] >= test_start_date) & (df['date'] <= test_end_date)
    test_df = df[test_mask].copy().reset_index(drop=True)

    if test_df.empty:
        raise ValueError(f"No test data found between {test_start_date} and {test_end_date}")

    print(f"Test slice contains {test_df['date'].nunique()} trading days ({test_df['date'].min()} to {test_df['date'].max()})")

    # Load RL Model
    if not os.path.exists(model_path):
        if os.path.exists("trained_models/best_model.zip"):
            model_path = "trained_models/best_model.zip"
        elif os.path.exists("best_model.zip"):
            model_path = "best_model.zip"
        else:
            raise FileNotFoundError(f"Model zip file not found at {model_path}")

    print(f"Loading trained RL agent from {model_path}...")
    model = PPO.load(model_path, device='cpu')

    # Instantiate Environment
    test_env = StockTradingEnv(df=test_df)
    obs, info = test_env.reset()

    rl_net_worths = [float(test_env.net_worth)]
    rl_returns = []
    rl_drawdowns = [0.0]
    rl_regimes = []
    rl_cash = [float(test_env.cash)]
    dates_list = test_env.dates

    # Log initial regime
    regime_probs_0 = test_env.regime_array[0]
    rl_regimes.append(int(np.argmax(regime_probs_0)))

    done = False
    step_idx = 0

    while not done:
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = test_env.step(action)
        done = terminated or truncated

        rl_net_worths.append(float(info['net_worth']))
        rl_returns.append(float(info['portfolio_return']))
        rl_drawdowns.append(float(info['drawdown']))
        rl_cash.append(float(test_env.cash))

        step_idx += 1
        if step_idx < len(dates_list):
            reg_probs = test_env.regime_array[step_idx]
            rl_regimes.append(int(np.argmax(reg_probs)))

    rl_net_worths = np.array(rl_net_worths, dtype=np.float64)
    rl_returns = np.array(rl_returns, dtype=np.float64)
    rl_drawdowns = np.array(rl_drawdowns, dtype=np.float64)
    rl_total_fees = float(test_env.cost)

    # Compute DJIA Equal-Weighted Baseline
    dates_b, baseline_values, baseline_returns, baseline_fees = compute_equal_weight_baseline(test_df)

    # Ensure length alignment between RL trajectory and dates
    min_len = min(len(dates_list), len(rl_net_worths), len(baseline_values))
    eval_dates = dates_list[:min_len]
    rl_net_worths = rl_net_worths[:min_len]
    baseline_values = baseline_values[:min_len]
    rl_drawdowns = rl_drawdowns[:min_len]

    # Calculate Drawdown curve for Baseline
    base_peaks = np.maximum.accumulate(baseline_values)
    baseline_drawdowns = (base_peaks - baseline_values) / (base_peaks + 1e-8)

    # Metrics computation
    trading_days = len(rl_returns)
    rl_metrics = calculate_metrics(rl_net_worths, rl_returns, trading_days)
    rl_metrics["Total Transaction Fees ($)"] = rl_total_fees

    base_trading_days = max(1, len(baseline_returns) - 1)
    baseline_metrics = calculate_metrics(baseline_values, baseline_returns[1:], base_trading_days)
    baseline_metrics["Total Transaction Fees ($)"] = baseline_fees

    # Build Comparison Table DataFrame
    comparison_df = pd.DataFrame([rl_metrics, baseline_metrics], index=["Optimized RL Strategy", "DJIA Equal-Weighted Baseline"]).T

    # Display Results Table
    print("\n" + "=" * 75)
    print("           OUT-OF-SAMPLE BACKTESTING & EVALUATION RESULTS")
    print(f"           Test Period: {eval_dates[0]} to {eval_dates[-1]}")
    print("=" * 75)

    table_data = []
    for metric in rl_metrics.keys():
        rl_val = rl_metrics[metric]
        base_val = baseline_metrics[metric]

        if "Value" in metric or "Fees" in metric:
            rl_str = f"${rl_val:,.2f}"
            base_str = f"${base_val:,.2f}"
        elif "Ratio" in metric:
            rl_str = f"{rl_val:.4f}"
            base_str = f"{base_val:.4f}"
        else:
            rl_str = f"{rl_str_val:.2f}%" if (rl_str_val := rl_val) else f"{rl_val:.2f}%"

        table_data.append([metric, rl_str, base_str])

    if HAS_TABULATE:
        print(tabulate(table_data, headers=["Metric", "Optimized RL Strategy", "DJIA Equal-Weighted Baseline"], tablefmt="fancy_grid"))
    else:
        print(f"{'Metric':<30} | {'Optimized RL Strategy':<22} | {'DJIA Baseline':<20}")
        print("-" * 75)
        for metric, rl_str, base_str in table_data:
            print(f"{metric:<30} | {rl_str:<22} | {base_str:<20}")
    print("=" * 75 + "\n")

    # Build structured DataFrame for timeseries output
    timeseries_df = pd.DataFrame({
        "date": eval_dates,
        "rl_net_worth": rl_net_worths,
        "baseline_net_worth": baseline_values,
        "rl_drawdown": rl_drawdowns,
        "baseline_drawdown": baseline_drawdowns,
        "regime_label": rl_regimes[:min_len]
    })

    results = {
        "comparison_table": comparison_df,
        "rl_metrics": rl_metrics,
        "baseline_metrics": baseline_metrics,
        "timeseries_df": timeseries_df
    }

    return results


if __name__ == "__main__":
    evaluate_strategy()
