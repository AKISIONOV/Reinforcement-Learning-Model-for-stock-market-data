# Forensic Audit Report — RL Paper Trading Deployment

**Verdict: CLEAN**

**Auditor Subagent**: `auditor_m4`  
**Target Codebase**: `f:/SURE Trust/Capstone Project/RL_Paper_Trading_Deployment` (`trade_executor.py`, `dashboard.py`, `secrets_guide.md`, `logs/paper_trade_log.csv`)  
**Audit Timestamp**: 2026-07-31T17:20:15Z  

---

## 1. Observation

Direct empirical observations collected during static code inspection and dynamic execution tracing:

1. **Static Analysis of `trade_executor.py`**:
   - **Data Ingestion (`fetch_aligned_market_data`)**: Lines 82–172 implement yfinance live API data fetching (`yf.download`) for 28 DJIA tickers across 60 trading days with automatic CSV fallback (`data/processed_market_dynamics.csv`) and Cartesian product alignment (`dates` × `tickers`). Handles missing/delisted tickers (e.g. `WBA` returning Yahoo 404) via last-known value imputation and forward/backward filling.
   - **Technical Feature Engine (`engineer_asset_features`)**: Lines 231–300 calculate all 17 technical indicators natively using Pandas/NumPy:
     - Returns & Log returns (`pct_change`, `np.log`)
     - EWMA volatility (`ewm(alpha=0.06)`)
     - Volatility ratio 5/21 (`rolling(5).std() / rolling(21).std()`)
     - Garman-Klass volatility (`0.5*(log(H/L))^2 - (2*log(2)-1)*(log(C/O))^2`)
     - GARCH(1,1) volatility (`arch_model` or `fallback_garch11` recursive variance update `sigma2[t] = omega + alpha*r[t-1]^2 + beta*sigma2[t-1]`)
     - Upper/Lower Candlestick Shadows & Shadow Ratio
     - 21-day VWAP & VWAP distance
     - Order Flow Imbalance (`sign(delta_close) * volume`)
     - Corwin-Schultz High-Low Bid-Ask Spread Proxy
     - Return Shock Z-Score & Jump Indicator (`|zscore| > 3.0`)
     - Volume Spike Index & Joint Vol-Vol Shock
   - **Market Regime Engine (`fit_and_assign_market_regimes`)**: Lines 302–356 dynamically fit a 3-component Gaussian HMM (`GaussianHMM` from `hmmlearn.hmm`, with fallback to `GaussianMixture` and `KMeans`) on standardized asset returns and EWMA volatility. Predicts posterior regime probabilities `(regime_state_0, regime_state_1, regime_state_2)`.
   - **Observation Vector Assembly (`construct_observation_vector`)**: Lines 399–452 stack:
     - Cash norm (dim 1)
     - Shares scaled (dim 28)
     - Current prices (dim 28)
     - Technical features (28 assets × 17 indicators = dim 476)
     - Market regime probabilities (dim 3)
     - Risk state: drawdown, peak net worth ratio, downside volatility (dim 3)
     - Previous action vector (dim 28)
     Total shape strictly enforced via `assert obs.shape == (567,)`.
   - **Model Inference (`run_paper_trading`)**: Lines 503–755 load PyTorch weights from `optimal_trading_model.zip` using Stable-Baselines3 (`PPO.load`). Evaluates actions via `model.predict(obs, deterministic=True)` and converts continuous actions `[-1.0, 1.0]` into target portfolio weights, subject to circuit breaker liquidation (`daily_return < -5%`) and Bearish regime position capping (`[-0.5, 0.5]`).
   - **Dual-Mode Execution**: Lines 458–497 (`AlpacaExecutionEngine`) validate Alpaca REST API keys (`/v2/account`). If credentials are missing or invalid, automatically defaults to Mock Execution Mode with a 10 bps transaction fee model (`fee_pct = 0.001`).

2. **Static Analysis of `dashboard.py`**:
   - Lines 1–616 implement a complete Streamlit web application (`st.set_page_config`, layout wide).
   - Reads `logs/paper_trade_log.csv` via `load_trade_log()`.
   - Displays 5 key performance metrics (Portfolio Net Worth, Total Return vs $1M baseline, Daily Return, Active Market Regime, Execution Mode).
   - Contains 4 interactive visual tabs:
     - Tab 1: Portfolio Net Worth trajectory vs $1M baseline, daily returns bar chart, drawdown curve.
     - Tab 2: Asset allocation donut chart, asset weight breakdown bar chart, active holdings table.
     - Tab 3: Market regime distribution pie chart, frequency table, regime-overlay net worth scatter plot.
     - Tab 4: Interactive trade log data table with multi-criteria filtering (action type, ticker, free-text search) and CSV export button.

3. **Static Analysis of `secrets_guide.md`**:
   - Lines 1–90 contain a clear 5-section guide for obtaining free Alpaca paper trading API keys, configuring `.env` variables (`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `APCA_API_BASE_URL`), and explaining dual-mode fallback execution.

4. **Dynamic Execution Tracing**:
   - Command executed: `python trade_executor.py` in `f:/SURE Trust/Capstone Project/RL_Paper_Trading_Deployment`.
   - Log output summary:
     ```
     [INFO] Loading RL PPO model from: ...\optimal_trading_model.zip
     [INFO] SB3 Model loaded successfully. Action Dim: 28, Obs Dim: 567
     [WARNING] Alpaca API credentials missing or placeholder values in environment/.env.
     [WARNING] Automatically entering MOCK EXECUTION MODE.
     [INFO] Fetching live market data for 28 DJIA tickers via yfinance...
     [INFO] Successfully fetched yfinance data (1680 records across 60 dates).
     [2026-07-17] Mode: MOCK | Regime: Neutral | Trades: 10 | Cash: $0.00 | Net Worth: $998,539.75
     ...
     [2026-07-30] Mode: MOCK | Regime: Neutral | Trades: 28 | Cash: $0.00 | Net Worth: $1,043,354.88
     [SUCCESS] Total trade & snapshot records logged: 255
     [SUCCESS] Log file output: logs/paper_trade_log.csv
     ```
   - Command executed: `python -c "import dashboard; df, err = dashboard.load_trade_log('logs/paper_trade_log.csv'); print(len(df), err)"`
   - Log output: `Loaded trade log records: 255 Error: None`.

---

## 2. Logic Chain

1. **Observation 1 & 4** show that `trade_executor.py` ingests real market OHLCV data for 28 assets via `yfinance` (with fallback dataset support), computes 17 mathematical technical indicators and 3 HMM market regime probabilities without any hardcoded/stubbed values, and constructs valid 567-dimensional state vectors.
2. **Observation 1 & 4** show that `optimal_trading_model.zip` is loaded via Stable-Baselines3 PyTorch engine, generating continuous action vectors that govern trade allocation and execute simulated trades with 10 bps transaction costs in Mock Execution Mode.
3. **Observation 2 & 4** show that `dashboard.py` parses `logs/paper_trade_log.csv` dynamically, generating real-time performance metrics, Plotly visualizations, and interactive log tables without static/fake placeholders.
4. **Observation 3** shows that `secrets_guide.md` provides accurate setup documentation for Alpaca paper trading API keys.
5. **Conclusion**: The codebase represents a genuine, fully operational Reinforcement Learning paper trading execution pipeline. No integrity violations, facade implementations, hardcoded test results, or dummy loops exist.

---

## 3. Caveats

- **Live Alpaca Credentials**: The audit verified Alpaca API integration via static analysis of `AlpacaExecutionEngine` and dynamic execution in Mock Execution Mode. Live order submission against Alpaca's paper trading server requires user-supplied API keys in `.env`.

---

## 4. Conclusion

**Verdict: CLEAN**

The RL Paper Trading Deployment work product (`trade_executor.py`, `dashboard.py`, `secrets_guide.md`, `logs/paper_trade_log.csv`) passes all forensic checks:
- **Static Analysis**: CLEAN (No hardcoded test outputs, fake indicators, facade classes, or dummy execution loops).
- **Dynamic Verification**: CLEAN (Real yfinance data ingestion, 17 technical indicators, 3 HMM regimes, 567-dim state assembly, SB3 PPO model prediction, portfolio accounting with 10 bps fee model, and CSV logging).
- **Dashboard Integrity**: CLEAN (Dynamic visualization and filtering of execution logs).

---

## 5. Verification Method

To independently re-verify the forensic audit verdict, run the following commands from `f:/SURE Trust/Capstone Project/RL_Paper_Trading_Deployment`:

1. **Execute Paper Trading Engine in Mock Mode**:
   ```powershell
   python trade_executor.py
   ```
   *Expected outcome*: Output log shows yfinance data download, SB3 PPO model loading (Obs: 567, Action: 28), HMM regime calculation, 10 execution steps logged, and 255 records written to `logs/paper_trade_log.csv`.

2. **Verify Streamlit Dashboard Load**:
   ```powershell
   python -c "import dashboard; df, err = dashboard.load_trade_log(dashboard.DEFAULT_LOG_PATH); assert err is None and len(df) > 0, 'Dashboard load failed!'"
   ```
   *Expected outcome*: Exits cleanly with zero errors.

3. **Inspect Output Log File**:
   Inspect `logs/paper_trade_log.csv` to confirm 255 valid trade & snapshot records.
