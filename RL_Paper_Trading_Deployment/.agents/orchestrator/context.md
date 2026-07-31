# Context: RL Paper Trading Deployment

## Project Background
The parent project `Optimized_RL_Trading_Strategy` trained a PPO reinforcement learning model (`optimal_trading_model.zip`) on 28 DJIA equities using engineered market dynamics features (17 indicators) and 3-state HMM market regime probabilities. The trading environment (`custom_env.py`) defines a 567-dimensional observation space.

## Operational Objectives
1. Build `trade_executor.py`: Python deployment pipeline that ingests daily/intraday stock data via `yfinance`, computes the 567-dim state vector, performs PPO model inference, and generates portfolio weights.
2. Dual-Mode Execution & Documentation:
   - Provide `secrets_guide.md` for free Alpaca Paper Trading setup.
   - Built-in Mock Execution Mode in `trade_executor.py` when API keys are absent in `.env`, logging paper trades to `logs/paper_trade_log.csv`.
3. Build `dashboard.py`: Streamlit dashboard visualizing portfolio value, daily P&L, asset allocations, and market regime breakdown.
4. Independent verification, stress testing, and forensic audit.

## Key References & Paths
- Parent model: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/optimal_trading_model.zip`
- Parent env: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/custom_env.py`
- Parent pipeline: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data_pipeline.py`
- Deployment directory: `f:/SURE Trust/Capstone Project/RL_Paper_Trading_Deployment`
- Target outputs: `trade_executor.py`, `dashboard.py`, `secrets_guide.md`, `logs/paper_trade_log.csv`, `.env.example`
