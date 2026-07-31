# Handoff Report — Data Quality & Feature Correctness Review (Milestone 1)

**Working Directory**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_reviewer_m1_2`  
**Date**: 2026-07-31  

---

## 1. Observation

- **Source File Inspected**: `data_pipeline.py` (lines 1 to 318).
- **Generated Dataset Inspected**: `data/processed_market_dynamics.csv` (79,380 rows, 29 columns).
- **Execution & Automated Verification Logs**:
  - `python ".agents/teamwork_preview_reviewer_m1_2/scratch/thorough_verification.py"`
  - Tickers present: 28 exact DJIA assets (excluding UTX and DOW). Each ticker contains 2835 daily rows spanning `2009-02-03` to `2020-05-07`.
  - Missing value audit: `df.isna().sum().sum()` returned `0`. `np.isinf(df.select_dtypes(include=[np.number])).sum().sum()` returned `0`.
  - Feature variance audit: All 27 numerical feature columns have non-zero variance.
  - Outlier audit: `df['shadow_ratio'].max()` returned `1.000000e+08` (100 million).
  - Corwin-Schultz zero audit: `(df['corwin_schultz_spread'] == 0.0).mean()` returned `0.459725` (45.97% zeros).
  - Truncation / Data Leakage experiment: Truncating `combined_df` from 79,380 rows to 39,690 rows (first half) shifted historical regime posteriors on identical historical dates by up to **`0.308002`** (30.8% shift in `regime_state_0`).
  - HMM fitting code inspection: Line 202 calls `hmm.fit(X_scaled)` without passing the `lengths` argument.

---

## 2. Logic Chain

1. **Dataset Integrity Logic**:
   - Observations show `processed_market_dynamics.csv` contains all 28 expected DJIA tickers (`AAPL` to `XOM`, excluding `UTX` and `DOW`) with exactly 2835 aligned dates per ticker.
   - Standard columns (`date`, `open`, `high`, `low`, `close`, `adj_close`, `volume`, `tic`) are correctly populated, sorted by `['date', 'tic']`, and free of NaNs/Infs.

2. **Data Leakage & Temporal Lookahead Logic**:
   - Lines 186-193 in `fit_and_assign_market_regimes` calculate global mean/std scaling (`mean_f`, `std_f`) over all 79,380 rows across the entire 11-year dataset simultaneously.
   - Lines 201-226 fit HMM / GMM models on the entire time horizon simultaneously.
   - When the dataset was truncated in our verification test, the historical regime posterior probabilities changed by up to **0.308002**. This proves that regime features assigned to early dates incorporate future dataset information (lookahead leakage).

3. **Cross-Asset HMM Boundary Logic**:
   - `combined_df` concatenates 28 stock time series sequentially (`pd.concat(processed_dfs)`).
   - In `GaussianHMM.fit(X_scaled)` (line 202), no `lengths` parameter is passed to specify sequence breaks between tickers.
   - `hmmlearn` assumes a single continuous Markov process, corrupting transition probability matrix $A_{ij}$ across ticker boundaries (e.g. from AAPL end-date to AXP start-date).

4. **Numerical Stability Logic**:
   - Line 151 computes `shadow_ratio = shadow_upper / (shadow_lower + 1e-8)`.
   - When `shadow_lower == 0.0` (3.97% of rows), the denominator drops to `1e-8`, magnifying `shadow_upper` by $10^8$. Max value reaches $10^8$, creating destabilizing input spikes for neural networks.

---

## 3. Caveats

- **External Packages**: Python 3.14 environment lacked C++ build tools to compile `hmmlearn` wheel; fallback execution cleanly tested `GaussianMixture` (GMM). `GaussianHMM` logic was verified via code inspection and algorithm analysis.
- **Upstream CSV Data Source**: The raw stock CSVs in `Deep-Reinforcement-Learning-with-Stock-Trading` were assumed accurate with respect to market prices.

---

## 4. Conclusion

**Verdict**: **REQUEST_CHANGES**

`data_pipeline.py` creates a well-formatted output CSV (`processed_market_dynamics.csv`) with zero missing values and solid fallback paths. However, **REQUEST_CHANGES** is issued due to:
1. **Temporal lookahead leakage in regime assignment** (future data influences historical regime features).
2. **Cross-asset boundary jumping in HMM fitting** (missing `lengths` parameter).
3. **Extreme unscaled outlier spikes ($10^8$) in `shadow_ratio`**.

---

## 5. Verification Method

To independently verify these findings:

1. **Run Output CSV Inspection**:
   ```bash
   python -c "import pandas as pd; df = pd.read_csv('data/processed_market_dynamics.csv'); print(df.shape); print(df['shadow_ratio'].max()); print((df['corwin_schultz_spread']==0).mean())"
   ```
   - Expect shape `(79380, 29)`, `shadow_ratio` max `1e8`, and ~45.97% zero spread.

2. **Run Temporal Leakage Check**:
   ```bash
   python ".agents/teamwork_preview_reviewer_m1_2/scratch/thorough_verification.py"
   ```
   - Inspect Step 4 output confirming max regime posterior difference $> 0.30$.
