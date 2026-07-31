# Project: Optimized_RL_Trading_Strategy

## Architecture
- **Data Engineering Layer**: `data_pipeline.py` — reads parent CSV data, computes volatility clustering, spoofing proxies, news shock jumps, and HMM/regime features.
- **Gymnasium Trading Environment Layer**: `custom_env.py` — custom Gymnasium env processing expanded observation spaces and drawdown-penalized rewards.
- **RL Agent & CPU Training Layer**: `train_optimized.py` — SB3 based PPO trainer forced on CPU (`device='cpu'`). Trains on `data/processed_market_dynamics.csv` and saves `optimal_trading_model.zip`.
- **Evaluation & Packaging Layer**: `main.ipynb`, `evaluate.py`, `summary_of_files.md`, `README.md` — reproducible evaluation, visualization, file summaries, and user documentation.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 0 | Codebase & Data Exploration | Audit parent repo, CSV files, dependencies | none | DONE |
| 1 | Market Dynamics Data Pipeline (R1) | Feature engineering for vol clustering, spoofing, shocks, regimes | M0 | DONE |
| 2 | RL Gymnasium Environment (R2) | Expanded observation space & drawdown risk reward function | M1 | DONE |
| 3 | CPU RL Model Training Pipeline (R3) | Standalone `train_optimized.py` CPU training & model saving | M2 | IN_PROGRESS |
| 4 | Packaging, Notebooks & Documentation | `main.ipynb`, `evaluate.py`, `summary_of_files.md`, `README.md` | M3 | PLANNED |

## Interface Contracts
### Data Pipeline -> RL Environment
- Inputs: Processed pandas DataFrame (`data/processed_market_dynamics.csv`) with date, ticker, close, volume, technical indicators, spoofing proxies, shock indicators, and regime probabilities.
- Outputs: Normalized state vector per timestep per ticker.

### RL Environment -> Agent Trainer
- Standard Gymnasium interface `reset(seed=...)`, `step(action)` returning `(obs, reward, terminated, truncated, info)`.
- Continuous action space `Box(-1.0, 1.0, shape=(28,))`, observation space `Box(-inf, inf, shape=(539,))`.
- Reward includes portfolio return minus drawdown and downside volatility penalties.

## Code Layout
Target root directory `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy`:
```
Optimized_RL_Trading_Strategy/
├── data_pipeline.py        # Feature engineering & dataset preparation
├── custom_env.py           # Custom Gymnasium Trading Environment with drawdown penalty
├── test_custom_env.py      # Unit tests for trading environment
├── train_optimized.py      # Reproducible CPU-only training script
├── evaluate.py             # Evaluation & backtesting utilities
├── main.ipynb              # End-to-end execution notebook
├── optimal_trading_model.zip # Trained model artifact
├── data/                   # Processed datasets (processed_market_dynamics.csv)
├── README.md               # Comprehensive documentation
└── summary_of_files.md     # Summary of files used and created
```
