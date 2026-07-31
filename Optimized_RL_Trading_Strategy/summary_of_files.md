# Project Summary of Files: Optimized RL Trading Strategy

## Overview

This document provides a comprehensive index and detailed technical breakdown of all code, configuration, data, evaluation, notebook, and documentation files in the `Optimized_RL_Trading_Strategy` project workspace.

---

## File Architecture & Summary Table

| Filename | File Type | Role in Pipeline | Key Classes / Functions | Primary Inputs | Primary Outputs |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`data_pipeline.py`** | Python Script | Data Engineering & Market Dynamics | `run_pipeline()`, `engineer_asset_features()`, `fit_and_assign_market_regimes()`, `compute_garch_volatility()`, `compute_corwin_schultz_spread()` | Daily OHLCV stock CSVs (28 DJIA assets) | `data/processed_market_dynamics.csv` |
| **`custom_env.py`** | Python Module | Custom Gymnasium Trading Environment | `StockTradingEnv`, `DEFAULT_TECH_INDICATORS` | Processed market dynamics CSV or DataFrame | 539-dim state obs, scalar reward, reset/step dicts |
| **`train_optimized.py`** | Python Script | CPU Model Training & Checkpointing | `train_ppo_agent()`, `load_and_split_data()`, `evaluate_on_test_set()`, `main()` | `data/processed_market_dynamics.csv` | `optimal_trading_model.zip`, `trained_models/best_model.zip` |
| **`evaluate.py`** | Python Script | Standalone Backtesting & Evaluation | `evaluate_strategy()`, `calculate_metrics()`, `compute_equal_weight_baseline()` | `optimal_trading_model.zip`, test dataset slice | Performance metric tables, timeseries results dictionary |
| **`main.ipynb`** | Jupyter Notebook | End-to-End Workflow & Visualization | End-to-end execution cells, matplotlib & seaborn plot generators | Dataset, model artifact, evaluation script | Interactive visualizations, performance plots, metric tables |
| **`test_custom_env.py`** | Python Test | Unit Verification Suite | `TestStockTradingEnv` (`unittest.TestCase`) | `StockTradingEnv`, processed dataset | Test pass/fail assertions for Gymnasium compliance |
| **`stress_harness_m2.py`** | Python Test | Empirical Stress Suite | `EmpiricalStressHarnessM2` (`unittest.TestCase`) | `StockTradingEnv`, random/adversarial actions | Robustness, fee enforcement, and numerical stability verification |
| **`optimal_trading_model.zip`** | Zip Artifact | Trained RL Agent Weights | SB3 PPO Policy & Value network PyTorch weights | Model training checkpoints | Saved model binary for inference & backtesting |
| **`data/processed_market_dynamics.csv`** | CSV Data | Processed Feature Dataset | 29 columns: OHLCV, 17 technical indicators, 3 HMM regime probabilities | Output of `data_pipeline.py` | Input dataset for training & evaluation environments |
| **`summary_of_files.md`** | Markdown Doc | File Architecture Index | Project summary documentation | Repository structure analysis | Detailed project file index and documentation |
| **`README.md`** | Markdown Doc | Comprehensive Project Documentation | System documentation, guides, formulation equations, benchmarks | Complete project state | Master documentation for users and auditors |

---

## Detailed Per-File Technical Breakdown

### 1. `data_pipeline.py`
- **Purpose**: Ingests raw daily OHLCV CSV files for 28 DJIA equities, computes 17 market dynamics features, fits a 3-state HMM market regime model, and exports the unified dataset.
- **Key Functions**:
  - `engineer_asset_features(df)`: Calculates EWMA volatility, Garman-Klass volatility, GARCH(1,1) conditional volatility, shadow ratios, VWAP distance, Order Flow Imbalance (OFI), Corwin-Schultz bid-ask spread proxy, return Z-score, volume spike index, and joint return-volume shocks.
  - `fit_and_assign_market_regimes(combined_df, lengths)`: Fits GaussianHMM / GMM / KMeans across concatenated sequences (passing length vectors to prevent cross-asset boundary state contamination) and assigns posterior probabilities for State 0 (Bullish Low-Vol), State 1 (Neutral), State 2 (Bearish High-Vol).
  - `run_pipeline(source_dir, output_file)`: Executes end-to-end ingestion, feature calculations, regime fitting, missing value forward/backward filling, and CSV export.
- **Dependencies**: `numpy`, `pandas`, `arch` (optional), `hmmlearn` (optional), `scikit-learn`.

### 2. `custom_env.py`
- **Purpose**: Defines `StockTradingEnv`, a Gymnasium-compliant multi-asset stock trading environment designed for reinforcement learning.
- **Key Specifications**:
  - **State Vector (539 dimensions)**: Cash balance (1), scaled shares held (28), adjusted close prices (28), market dynamics features (28 assets × 17 features = 476), global market regime probabilities (3), and portfolio risk state (3: current drawdown, peak net worth norm, rolling 21-day downside volatility).
  - **Action Space**: Continuous `Box(low=-1.0, high=1.0, shape=(28,))`. Positive values buy target proportions of available cash; negative values sell target proportions of held shares.
  - **Transaction Fee**: 10 bps (0.001 × transaction value) strictly enforced on buy and sell operations.
  - **Reward Function**: Drawdown-penalized reward:
    $$R_t = r_{p,t} - \lambda_{dd} DD_t - \mu_{dd} \Delta DD_t - \theta \cdot DownsideVol_t \cdot \mathbb{I}(\text{Regime} == 2)$$
- **Dependencies**: `gymnasium`, `numpy`, `pandas`.

### 3. `train_optimized.py`
- **Purpose**: Standalone execution script for CPU-only training of the PPO reinforcement learning agent.
- **Key Components**:
  - Sets strict CPU multi-threading via `torch.set_num_threads(os.cpu_count() or 1)` and `device='cpu'`.
  - Chronologically splits `data/processed_market_dynamics.csv` into Train (`2009-02-03` to `2015-12-31`), Validation (`2016-01-04` to `2016-12-30`), and Test (`2016-01-04` to `2020-05-07`).
  - Utilizes SB3 `EvalCallback` for evaluation on validation set during training.
  - Saves best model artifacts to `optimal_trading_model.zip` and `trained_models/best_model.zip`.

### 4. `evaluate.py`
- **Purpose**: Standalone backtesting and quantitative evaluation script.
- **Key Functions**:
  - `evaluate_strategy()`: Runs `optimal_trading_model.zip` on the test slice (`2016-01-01` to `2020-05-08`).
  - `compute_equal_weight_baseline()`: Simulates an Equal-Weighted Buy-and-Hold DJIA baseline starting at $1,000,000 with 10 bps initial buy fee.
  - `calculate_metrics()`: Calculates Total Return (%), Annualized Return (%), Annualized Volatility (%), Sharpe Ratio, Sortino Ratio, Max Drawdown (%), Win Rate (%), and Total Fees Paid ($).
  - Outputs formatted comparison tables via `tabulate` / ASCII tables.

### 5. `main.ipynb`
- **Purpose**: Self-contained, fully runnable Jupyter Notebook demonstrating the end-to-end strategy workflow.
- **Contents**:
  - Feature engineering overview (`data_pipeline.py`).
  - Environment setup and state breakdown (`custom_env.py`).
  - Model loading and policy inspection (`train_optimized.py`).
  - Out-of-sample backtesting (`evaluate.py`).
  - Publication-quality Matplotlib performance plots: Cumulative Portfolio Value vs Baseline, Portfolio Drawdown Curve (%), and Market Regime Breakdown (pie chart & regime-highlighted portfolio trajectory).

### 6. `test_custom_env.py` & `stress_harness_m2.py`
- **Purpose**: Unit testing and empirical stress suites for `custom_env.py`.
- **Coverage**: SB3 `check_env`, Gymnasium `check_env`, 1000-step random action trajectory stability, 10 bps fee accuracy, 539-dim observation vector verification, episode reset cleanliness, and adversarial input robustness (NaNs, Infs, extreme bounds).

### 7. `optimal_trading_model.zip`
- **Purpose**: Saved model weights artifact containing PyTorch policy network parameters trained via PPO on CPU.

### 8. `data/processed_market_dynamics.csv`
- **Purpose**: Preprocessed market dynamics dataset containing 79,380 rows across 28 DJIA equities and 29 columns.
