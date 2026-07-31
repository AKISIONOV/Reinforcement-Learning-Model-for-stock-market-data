# Comprehensive Technical Analysis: GitHub Actions Workflow & Dependencies

## Executive Summary
An inspection of `.github/workflows/daily_trading.yml` and the dependency configuration files in `RL_Paper_Trading_Deployment/` revealed **critical dependency breakages** that cause immediate failure of the CI/CD pipeline, as well as minor configuration flaws in the workflow definition.

---

## 1. Key Inspection Findings

### A. Critical Dependency Breakage (`RL_Paper_Trading_Deployment/requirements-heavy.txt`)
- **Non-Existent NumPy Version (`numpy==2.4.0`)**:
  - File: `RL_Paper_Trading_Deployment/requirements-heavy.txt`, line 1
  - Current spec: `numpy==2.4.0`
  - Problem: NumPy version `2.4.0` has **never been released on PyPI**. PyPI releases currently reach NumPy `2.2.x`.
  - Impact: `pip install -r requirements-heavy.txt` fails immediately with:
    `ERROR: Could not find a version that satisfies the requirement numpy==2.4.0 (from versions: ...)`

- **Non-Existent Pandas Version (`pandas==2.3.3`)**:
  - File: `RL_Paper_Trading_Deployment/requirements-heavy.txt`, line 2
  - Current spec: `pandas==2.3.3`
  - Problem: Pandas version `2.3.3` has **never been released on PyPI**. PyPI 2.x releases currently reach `2.2.3`.
  - Impact: `pip install -r requirements-heavy.txt` fails immediately with:
    `ERROR: Could not find a version that satisfies the requirement pandas==2.3.3 (from versions: ...)`

### B. Missing Explicit Dependency
- **`requests` library missing from `requirements-heavy.txt`**:
  - File: `RL_Paper_Trading_Deployment/trade_executor.py`, line 32 (`import requests`) and line 515 (`requests.post(...)`)
  - Problem: `requests` is used directly in `trade_executor.py` for Alpaca REST API HTTP communications but is not declared in `requirements-heavy.txt`.
  - Impact: Risk of `ModuleNotFoundError: No module named 'requests'` if transitive dependencies change.

### C. Workflow Configuration Flaws (`.github/workflows/daily_trading.yml`)
- **Missing `cache-dependency-path` for Pip Caching**:
  - File: `.github/workflows/daily_trading.yml`, lines 17–21
  - Current setup:
    ```yaml
    - name: Set up Python 3.12
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
        cache: 'pip'
    ```
  - Problem: By default, `actions/setup-python` searches the repository root for `requirements.txt` or `setup.py`. Because `requirements-heavy.txt` is located in `RL_Paper_Trading_Deployment/requirements-heavy.txt`, pip cache resolution fails or produces warnings.
  - Fix: Add `cache-dependency-path: 'RL_Paper_Trading_Deployment/requirements-heavy.txt'`.

- **Missing Artifact Preservation**:
  - File: `.github/workflows/daily_trading.yml`
  - Problem: `trade_executor.py` generates daily execution logs at `RL_Paper_Trading_Deployment/logs/paper_trade_log.csv`, but the workflow does not preserve this output artifact using `actions/upload-artifact@v4`.

---

## 2. File & Configuration Audit Table

| File Path | Inspected Component | Finding / Status | Action Required |
|---|---|---|---|
| `.github/workflows/daily_trading.yml` | Step: `Set up Python 3.12` | Missing `cache-dependency-path` | Add `cache-dependency-path: 'RL_Paper_Trading_Deployment/requirements-heavy.txt'` |
| `.github/workflows/daily_trading.yml` | Step: `Install ML Dependencies` | Installs invalid versions from `requirements-heavy.txt` | Fix `requirements-heavy.txt` |
| `RL_Paper_Trading_Deployment/requirements-heavy.txt` | Line 1: `numpy==2.4.0` | **CRITICAL**: Version 2.4.0 does not exist on PyPI | Change to `numpy==1.26.4` or `numpy>=1.26.4,<2.3.0` |
| `RL_Paper_Trading_Deployment/requirements-heavy.txt` | Line 2: `pandas==2.3.3` | **CRITICAL**: Version 2.3.3 does not exist on PyPI | Change to `pandas==2.2.3` or `pandas>=2.2.0,<2.3.0` |
| `RL_Paper_Trading_Deployment/requirements-heavy.txt` | Explicit imports | Missing `requests` | Add `requests>=2.31.0` |
| `RL_Paper_Trading_Deployment/trade_executor.py` | Import / execution logic | Graceful fallback present for invalid API keys / offline network | No change needed |

---

## 3. Proposed Fixes (Patch Blueprint)

### A. Proposed `RL_Paper_Trading_Deployment/requirements-heavy.txt`
```text
numpy>=1.26.4,<2.0.0
pandas>=2.2.0,<2.3.0
yfinance
arch==8.0.0
hmmlearn==0.3.3
scikit-learn
stable-baselines3==2.9.0
supabase
python-dotenv==1.0.1
requests>=2.31.0
```

### B. Proposed `.github/workflows/daily_trading.yml`
```yaml
name: Daily Paper Trading Execution

on:
  schedule:
    # Run at 21:00 UTC (4:00 PM EST / 5:00 PM EDT) Monday through Friday
    - cron: '0 21 * * 1-5'
  workflow_dispatch: # Allows manual triggering from the GitHub UI

jobs:
  execute-trades:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        
      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
          cache-dependency-path: 'RL_Paper_Trading_Deployment/requirements-heavy.txt'
          
      - name: Install ML Dependencies
        run: |
          cd RL_Paper_Trading_Deployment
          pip install -r requirements-heavy.txt
          
      - name: Execute RL Trading Model
        env:
          APCA_API_KEY_ID: ${{ secrets.APCA_API_KEY_ID }}
          APCA_API_SECRET_KEY: ${{ secrets.APCA_API_SECRET_KEY }}
          APCA_API_BASE_URL: https://paper-api.alpaca.markets
          TRADING_MODE: paper
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
        run: |
          cd RL_Paper_Trading_Deployment
          python trade_executor.py

      - name: Upload Paper Trading Log Artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: paper-trade-logs
          path: RL_Paper_Trading_Deployment/logs/paper_trade_log.csv
```
