# Milestone 1 Data Quality & Feature Correctness Review Report

**Target File**: `data_pipeline.py`  
**Output Dataset**: `data/processed_market_dynamics.csv`  
**Reviewer**: Reviewer 2 (Data Quality, Feature Distribution & Mathematical Correctness)  
**Date**: 2026-07-31  

---

## Executive Review Summary

**Verdict**: **REQUEST_CHANGES**

While `data_pipeline.py` successfully generates a full dataset of 79,380 rows across 28 DJIA tickers with zero missing values (0 NaNs / 0 Infs) and functional fallback mechanisms (GARCH fallback and HMM $\to$ GMM $\to$ KMeans fallback work properly), there are **critical temporal lookahead data leakage issues**, **cross-asset HMM boundary violations**, and **extreme unbounded feature outliers ($10^8$)** that invalidate downstream RL model training if uncorrected.

---

## Key Findings

### 1. [Major] Temporal Lookahead Data Leakage in Market Regime Assignment
- **Where**: `data_pipeline.py`, lines 183–204 (`fit_and_assign_market_regimes`)
- **Why**: `fit_and_assign_market_regimes` performs Z-score feature standardization (`mean_f`, `std_f`) and fits `GaussianHMM` / `GaussianMixture` globally on the entire concatenated 11-year dataset (`combined_df` spanning 2009-02-03 to 2020-05-07).
- **Impact**: 
  1. The regime transition matrices, emission distributions, and normalization statistics on day $t$ in 2010 incorporate information from future dates up to May 2020.
  2. In automated verification, truncating the dataset to the first half shifted historical regime posteriors by up to **0.308002** (a 30.8% probability shift), proving significant lookahead bias.
  3. When an RL agent is trained/evaluated on train/val/test splits, test-set distribution statistics leak into historical regime feature columns (`regime_state_0`, `regime_state_1`, `regime_state_2`, `regime_label`).
- **Suggested Fix**: Fit regime models on an expanding/rolling window or compute normalization and regime parameters strictly on the training partition, applying `predict_proba` causally or using online state filtering.

### 2. [Major] Cross-Asset HMM Sequence Boundary Contamination
- **Where**: `data_pipeline.py`, lines 188–204 (`fit_and_assign_market_regimes`)
- **Why**: `combined_df` is built by concatenating ticker dataframes end-to-end (`pd.concat(processed_dfs, ignore_index=True)`). When passed to `GaussianHMM.fit(X_scaled)`, `hmmlearn` treats all 79,380 rows as a single continuous time series.
- **Impact**: `GaussianHMM` models consecutive transitions $P(S_t \mid S_{t-1})$. Line 202 omits the `lengths` argument (e.g. `lengths=[2835]*28`). As a result, the HMM treats the transition from AAPL's final row (2020-05-07) to AXP's initial row (2009-02-03) as a valid single-step temporal state transition, corrupting transition probability estimation.
- **Suggested Fix**: Pass `lengths=[len(df_single_asset)] * num_assets` to `hmm.fit()` or fit regime models per-asset / per-cross-section.

### 3. [Major] Unbounded Outlier Spikes in `shadow_ratio` ($10^8$)
- **Where**: `data_pipeline.py`, lines 149–151 (`engineer_asset_features`)
- **Why**: `shadow_ratio` is calculated as `df['shadow_upper'] / (df['shadow_lower'] + 1e-8)`. When `shadow_lower` is `0.0` (which occurs in 3.97% of trading days), the denominator reduces to `1e-8`, scaling `shadow_upper` by $10^8$.
- **Impact**: Feature statistics reveal a maximum value of **$1.000000 \times 10^8$** (100 million). Such high magnitude outliers will cause gradient instability or exploding activations when fed into deep neural networks (DDPG / PPO / SAC policy/value networks).
- **Suggested Fix**: Clip `shadow_ratio` (e.g. `np.clip(df['shadow_ratio'], 0.0, 10.0)` or `df['shadow_upper'] - df['shadow_lower']`) or use log-ratio scaling.

### 4. [Minor] High Proportion of Zero Values in Corwin-Schultz Spread (45.97% Zeros)
- **Where**: `data_pipeline.py`, lines 100–106 (`compute_corwin_schultz_spread`)
- **Why**: Daily Corwin-Schultz estimation sets negative $\alpha$ values to 0.0 (`if alpha < 0: s = 0.0`).
- **Impact**: 45.97% of all rows in `corwin_schultz_spread` are exact 0.0 values due to overnight price jumps or intraday variance noise exceeding 2-day combined variance.
- **Suggested Fix**: Apply a rolling moving average (e.g. 5-day EMA) to smooth `corwin_schultz_spread` and reduce zero-inflation.

---

## Verified Claims

| Claim / Requirement | Verification Method | Result | Notes |
|-------------------|-------------------|--------|-------|
| 28 DJIA Assets processed (excluding UTX, DOW) | Automated Python inspection of `processed_market_dynamics.csv` | **PASS** | Exactly 28 tickers present: AAPL, AXP, BA, CAT, CSCO, CVX, DIS, GS, HD, IBM, INTC, JNJ, JPM, KO, MCD, MMM, MRK, MSFT, NKE, PFE, PG, TRV, UNH, V, VZ, WBA, WMT, XOM. UTX and DOW excluded. |
| Row count and Date Indexing | Groupby inspection by `tic` and `date` | **PASS** | 2835 rows per ticker (79,380 total rows). Exactly 28 tickers present on all 2835 dates (2009-02-03 to 2020-05-07). Formatted `YYYY-MM-DD`, sorted by `[date, tic]`. |
| Null / NaN / Inf counts | `df.isna().sum()` and `np.isinf().sum()` | **PASS** | 0 NaNs and 0 Infs across all 29 columns. |
| Non-Zero Feature Variances | `df[col].std()` calculation across all numeric columns | **PASS** | All 27 numeric feature columns have positive non-zero standard deviations. |
| GARCH Fallback Mechanism | Forced `HAS_ARCH=False` and invoked `fallback_garch11` | **PASS** | `fallback_garch11` executes cleanly and outputs valid conditional volatility estimates ($0.0129$ to $0.0528$). |
| HMM Fallback Mechanism | Forced `HAS_HMM=False` and invoked `fit_and_assign_market_regimes` | **PASS** | Smoothly falls back to `GaussianMixture` (GMM) and assigns regime probabilities. |
| No Data Leakage Across Time | Truncated dataset fit vs Full dataset fit comparison | **FAIL** | Historical regime posteriors shift by up to **0.3080** when future data is truncated. Future lookahead leakage confirmed. |
| Cross-Asset HMM Boundaries | Code inspection of `GaussianHMM.fit` invocation | **FAIL** | Concatenated multi-asset data passed without `lengths` sequence array, creating artificial cross-ticker transitions. |

---

## Feature Distribution Summary Table

| Feature Name | Mean | Std Dev | Min | Max | Zeros % | Status / Assessment |
|--------------|------|---------|-----|-----|---------|---------------------|
| `open` | 78.74 | 55.48 | 3.01 | 446.01 | 0.0% | Normal stock price range |
| `high` | 79.41 | 55.97 | 3.13 | 446.01 | 0.0% | Normal stock price range |
| `low` | 78.05 | 54.97 | 2.94 | 440.19 | 0.0% | Normal stock price range |
| `close` | 78.75 | 55.48 | 2.97 | 440.62 | 0.0% | Normal stock price range |
| `adj_close` | 63.35 | 49.88 | 2.51 | 430.30 | 0.0% | Normal stock price range |
| `volume` | 2.53e+07 | 7.36e+07 | 3.05e+05 | 1.88e+09 | 0.0% | Normal trading volume |
| `return` | 6.68e-04 | 1.61e-02 | -0.2385 | 0.2467 | 0.65% | Valid daily returns |
| `log_return` | 5.38e-04 | 1.61e-02 | -0.2724 | 0.2205 | 0.65% | Valid log returns |
| `ewma_vol` | 1.39e-02 | 7.97e-03 | 3.48e-03 | 0.1196 | 0.0% | Well-behaved EWMA volatility |
| `volatility_ratio_5_21` | 0.9331 | 0.3747 | 0.0328 | 2.1341 | 0.0% | Well-behaved short/long vol ratio |
| `garman_klass_vol` | 1.09e-02 | 7.69e-03 | 1.30e-03 | 0.3285 | 0.0% | Valid Garman-Klass volatility |
| `garch_vol` | 1.53e-02 | 5.50e-03 | 7.83e-03 | 0.0997 | 0.0% | Valid GARCH(1,1) volatility |
| `shadow_upper` | 0.2685 | 0.2049 | 0.0 | 1.0000 | 4.08% | Normal range [0, 1] |
| `shadow_lower` | 0.2842 | 0.2112 | 0.0 | 1.0000 | 3.97% | Normal range [0, 1] |
| `shadow_ratio` | 1.296e+06 | 7.877e+06 | 0.0 | **1.000e+08** | 4.08% | **CRITICAL OUTLIER SPIKE ($10^8$)** |
| `vwap` | 78.37 | 55.21 | 3.15 | 422.07 | 0.0% | Valid 21-day rolling VWAP |
| `vwap_distance` | 5.97e-03 | 3.59e-02 | -0.4664 | 0.4000 | 0.0% | Normalized VWAP distance |
| `order_flow_imbalance` | 6.56e+05 | 7.78e+07 | -1.88e+09 | 1.87e+09 | 0.65% | Valid sign(ret) * volume |
| `corwin_schultz_spread` | 4.08e-03 | 6.19e-03 | 0.0 | 0.1277 | **45.97%** | 45.97% zero values |
| `return_shock_zscore` | -1.58e-02 | 0.9864 | -4.2228 | 4.2634 | 0.0% | Standardized z-score |
| `return_jump_indicator` | 6.74e-03 | 8.18e-02 | 0 | 1 | 99.33% | Binary jump indicator (0.67% jumps) |
| `volume_spike_index` | 1.0054 | 0.4097 | 0.1561 | 11.5261 | 0.0% | Valid volume ratio |
| `joint_vol_vol_shock` | -3.75e-02 | 1.5312 | -32.8515 | 28.7977 | 0.0% | Valid joint shock interaction |
| `regime_state_0` | 0.7026 | 0.3766 | 0.0 | 0.9866 | 0.88% | Bullish low-vol probability |
| `regime_state_1` | 0.2602 | 0.3439 | 0.0 | 0.9847 | 0.0% | Neutral regime probability |
| `regime_state_2` | 0.0372 | 0.1654 | 0.0 | 1.0000 | 0.0% | Bearish high-vol probability |
| `regime_label` | 0.2929 | 0.5201 | 0 | 2 | 73.88% | Categorical regime index (0, 1, 2) |

---

## Adversarial Stress Test & Integrity Evaluation

1. **Integrity Violation Check**:
   - Source code inspected for hardcoded outputs, dummy values, or facade logic.
   - **Result**: No integrity violations found. Mathematical feature functions reflect true financial indicators. Fallbacks are genuinely functional.

2. **Edge Case & Numerical Stability Tests**:
   - Zero division in `shadow_ratio`: **Vulnerable**. Division by `(shadow_lower + 1e-8)` produces values of $10^8$.
   - Negative variance in Garman-Klass or EWMA: **Protected**. `np.maximum(0.0, var)` prevents negative square roots.
   - Corwin-Schultz negative alpha: **Protected from NaN**, but thresholding to 0 yields 46% zeros.

---

## Recommendations for Implementer

1. **Fix Temporal Lookahead Leakage in Market Regimes**:
   - Standardize `features` using expanding historical means/stds or training split parameters.
   - Train HMM / GMM strictly on historical training split (e.g. 2009–2018) before transforming test data.
2. **Pass Sequence Lengths to `GaussianHMM`**:
   - Change line 202 to: `hmm.fit(X_scaled, lengths=[len(df_single_asset)] * num_assets)`.
3. **Cap / Clip `shadow_ratio` Outliers**:
   - Apply `np.clip(df['shadow_ratio'], 0.0, 10.0)` or compute `df['shadow_upper'] - df['shadow_lower']`.
4. **Smooth `corwin_schultz_spread`**:
   - Use a 5-day rolling exponential moving average to mitigate zero-inflation.
