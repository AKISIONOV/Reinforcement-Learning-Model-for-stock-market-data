## 2026-07-31T05:56:34Z
<USER_REQUEST>
You are Worker 3 (Milestone 1 Code Hardening).
Working directory for metadata: f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_worker_m1_hardening
Target code file: f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data_pipeline.py
Target output dataset: f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task & Hardening Fixes:
1. Fix `ffill()` Cross-Ticker Isolation: In `data_pipeline.py`, change any global `.ffill()` or `.bfill()` on concatenated multi-asset DataFrame to group by ticker first: `df.groupby('tic').ffill().groupby('tic').bfill()`.
2. Fix Garman-Klass Volatility for Zero/Zero Price: Use `high = np.maximum(high, 1e-8)` and `low = np.maximum(low, 1e-8)` inside `garman_klass_vol` computation so `log(high/low)` never produces `-inf` or `+inf`.
3. Fix VWAP Distance for Zero Volume: In `vwap` calculation, use `(cum_vol_price) / (cum_vol + 1e-8)` to prevent division by zero when volume is zero.
4. Re-run `python data_pipeline.py` via command line and verify zero NaNs, zero Infs, 28 tickers, 2,835 dates, output saved to `processed_market_dynamics.csv`.
5. Write your handoff report to `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_worker_m1_hardening/handoff.md`.
6. Send a message to the orchestrator (parent) when complete.
</USER_REQUEST>
