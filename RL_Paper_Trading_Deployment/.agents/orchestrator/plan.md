# Plan: RL Paper Trading Deployment

## Overview
Decompose the RL paper trading deployment into 4 sequential milestones using Project Pattern orchestration.

## Milestone Breakdown

### Milestone 1: Live Data & Inference Pipeline (`trade_executor.py` core)
- Explorer: Inspect `optimal_trading_model.zip`, `custom_env.py`, `data_pipeline.py` in parent directory. Map 28 DJIA asset tickers, 17 technical indicators, 3 HMM regime probabilities, and 567-dim state structure.
- Worker: Implement `trade_executor.py` with:
  - Model loader (PPO from `optimal_trading_model.zip`).
  - Data fetcher using `yfinance` with fallback for historical/offline data.
  - Feature engineering engine matching `data_pipeline.py`.
  - 567-dimensional state vector construction matching `custom_env.py`.
  - Portfolio action & target weight calculation.
- Verification: Verify model loads, state vector is exactly shape `(567,)`, and target weights sum/scale appropriately.

### Milestone 2: Alpaca API Integration, Mock Mode & Secrets Guide
- Worker:
  - Create `secrets_guide.md` with step-by-step instructions for free Alpaca Paper Trading account creation, API keys setup (`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `APCA_API_BASE_URL`), and `.env` setup.
  - Create `.env.example` template.
  - Extend `trade_executor.py` with dual-mode execution engine:
    - Environment check for Alpaca credentials.
    - If credentials missing -> automatically enter **Mock Execution Mode**, log simulated trades and portfolio state to `logs/paper_trade_log.csv` with 10 bps fee model.
    - If credentials present -> attempt execution via Alpaca SDK (`alpaca-py` or REST API).

### Milestone 3: Local Streamlit Dashboard (`dashboard.py`)
- Worker: Implement `dashboard.py` using Streamlit:
  - Read `logs/paper_trade_log.csv`.
  - Key metrics cards: Net Worth, Daily P&L, Total Return %, Active Market Regime.
  - Interactive timeseries plots: Portfolio Value over time, Daily P&L bars.
  - Allocation charts: Asset weights pie/donut chart.
  - Market regime history & breakdown.
- Verification: Launch Streamlit server headlessly or verify script execution via automated test runner.

### Milestone 4: Verification & Forensic Audit
- Reviewer: Examine `trade_executor.py`, `dashboard.py`, `secrets_guide.md`, `logs/paper_trade_log.csv`. Run unit test / verification checks.
- Challenger: Conduct empirical stress tests (missing network/yfinance failure handling, NaN handling, invalid inputs, edge cases).
- Auditor: Perform forensic integrity audit to verify authentic implementation without hardcoding or facades.
