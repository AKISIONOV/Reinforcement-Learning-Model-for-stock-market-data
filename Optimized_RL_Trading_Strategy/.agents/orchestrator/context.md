# Context & Background

## Mission Overview
The objective of this project is to build an **Optimized RL Trading Strategy** system with enhanced market dynamics features and risk-adjusted reward mechanisms.

## Directory Paths
- **Target Workspace**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy`
- **Parent Codebase & Data**: `f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading`
- **Orchestrator Metadata**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/orchestrator`

## Core Requirements & Specifications

### 1. Data Engineering for Market Dynamics (R1) [COMPLETE & AUDITED CLEAN]
- `data_pipeline.py` & `data/processed_market_dynamics.csv`
- Engineered features: EWMA, vol ratio, Garman-Klass, GARCH, shadow ratios, VWAP distance, OFI, Corwin-Schultz spread, return Z-score, jump indicator, volume spike index, joint shock, and 3-state HMM market regimes.

### 2. RL Environment Adaptation (R2) [COMPLETE & AUDITED CLEAN]
- `custom_env.py` & `test_custom_env.py`
- Gymnasium compliance: 539-dim observation space, 28-dim continuous action space, 10 bps fee enforcement, drawdown-penalized risk reward ($R_t = r_{p,t} - \lambda_{dd} DD_t - \mu_{dd} \Delta DD_t - \theta \cdot DownsideVol_t \cdot \mathbb{I}(\text{Regime}==2)$).

### 3. Model Training & Saving (R3) [IN_PROGRESS / NEXT TO EXECUTE]
- Standalone reproducible execution script `train_optimized.py`.
- Train RL agent (PPO) **EXCLUSIVELY on CPU** (`device='cpu'`) using `StockTradingEnv` and `data/processed_market_dynamics.csv`.
- Save the trained model weights/artifacts (`optimal_trading_model.zip`) to `Optimized_RL_Trading_Strategy`.

### 4. Packaging, Notebooks & Documentation (R3/Packaging) [TO EXECUTE AFTER M3]
- `evaluate.py`: Evaluation and backtesting utilities.
- `main.ipynb`: End-to-end reproducible Jupyter Notebook.
- `summary_of_files.md`: Comprehensive index and summary of files used and created.
- `README.md`: Detailed documentation explaining feature engineering, drawdown reward rationale, installation, usage, and performance benchmarks.
