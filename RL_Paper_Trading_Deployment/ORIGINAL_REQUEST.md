# Original User Request

## 2026-07-31T11:35:40Z

Build a live paper-trading deployment pipeline for the optimal PPO RL model. The system will fetch real-time market data, execute inference, send paper trades via the Alpaca API, and visualize portfolio performance on a Streamlit web dashboard.

Working directory: f:/SURE Trust/Capstone Project/RL_Paper_Trading_Deployment
Integrity mode: development

## Requirements

### R1. Live Data & Inference Pipeline
Create a Python execution script (`trade_executor.py`) that loads `optimal_trading_model.zip` (from the parent project directory: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/optimal_trading_model.zip`), fetches daily/intraday price data for the 28 DJIA assets (using yfinance as a free fallback), computes the 567-dimensional observation state, and outputs the target portfolio weights.

### R2. Alpaca Integration & Mock Execution Mode
Integrate the Alpaca Trading API for execution. Since the user does **not** currently have Alpaca API keys:
1. Provide a `secrets_guide.md` explaining exactly how to register for a free Alpaca Paper Trading account and get the keys.
2. Build a **Mock Execution Mode** into `trade_executor.py`. If no API keys are found in the `.env` file, the script should automatically simulate the trades locally (logging them to a file) instead of crashing, allowing the user to test the pipeline immediately.

### R3. Local Streamlit Dashboard
Build a lightweight Streamlit web dashboard (`dashboard.py`) designed for local testing. It must read the local portfolio logs (from either Alpaca or the Mock Execution Mode) and visualize the paper-trading portfolio value, daily P&L, current asset allocations, and market regimes.

## Acceptance Criteria

### Verification
- [ ] `trade_executor.py` runs successfully in Mock Execution Mode when no API keys are provided, logging simulated trades to a CSV file.
- [ ] The Streamlit dashboard launches locally and successfully visualizes the mock trade logs without crashing.
- [ ] A clear guide (`secrets_guide.md`) is generated explaining how to obtain and inject the Alpaca API keys.
