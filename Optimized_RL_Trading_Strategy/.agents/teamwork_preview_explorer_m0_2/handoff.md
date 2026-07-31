# Handoff Report: Data Audit (Milestone 0)

**From:** Explorer 2  
**To:** Orchestrator (Parent)  
**Date:** 2026-07-31  
**Working Directory:** `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_explorer_m0_2`  
**Analysis Report:** `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_explorer_m0_2/analysis.md`

---

## 1. Observation

- **Directory Inspected:** `f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading` and subfolder `notebooks/`.
- **Total CSV Files Discovered:** 60 files (30 in root directory, 30 in `notebooks/`).
- **File Schema:** All valid files contain 7 columns: `Date`, `Open`, `High`, `Low`, `Close`, `Adj Close`, `Volume`. There is no explicit `tic` column in any CSV file.
- **Sampling Frequency:** Daily OHLCV bars (1 row per trading day).
- **Core Universe Audit Details:**
  - **28 Active Tickers:** AAPL, AXP, BA, CAT, CSCO, CVX, DIS, GS, HD, IBM, INTC, JNJ, JPM, KO, MCD, MMM, MRK, MSFT, NKE, PFE, PG, TRV, UNH, V, VZ, WBA, WMT, XOM.
    - Start Date: `2009-01-02`
    - End Date: `2020-05-07`
    - Total Lines: 2,858 lines (1 header row + 2,857 data rows).
    - Missing Values (NaN): 0 missing values across all 28 assets.
  - **DOW.csv:**
    - Size: 30,723 bytes. Total Lines: 289 lines (1 header + 288 data rows).
    - Date Range: `2019-03-20` to `2020-05-07`. Missing pre-2019 data due to spin-off from DowDuPont.
  - **UTX.csv:**
    - Size: 42 bytes. Total Lines: 2 lines (1 header row `Date,Open,High,Low,Close,Adj Close,Volume`, 0 data rows).
    - Data Content: 100% missing due to United Technologies / Raytheon merger in April 2020.

---

## 2. Logic Chain

1. **Observation:** `UTX.csv` has 0 data rows (42 bytes).  
   **Reasoning:** Attempting to build tensor representations or calculate rolling returns on `UTX.csv` will result in empty arrays, division by zero, or matrix dimension mismatches in RL environments (e.g. Gym / Stable-Baselines3).  
   **Deduction:** `UTX` must be completely purged from the ticker list before dataset loading.

2. **Observation:** `DOW.csv` starts on `2019-03-20`, whereas `main_extracted.py` defines training splits as `2009-01-01` to `2015-12-31`.  
   **Reasoning:** `DOW` contains zero training samples during the specified 2009–2015 training period and zero validation samples in 2016.  
   **Deduction:** `DOW` should be excluded from multi-asset portfolio training algorithms unless historical imputation or a truncated training window (2019+) is explicitly intended.

3. **Observation:** 28 tickers are 100% complete with aligned date ranges (2,857 rows from 2009-01-02 to 2020-05-07).  
   **Reasoning:** These 28 tickers form a contiguous, leak-free panel dataset without missing value gaps.  
   **Deduction:** The benchmark ticker universe for RL training in Milestone 1 should be set to these **28 clean DJIA assets**.

4. **Observation:** Datasets contain daily aggregated OHLCV bars without L2/L3 order book depth, quote bid/ask spreads, or sub-second timestamps.  
   **Reasoning:** True spoofing detection requires analyzing order placement, modification, and rapid cancellation in order book depth.  
   **Deduction:** Direct microstructural spoofing features cannot be engineered from daily CSV data. Coarse daily proxies (Upper/Lower Shadow ratio, VWAP distance, Kyle's Lambda proxy) must be used as substitutes.

5. **Observation:** Daily prices (`Open`, `High`, `Low`, `Close`, `Adj Close`) and multi-year history (2009–2020) are available.  
   **Reasoning:** Exponential smoothing, rolling standard deviations, GARCH(1,1) optimization, and Gaussian Hidden Markov Models rely on daily returns and OHLC ranges.  
   **Deduction:** Volatility clustering (EWMA, GARCH, Parkinson/GK), statistical news jump proxies (Z-scores, overnight gaps, volume spikes), and daily market regime switching (3-State Gaussian HMM) are fully feasible and highly recommended for M1 feature engineering.

---

## 3. Caveats

- **Intraday Limitations:** Because frequency is daily, intraday regime transitions (e.g. morning open vs lunch lulls) cannot be modeled.
- **Microstructure / Spoofing Limitations:** True L2 order book spoofing patterns cannot be detected due to lack of tick-by-tick order book data.
- **News Sentiment Absence:** No textual news or sentiment score data is present in the repository; news shocks are proxied strictly via statistical price/volume jumps.
- **Split Adjustments:** Price return calculations must strictly use `Adj Close` or split-adjusted prices to prevent artificial jump anomalies on split dates (e.g. AAPL 7:1 split in 2014).

---

## 4. Conclusion

- **Dataset State:** The repository contains a solid 11-year daily dataset (2009–2020) for **28 out of 30 DJIA stocks**.
- **Action Items for Data Pipeline (M1):**
  1. Drop `UTX` (empty) and `DOW` (truncated) from the asset universe.
  2. Inject explicit `tic` symbol column into each asset dataframe upon loading.
  3. Compute returns based on `Adj Close`.
  4. Construct feature matrix containing:
     - Volatility clustering: EWMA ($\lambda=0.94$), Garman-Klass Volatility, Rolling Vol Ratio ($5\text{d}/21\text{d}$).
     - News shocks: Return Z-Score, Overnight Gap Return, Volume Spike Index.
     - Market regimes: 3-State Gaussian HMM state posterior probabilities.
     - Shadow Ratio & VWAP distance as daily imbalance proxies.

---

## 5. Verification Method

To independently verify these findings:

1. **Inspect UTX & DOW file size and line counts:**
   - Run `view_file` on `f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading/UTX.csv` to confirm total lines = 2 and size = 42 bytes.
   - Run `view_file` on `f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading/DOW.csv` to confirm total lines = 289 and start date = `2019-03-20`.
2. **Verify 28 Active Stock Line Counts:**
   - Inspect any of the 28 active files (e.g., `AAPL.csv`, `AXP.csv`, `MSFT.csv`) to confirm total lines = 2,858 (2,857 data rows spanning 2009-01-02 to 2020-05-07).
3. **Verify Schema & Columns:**
   - Check line 1 of any non-empty CSV file to confirm header `Date,Open,High,Low,Close,Adj Close,Volume`.

---
*Handoff report completed by Explorer 2.*
