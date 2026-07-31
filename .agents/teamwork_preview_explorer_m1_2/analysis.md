# Comprehensive Python Code & Runtime Analysis Report

**Target Project Directory**: `f:\SURE Trust\Capstone Project\RL_Paper_Trading_Deployment`  
**Inspector**: Explorer 2  
**Date**: 2026-07-31  

---

## Executive Summary

A comprehensive code audit was performed on `trade_executor.py`, `dashboard.py`, `test_stress_executor.py`, `test_stress_dashboard.py`, and project configuration files (`requirements.txt`, `requirements-heavy.txt`, `.env`). 

Key findings include a **critical runtime module import crash** caused by a broken NumPy 2.x alias hack, **missing deployment model and dataset files** required for standalone GitHub Actions CI runner execution, and a **package dependency omission** in `requirements.txt`.

---

## Detailed Findings

### 1. [CRITICAL] Broken NumPy Pickle Workaround Causing Import Crash
* **File**: `trade_executor.py` (lines 20–27)
* **Code snippet**:
  ```python
  try:
      import numpy.core
      sys.modules['numpy._core'] = numpy.core
  except ImportError:
      pass
  ```
* **Empirical Observation**:
  Running `python -c "import trade_executor"` or `python -m pytest` fails during module loading with:
  ```text
  ModuleNotFoundError: No module named 'numpy._core.strings'
  RecursionError: maximum recursion depth exceeded
  ```
* **Root Cause**:
  In NumPy 2.x, `numpy.core` is a deprecated alias module that delegates calls to `numpy._core`. Setting `sys.modules['numpy._core'] = numpy.core` creates a circular aliasing loop (`numpy._core` $\leftrightarrow$ `numpy.core`). When third-party packages (`scipy`, `sklearn`, `arch`) attempt to import submodules like `numpy._core.strings`, Python searches `numpy.core` for `strings`, which fails or enters infinite recursion delegating `__getattr__`.
* **Impact**:
  Execution fails immediately before `trade_executor.py` or any test suite can start.

---

### 2. [HIGH] Missing Strategy Model & Dataset Artifacts in Deployment Root
* **File**: `trade_executor.py` (lines 81–93)
* **Code snippet**:
  ```python
  BASE_DIR = os.path.dirname(os.path.abspath(__file__))
  STRATEGY_DIR = os.path.join(os.path.dirname(BASE_DIR), "Optimized_RL_Trading_Strategy")
  if not os.path.exists(STRATEGY_DIR):
      STRATEGY_DIR = BASE_DIR

  MODEL_PATH = os.path.join(STRATEGY_DIR, "optimal_trading_model.zip")
  if not os.path.exists(MODEL_PATH):
      MODEL_PATH = os.path.join(BASE_DIR, "optimal_trading_model.zip")

  HISTORICAL_DATA_PATH = os.path.join(STRATEGY_DIR, "data", "processed_market_dynamics.csv")
  if not os.path.exists(HISTORICAL_DATA_PATH):
      HISTORICAL_DATA_PATH = os.path.join(BASE_DIR, "data", "processed_market_dynamics.csv")
  ```
* **Empirical Observation**:
  - `optimal_trading_model.zip` exists in `Optimized_RL_Trading_Strategy/optimal_trading_model.zip` (outside `RL_Paper_Trading_Deployment`).
  - `processed_market_dynamics.csv` exists in `Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv` (outside `RL_Paper_Trading_Deployment`).
  - Neither file is present inside `RL_Paper_Trading_Deployment/` repository root.
* **Impact**:
  In a GitHub Actions CI environment where only `RL_Paper_Trading_Deployment` is checked out, `STRATEGY_DIR` will fall back to `BASE_DIR`, triggering an immediate `FileNotFoundError: PPO Model file not found at .../optimal_trading_model.zip` or `FileNotFoundError: Historical dataset not found at .../data/processed_market_dynamics.csv`.

---

### 3. [HIGH] Dependency File Inconsistency (`requirements.txt` vs `requirements-heavy.txt`)
* **Files**: `requirements.txt` and `requirements-heavy.txt`
* **Analysis**:
  - `requirements.txt` contains:
    ```text
    numpy
    pandas
    streamlit
    plotly
    supabase
    python-dotenv
    ```
    It **lacks** core ML packages required by `trade_executor.py`: `stable-baselines3`, `yfinance`, `scikit-learn`, `arch`, `hmmlearn`.
  - If a GitHub Actions workflow installs `requirements.txt`, running `python trade_executor.py` will fail with `ModuleNotFoundError: No module named 'stable_baselines3'`.
  - `requirements-heavy.txt` includes `stable-baselines3==2.9.0`, `arch==8.0.0`, `hmmlearn==0.3.3`, `scikit-learn`, and `yfinance`, but pins `numpy==2.4.0` which triggers Finding #1.

---

### 4. [PASS/RESILIENT] API Key Handling & Mock Execution Fallback
* **File**: `trade_executor.py` (lines 537–558)
* **Analysis**:
  - `trade_executor.py` checks `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, and `TRADING_MODE`. If keys are missing or contain placeholder values (`YOUR_...`), it logs a warning and switches to `MOCK EXECUTION MODE`.
  - Cloud logging via Supabase (lines 783–792) is wrapped in a `try...except` block, preventing database connection errors from failing trade execution.
  - Overall API key handling is resilient and does not cause unhandled runtime crashes.

---

### 5. [MEDIUM] Delisted Ticker Handling (`WBA`)
* **File**: `trade_executor.py` (lines 65–69, 176–191)
* **Analysis**:
  - The ticker list includes `WBA`, which was removed from DJIA in 2024. `yfinance` queries for `WBA` may fail or return NaN rows.
  - Line 176 attempts to backfill missing ticker data from `HISTORICAL_DATA_PATH`. If `HISTORICAL_DATA_PATH` is missing in CI (Finding #2), imputation falls back to a flat value of `100.0`.

---

### 6. [PASS] Observation State Vector Assembly
* **File**: `trade_executor.py` (lines 419–471)
* **Analysis**:
  - Vector layout:
    1. Cash ratio: 1 dimension (`cash / initial_amount`)
    2. Scaled shares: 28 dimensions
    3. Prices: 28 dimensions
    4. Technical indicators: 476 dimensions ($28 \times 17$)
    5. Regime probabilities: 3 dimensions
    6. Risk metrics: 3 dimensions (`drawdown`, `peak_net_worth / initial_amount`, `downside_vol`)
    7. Previous actions: 28 dimensions
    - Total: $1 + 28 + 28 + 476 + 3 + 3 + 28 = 567$ dimensions.
  - The vector shape is strictly asserted `assert obs.shape == (567,)` and sanitized via `np.nan_to_num(obs, nan=0.0, posinf=1e6, neginf=-1e6)`.

---

### 7. [PASS] Streamlit Dashboard & Test Suite Health
* **Files**: `dashboard.py`, `test_stress_dashboard.py`, `test_stress_executor.py`
* **Analysis**:
  - `dashboard.py` handles missing log files gracefully by showing user instructions and calling `st.stop()`.
  - `test_stress_dashboard.py` passes all unit tests for metric calculation and headless rendering once Finding #1 is resolved.
  - `test_stress_executor.py` logic is complete and thorough, but cannot run currently due to Finding #1.

---

## Actionable Recommendations for Implementer

1. **Remove Broken NumPy Alias Hack**:
   - In `trade_executor.py`, remove lines 20–27 (`sys.modules['numpy._core'] = numpy.core`).
2. **Copy Required Artifacts into Repository Root**:
   - Copy `optimal_trading_model.zip` into `RL_Paper_Trading_Deployment/optimal_trading_model.zip`.
   - Copy `data/processed_market_dynamics.csv` into `RL_Paper_Trading_Deployment/data/processed_market_dynamics.csv`.
3. **Consolidate Requirements**:
   - Ensure `requirements.txt` includes all required execution dependencies (`stable-baselines3`, `yfinance`, `scikit-learn`, `arch`, `hmmlearn`, `supabase`, `python-dotenv`, `pandas`, `numpy`).
