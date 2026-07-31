# Algorithmic Trading Strategy Optimization via Deep RL

This repository contains an end-to-end Reinforcement Learning framework for stock market trading, designed to address intraday regime shifts, spoofing, news shocks, and volatility clustering. It improves upon traditional static parametric strategies by utilizing a Deep RL agent (Proximal Policy Optimization) that dynamically adapts to market conditions.

## Project Structure

The project is divided into two primary phases:

### 1. `Optimized_RL_Trading_Strategy/` (Model Training & Optimization)
The core RL training environment that ingests engineered features (HMM Market Regimes, GARCH volatility, Corwin-Schultz spreads).
- **Environment Upgrades**: Tracks a 567-dimensional observation space to handle regime-based position clipping, daily circuit breakers, and action-turnover penalties.
- **Reward Function**: Optimized to heavily penalize downside variance (Sortino proxy) and transaction costs.

### 📈 Benchmarks (Out-of-Sample: 2016 - 2020)
| Metric | Baseline RL Model | **Optimized RL Model (PPO)** |
| :--- | :--- | :--- |
| **Total Return** | 56.71% | **62.21%** |
| **Annualized Return** | 10.91% | **11.80%** |
| **Sharpe Ratio** | 0.6452 | **0.7030** |
| **Sortino Ratio** | 0.8973 | **0.9951** |
| **Max Drawdown** | 33.04% | **31.47%** |
| **Win Rate** | 55.63% | **57.00%** |

### 💾 Dataset
The complete engineered dataset used for training the model (containing 79,380 rows of 28 DJIA assets, featuring Hidden Markov Model regimes, GARCH volatilities, and Corwin-Schultz spreads) is openly available in this repository. 
You can view or download the raw data here: `Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv`

### 2. `RL_Paper_Trading_Deployment/` (Live Deployment Pipeline)
A production-ready pipeline that connects the trained PPO agent to live market feeds.
- **Trade Executor**: Runs inference against real-time Yahoo Finance data to output live portfolio target weights. Integrates directly with the **Alpaca Trading API** to execute paper trades.
- **Mock Execution Mode**: Automatically falls back to simulating live trades locally if Alpaca API keys are not provided.
- **Streamlit Dashboard**: A local web interface (`dashboard.py`) to visualize live portfolio performance, daily P&L, and dynamic market regimes.

## Quick Start

### Running the Deployment Dashboard
```bash
cd RL_Paper_Trading_Deployment/
pip install -r requirements.txt # (Dependencies: stable-baselines3, yfinance, streamlit, alpaca-trade-api)
streamlit run dashboard.py
```

### Live Paper Trading
1. Open the `RL_Paper_Trading_Deployment/secrets_guide.md` for instructions on acquiring a free Alpaca API key.
2. Inject your keys into the `.env` file.
3. Run `python trade_executor.py` to fetch today's market data and execute trades!

---
*Developed for the SURE Trust Capstone Project.*
