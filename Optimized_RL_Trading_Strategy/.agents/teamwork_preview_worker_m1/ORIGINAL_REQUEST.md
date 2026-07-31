## 2026-07-31T11:07:34Z
<USER_REQUEST>
You are Worker 1 for Milestone 1 (Data Engineering for Market Dynamics).
Working directory for metadata: f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_worker_m1
Target project directory: f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy
Parent data source directory: f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Task:
1. Create `data_pipeline.py` in `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy`.
2. Load daily stock CSVs from `f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading`:
   - Include 28 DJIA assets: AAPL, AXP, BA, CAT, CSCO, CVX, DIS, GS, HD, IBM, INTC, JNJ, JPM, KO, MCD, MMM, MRK, MSFT, NKE, PFE, PG, TRV, UNH, V, VZ, WBA, WMT, XOM.
   - Strictly EXCLUDE `UTX.csv` (0 rows) and `DOW.csv` (truncated history).
   - Inject symbol column `tic` for each asset dataframe.
   - Calculate log returns / daily returns based on `Adj Close`.
3. Feature Engineering for Market Dynamics:
   - **Volatility Clustering**:
     - EWMA volatility ($\lambda=0.94$).
     - Rolling Volatility Ratio ($5d / 21d$).
     - Garman-Klass Volatility ($0.5(\ln(H/L))^2 - (2\ln 2 - 1)(\ln(C/O))^2$).
     - GARCH(1,1) conditional volatility (using `arch` library or robust fallback heuristic $\alpha=0.05, \beta=0.90$).
   - **Spoofing Proxies**:
     - Shadow Ratio = (High - max(Open, Close)) / (High - Low + 1e-8) vs (min(Open, Close) - Low) / (High - Low + 1e-8).
     - VWAP distance = (Close - VWAP) / VWAP.
     - Order flow imbalance proxy (Sign(ΔClose) * Volume).
     - Bid-ask spread proxy (Corwin-Schultz High-Low spread proxy).
   - **News Shocks**:
     - Return Shock Z-Score = $(r_t - \mu_{21}) / \sigma_{21}$.
     - Return Jump Indicator = $\mathbb{I}(|\text{Z-Score}| > 3.0)$.
     - Volume Spike Index = $V_t / \text{SMA}_{21}(V)$.
     - Joint Volume-Volatility Shock Proxy.
   - **Intraday Market Regimes**:
     - 3-State Gaussian HMM (fitted using `hmmlearn.hmm.GaussianHMM` on returns & vol, returning posterior probabilities for State 0: Bullish Low-Vol, State 1: Neutral, State 2: Bearish High-Vol). Include fallback to KMeans regime clustering if `hmmlearn` is not installed or fails to converge.
4. Output Dataset:
   - Combine all 28 assets, sort by `['date', 'tic']`, handle any initial window NaNs appropriately (ffill/bfill or drop initial 21-day window).
   - Export processed dataset to `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv`.
5. Verification & Execution:
   - Run `python data_pipeline.py` via command line.
   - Verify that the CSV file is generated, non-empty, contains 28 tickers x ~2836 dates, zero NaNs, and correct columns.
   - Document execution commands and output logs in your handoff report at `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_worker_m1/handoff.md`.
6. Send a message to the orchestrator (parent) when complete.
</USER_REQUEST>
