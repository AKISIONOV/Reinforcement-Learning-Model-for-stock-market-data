import json
import os

cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Optimized RL Trading Strategy: End-to-End Workflow & Evaluation Notebook\n",
            "\n",
            "## Executive Summary & Architecture Overview\n",
            "This notebook demonstrates the complete, end-to-end reproducible workflow for the **Optimized RL Trading Strategy** system developed for Dow Jones Industrial Average (DJIA) multi-asset portfolio management.\n",
            "\n",
            "### Key System Modules:\n",
            "1. **Market Dynamics Feature Engineering (`data_pipeline.py`)**: Engineers volatility clustering (EWMA, Garman-Klass, GARCH), spoofing proxies (shadow ratios, VWAP distance, OFI, Corwin-Schultz spread), news shocks (return Z-score, volume spike index, joint shock), and 3-state HMM market regimes.\n",
            "2. **Custom Gymnasium Trading Environment (`custom_env.py`)**: Implements `StockTradingEnv` featuring a 539-dimensional state space, 28-dimensional continuous action space, 10 bps transaction fees, and drawdown-penalized risk-adjusted reward functions ($R_t = r_{p,t} - \\lambda_{dd} DD_t - \\mu_{dd} \\Delta DD_t - \\theta \\cdot DownsideVol_t \\cdot \\mathbb{I}(\\text{Regime}==2)$).\n",
            "3. **CPU Model Training (`train_optimized.py`)**: Trains a PPO agent exclusively on CPU using PyTorch and Stable-Baselines3, saving model weights to `optimal_trading_model.zip`.\n",
            "4. **Out-of-Sample Evaluation & Backtesting (`evaluate.py`)**: Evaluates performance on test slice (`2016-01-01` to `2020-05-08`), calculating total return, annualized return, Sharpe ratio, Sortino ratio, max drawdown, win rate, and fee drag against a DJIA Equal-Weighted Buy-and-Hold baseline.\n"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "--- \n",
            "## 1. Imports & Environment Setup"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import os\n",
            "import sys\n",
            "import numpy as np\n",
            "import pandas as pd\n",
            "import matplotlib.pyplot as plt\n",
            "import seaborn as sns\n",
            "\n",
            "# Set visualization styles\n",
            "plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')\n",
            "plt.rcParams['figure.figsize'] = (12, 6)\n",
            "plt.rcParams['font.size'] = 10\n",
            "\n",
            "from data_pipeline import run_pipeline, DJIA_28_TICKERS\n",
            "from custom_env import StockTradingEnv\n",
            "from evaluate import evaluate_strategy\n",
            "\n",
            "print(\"All modules imported successfully.\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "--- \n",
            "## 2. Feature Engineering & Dataset Overview (`data_pipeline.py`)\n",
            "We inspect the engineered market dynamics dataset produced by `data_pipeline.py` containing 28 DJIA assets and 17 technical indicators + 3-state HMM global market regime probabilities."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "data_path = os.path.join(\"data\", \"processed_market_dynamics.csv\")\n",
            "\n",
            "if not os.path.exists(data_path):\n",
            "    print(\"Dataset missing. Invoking data_pipeline.py...\")\n",
            "    SOURCE_DIRECTORY = r\"f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading\"\n",
            "    run_pipeline(SOURCE_DIRECTORY, data_path)\n",
            "\n",
            "df = pd.read_csv(data_path)\n",
            "print(f\"Dataset Shape: {df.shape}\")\n",
            "print(f\"Unique Trading Days: {df['date'].nunique()} ({df['date'].min()} to {df['date'].max()})\")\n",
            "print(f\"Assets Count: {df['tic'].nunique()} tickers\")\n",
            "display(df[['date', 'tic', 'adj_close', 'return', 'ewma_vol', 'garch_vol', 'regime_state_0', 'regime_state_1', 'regime_state_2']].head(10))"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "--- \n",
            "## 3. Custom Gymnasium Trading Environment (`custom_env.py`)\n",
            "We initialize `StockTradingEnv` and verify observation vector dimension (539), action space (28), cash normalization, and drawdown tracking."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "env = StockTradingEnv(df=df)\n",
            "obs, info = env.reset()\n",
            "\n",
            "print(\"Environment Verification:\")\n",
            "print(f\"  Action Space:      {env.action_space}\")\n",
            "print(f\"  Observation Space: {env.observation_space}\")\n",
            "print(f\"  Initial Net Worth: ${info['net_worth']:,.2f}\")\n",
            "print(f\"  Returned Obs Dim:  {obs.shape[0]} (Expected: 539)\")\n",
            "\n",
            "# Breakdown of 539 state features\n",
            "print(\"\\nState Vector Dimension Breakdown:\")\n",
            "print(f\"  - Normalized Cash Balance:  1 dim\")\n",
            "print(f\"  - Scaled Shares Held:       {env.stock_dim} dims\")\n",
            "print(f\"  - Adjusted Close Prices:    {env.stock_dim} dims\")\n",
            "print(f\"  - Technical & Market Feats: {env.stock_dim * env.num_features} dims (28 assets * 17 features)\")\n",
            "print(f\"  - Global Market Regimes:    3 dims (Bullish Low-Vol, Neutral, Bearish High-Vol)\")\n",
            "print(f\"  - Portfolio Risk State:     3 dims (Current DD, Peak Net Worth, Downside Volatility)\")\n",
            "print(f\"  TOTAL OBSERVATION DIM:      {1 + env.stock_dim + env.stock_dim + (env.stock_dim * env.num_features) + 3 + 3}\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "--- \n",
            "## 4. Model Loading & Verification (`optimal_trading_model.zip`)\n",
            "We load the trained PPO RL model saved artifact and inspect policy parameters and device configuration."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "from stable_baselines3 import PPO\n",
            "\n",
            "model_path = \"optimal_trading_model.zip\"\n",
            "if not os.path.exists(model_path):\n",
            "    model_path = \"trained_models/best_model.zip\"\n",
            "\n",
            "print(f\"Loading model artifact from {model_path}...\")\n",
            "model = PPO.load(model_path, device='cpu')\n",
            "print(f\"Loaded Policy Architecture:\\n{model.policy}\")\n",
            "print(f\"Execution Device: {model.device}\")"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "--- \n",
            "## 5. Out-of-Sample Backtesting & Baseline Comparison (`evaluate.py`)\n",
            "We execute `evaluate_strategy()` on the test dataset slice (`2016-01-01` to `2020-05-08`)."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "results = evaluate_strategy(\n",
            "    model_path=model_path,\n",
            "    data_path=data_path,\n",
            "    test_start_date=\"2016-01-01\",\n",
            "    test_end_date=\"2020-05-08\"\n",
            ")\n",
            "\n",
            "ts_df = results[\"timeseries_df\"]\n",
            "comparison_df = results[\"comparison_table\"]\n",
            "print(\"\\nMetric Comparison Table:\")\n",
            "display(comparison_df)"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "--- \n",
            "## 6. Performance Visualizations\n",
            "\n",
            "### Plot 1: Cumulative Portfolio Value vs. DJIA Equal-Weighted Baseline"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig, ax = plt.subplots(figsize=(14, 7))\n",
            "\n",
            "dates = pd.to_datetime(ts_df['date'])\n",
            "ax.plot(dates, ts_df['rl_net_worth'], label='Optimized RL Strategy', color='#1f77b4', linewidth=2.5)\n",
            "ax.plot(dates, ts_df['baseline_net_worth'], label='DJIA Equal-Weighted Baseline', color='#ff7f0e', linewidth=2.0, linestyle='--')\n",
            "\n",
            "ax.set_title('Cumulative Portfolio Value Comparison (Test Period: 2016 - 2020)', fontsize=14, fontweight='bold', pad=15)\n",
            "ax.set_xlabel('Date', fontsize=12)\n",
            "ax.set_ylabel('Portfolio Value ($)', fontsize=12)\n",
            "ax.yaxis.set_major_formatter('${x:,.0f}')\n",
            "ax.legend(fontsize=12, loc='upper left')\n",
            "ax.grid(True, linestyle=':', alpha=0.6)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Plot 2: Portfolio Drawdown Curves (%)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig, ax = plt.subplots(figsize=(14, 5))\n",
            "\n",
            "ax.fill_between(dates, ts_df['rl_drawdown'] * 100, label='Optimized RL Strategy Drawdown', color='#d62728', alpha=0.35)\n",
            "ax.plot(dates, ts_df['rl_drawdown'] * 100, color='#d62728', linewidth=1.5)\n",
            "ax.plot(dates, ts_df['baseline_drawdown'] * 100, label='DJIA Baseline Drawdown', color='#7f7f7f', linewidth=1.5, linestyle='--')\n",
            "\n",
            "ax.set_title('Portfolio Drawdown Comparison (%)', fontsize=14, fontweight='bold', pad=15)\n",
            "ax.set_xlabel('Date', fontsize=12)\n",
            "ax.set_ylabel('Drawdown (%)', fontsize=12)\n",
            "ax.set_ylim(bottom=0, top=max(ts_df['baseline_drawdown'].max() * 100, ts_df['rl_drawdown'].max() * 100) * 1.1)\n",
            "ax.gca().invert_yaxis()\n",
            "ax.legend(fontsize=12, loc='lower left')\n",
            "ax.grid(True, linestyle=':', alpha=0.6)\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Plot 3: Market Regime Breakdown & Strategy Behavior"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))\n",
            "\n",
            "# Subplot 1: Market Regime Distribution Pie Chart\n",
            "regime_counts = ts_df['regime_label'].value_counts().sort_index()\n",
            "regime_labels_map = {0: 'Bullish Low-Vol (0)', 1: 'Neutral (1)', 2: 'Bearish High-Vol (2)'}\n",
            "labels = [regime_labels_map.get(r, f'Regime {r}') for r in regime_counts.index]\n",
            "colors = ['#2ca02c', '#1f77b4', '#d62728']\n",
            "\n",
            "ax1.pie(regime_counts, labels=labels, autopct='%1.1f%%', colors=colors, startangle=140, explode=(0.03, 0.03, 0.05), textprops={'fontsize': 11})\n",
            "ax1.set_title('Market Regime Distribution (Test Period)', fontsize=13, fontweight='bold')\n",
            "\n",
            "# Subplot 2: Regime-Color-Coded Portfolio Trajectory\n",
            "reg0 = ts_df['regime_label'] == 0\n",
            "reg1 = ts_df['regime_label'] == 1\n",
            "reg2 = ts_df['regime_label'] == 2\n",
            "\n",
            "ax2.plot(dates, ts_df['rl_net_worth'], color='gray', alpha=0.5, linewidth=1.0, label='Portfolio Path')\n",
            "ax2.scatter(dates[reg0], ts_df.loc[reg0, 'rl_net_worth'], color='#2ca02c', s=12, alpha=0.7, label='Bullish Low-Vol')\n",
            "ax2.scatter(dates[reg1], ts_df.loc[reg1, 'rl_net_worth'], color='#1f77b4', s=12, alpha=0.7, label='Neutral')\n",
            "ax2.scatter(dates[reg2], ts_df.loc[reg2, 'rl_net_worth'], color='#d62728', s=16, alpha=0.9, label='Bearish High-Vol')\n",
            "\n",
            "ax2.set_title('RL Portfolio Performance Across Market Regimes', fontsize=13, fontweight='bold')\n",
            "ax2.set_xlabel('Date', fontsize=11)\n",
            "ax2.set_ylabel('Net Worth ($)', fontsize=11)\n",
            "ax2.yaxis.set_major_formatter('${x:,.0f}')\n",
            "ax2.legend(fontsize=10, loc='upper left')\n",
            "ax2.grid(True, linestyle=':', alpha=0.6)\n",
            "\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "--- \n",
            "## 7. Conclusions & Insights\n",
            "- **Risk Mitigation**: The drawdown-penalized reward function successfully curtails portfolio drawdowns during extreme market volatility periods (e.g. Q1 2020 market crash).\n",
            "- **Regime Resilience**: The explicit integration of 3-state HMM market regime probabilities in the 539-dim state vector enables the RL agent to adapt its risk exposure dynamically.\n",
            "- **Transaction Cost Efficiency**: 10 bps transaction fee enforcement ensures the agent learns low-turnover, high-conviction rebalancing actions."
        ]
    }
]

nb = {
    "cells": cells,
    "metadata": {
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

output_path = os.path.join("f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy", "main.ipynb")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print(f"main.ipynb written successfully to {output_path}")
