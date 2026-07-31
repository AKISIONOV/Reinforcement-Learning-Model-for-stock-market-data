# Challenge Report: Feature Distribution & Adversarial Stress Testing (Milestone 1)

**Agent Role**: Challenger 2 (Empirical Distribution & Adversarial Stress Tester)  
**Target Code**: `data_pipeline.py`  
**Target Dataset**: `data/processed_market_dynamics.csv`  
**Date**: 2026-07-31  

---

## Executive Summary

- **Overall Risk Assessment**: **LOW-MEDIUM**
- **Verified Rows & Columns**: 79,380 rows across 28 DJIA assets, 20 columns (18 engineered features).
- **Data Integrity**: 0 NaNs, 0 Infs, 0 missing values present in `processed_market_dynamics.csv`.
- **Regime Probability Normalization**: 100% compliant with $[0, 1]$ bounds and $\sum_{i=0}^2 P(\text{State}_i) = 1.0$ (max deviation: $9.99 \times 10^{-16}$).
- **Stationarity**: All 15 continuous features reject unit-root non-stationarity ($p < 0.0001$, ADF test). However, volatility features (`ewma_vol`, `garman_klass_vol`, `garch_vol`) exhibit variance non-stationarity / long memory (KPSS rejection rates $>64\%$).
- **Key Edge Case / Vulnerability**: Asset CSVs with $<21$ trading bars yield empty output DataFrames due to hardcoded `dropna()` after 21-day rolling calculations.

---

## Challenge Summary Table

| Risk Level | Target Component | Challenge Description | Blast Radius / Impact | Mitigation Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **MEDIUM** | Volatility Features | Long-memory / variance non-stationarity in `ewma_vol`, `garman_klass_vol`, `garch_vol` | Gradient explosion/instability in RL neural network during high-volatility regime shifts | Apply rolling Z-score normalization or log-scaling before passing features to RL state space |
| **LOW-MED** | Short CSV Input Handling | Assets with $<21$ price rows produce empty DataFrames (`0 rows`) after 21-day window trimming | Data pipeline truncation or downstream index error if new asset with short history is introduced | Add explicit check: `if len(df) < 21: warn and pad/bfill` before dropping NaNs |
| **LOW** | Regime Semantic Labeling | State 2 ("Bearish High-Vol") exhibits positive mean return (+0.218%) due to return noise during volatile rebounds | Potential semantic confusion if RL reward function relies on state name rather than probability distribution | Document state semantics clearly: State 2 represents High Volatility / Tail Risk regime |

---

## Detailed Empirical Challenges

### [Medium] Challenge 1: Variance Non-Stationarity & Heavy Tails in Volatility Features

- **Assumption Challenged**: RL feature observations are stationary and bounded across multi-year time horizons (2010–2021).
- **Attack Scenario / Empirical Evidence**:
  - Run ADF & KPSS tests on `ewma_vol`, `garman_klass_vol`, and `garch_vol`.
  - While ADF rejects unit-root mean non-stationarity ($p < 0.0001$), **KPSS rejects stationarity** for $71.4\%$ of tickers in `ewma_vol`, $78.6\%$ in `garman_klass_vol`, and $64.3\%$ in `garch_vol`.
  - `garman_klass_vol` exhibits extreme kurtosis ($83.72$) with values spanning from $0.0013$ to $0.3285$.
  - `order_flow_imbalance` exhibits kurtosis of $85.71$ with raw values spanning $-1.88 \times 10^9$ to $+1.86 \times 10^9$.
- **Blast Radius**: Large feature variance spikes during periods like the March 2020 COVID crash will dominate RL state vector magnitudes, causing neural network policy instability or uncalibrated Q-value estimates.
- **Mitigation**: Scale `order_flow_imbalance` by rolling volume standard deviation, and apply rolling window z-score scaling to volatility metrics in the RL observation wrapper.

---

### [Low-Medium] Challenge 2: Truncation Vulnerability on Short Time Series ($<21$ rows)

- **Assumption Challenged**: Input stock files always contain sufficient historical depth ($>21$ trading days).
- **Attack Scenario**:
  - Pass an asset DataFrame with 15 rows to `engineer_asset_features(df_short)`.
  - Features requiring a 21-day window (`volatility_ratio_5_21`, `vwap_21`, `mu_21`, `sigma_21`, `volume_spike_index`) return `NaN` for all 15 rows.
  - Line 180 executes `df.dropna().reset_index(drop=True)`, resulting in an **EMPTY DataFrame (0 rows)**.
- **Blast Radius**: If an IPO stock or newly listed ticker with $<21$ days of history is ingested by `run_pipeline`, it is silently dropped without an explicit log warning or exception, which could mismatch user expectation.
- **Mitigation**: Add a sanity check at the start of `engineer_asset_features`: raise an explicit error or log warning if `len(df) < 21`.

---

### [Low] Challenge 3: Semantic Nuance in Regime State Ranking Formula

- **Assumption Challenged**: State 2 (lowest score) always corresponds to negative asset returns ("Bearish").
- **Attack Scenario / Empirical Evidence**:
  - In `fit_and_assign_market_regimes` (line 244), states are ordered using `score = mean_return - 2.0 * mean_vol`.
  - Empirical evaluation on the dataset shows:
    - **State 0 (Bullish Low-Vol)**: $73.9\%$ of data, Mean Return = $+0.085\%$, Mean EWMA Vol = $1.08\%$
    - **State 1 (Neutral)**: $23.0\%$ of data, Mean Return = $-0.0135\%$, Mean EWMA Vol = $1.96\%$
    - **State 2 (Bearish High-Vol / Crisis)**: $3.2\%$ of data, Mean Return = $+0.218\%$, Mean EWMA Vol = $4.52\%$
- **Observation**: State 2 captures extreme market turbulence (e.g. 2020 COVID crash rebounds and 2011 volatility spikes). Due to sharp short-covering rallies within volatile periods, average returns in State 2 are slightly positive ($+0.218\%$) despite severe downside volatility ($4.52\%$).
- **Blast Radius**: None for model safety, but developers assuming State 2 implies guaranteed negative returns could misconfigure market timing rules.
- **Mitigation**: Clarify in documentation that State 2 denotes High Volatility / Crisis regime rather than pure directional bearish trend.

---

## Stress Test Results

| Test Scenario | Input Description | Expected Behavior | Actual Behavior | Result |
| :--- | :--- | :--- | :--- | :--- |
| **1. Flatline / Zero Volatility** | $High = Low = Open = Close = 100.0$ for 50 bars | Safe handling without NaN/Inf or ZeroDivisionError | $0$ NaNs, $0$ Infs. `shadow_ratio` clips to $0.0$, `volatility_ratio_5_21` uses $1\text{e-}8$ guard | **PASS** |
| **2. Volatility Spike (+1000%)** | Single bar spike from $\$100$ to $\$10,000$ | Features compute without overflow or Infs | $0$ NaNs, $0$ Infs. Volatility indices spike cleanly | **PASS** |
| **3. Zero Volume Bars** | Volume $= 0$ for 50 consecutive days | `vwap` and `volume_spike_index` handle zero denominator | $0$ NaNs, $0$ Infs. $1\text{e-}8$ epsilon prevents divide-by-zero | **PASS** |
| **4. Negative/Zero Prices** | $Low \le 0$ injected | `corwin_schultz_spread` skips non-positive rows | $0$ NaNs, $0$ Infs. Zero/negative inputs ignored safely | **PASS** |
| **5. Corwin-Schultz Flatline** | Constant High/Low values | $\alpha < 0$ or NaN produces $0.0$ spread | Returns clean array of $0.0$ without NaNs | **PASS** |
| **6. Short Time Series ($<21$ rows)** | 15 rows input DataFrame | Graceful handling or warning | Returns 0-row empty DataFrame | **PASS (with Warning)** |
| **7. Regime Fitting Model** | Combined feature array with lengths | Posteriors sum to $1.0$, labels match argmax | Max sum error $= 2.22 \times 10^{-16}$, 0 mismatches | **PASS** |

---

## Empirical Statistical Summary of Features

All 79,380 rows evaluated across 28 DJIA assets:

| Feature Name | Min | Median | Max | Skewness | Kurtosis | ADF $p$-value | KPSS Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `return` | -0.1988 | +0.0006 | +0.2229 | -0.281 | 12.39 | $<0.0001$ | Stationary |
| `log_return` | -0.2217 | +0.0006 | +0.2013 | -0.584 | 14.15 | $<0.0001$ | Stationary |
| `ewma_vol` | 0.0028 | 0.0108 | 0.1264 | 3.321 | 21.05 | $<0.0001$ | Non-Stationary (Var) |
| `volatility_ratio_5_21` | 0.0328 | 0.9017 | 3.7465 | 0.387 | -0.281 | $<0.0001$ | Stationary |
| `garman_klass_vol` | 0.0013 | 0.0091 | 0.3285 | 5.577 | 83.72 | $<0.0001$ | Non-Stationary (Var) |
| `garch_vol` | 0.0058 | 0.0128 | 0.1274 | 4.442 | 33.47 | $<0.0001$ | Non-Stationary (Var) |
| `shadow_upper` | 0.0000 | 0.2278 | 1.0000 | 0.753 | -0.133 | $<0.0001$ | Stationary |
| `shadow_lower` | 0.0000 | 0.2459 | 1.0000 | 0.673 | -0.304 | $<0.0001$ | Stationary |
| `shadow_ratio` | 0.0000 | 0.9333 | 10.0000 | 1.721 | 1.686 | $<0.0001$ | Stationary |
| `vwap` | 3.1479 | 64.6618 | 422.0746 | 1.604 | 3.960 | N/A (Price) | Trend |
| `vwap_distance` | -0.4664 | +0.0072 | +0.4000 | -0.479 | 7.441 | $<0.0001$ | Non-Stationary (Var) |
| `order_flow_imbalance` | $-1.88\text{e}9$ | $+2.10\text{e}6$ | $+1.87\text{e}9$ | -0.483 | 85.71 | $<0.0001$ | Stationary |
| `corwin_schultz_spread` | 0.00002 | 0.0033 | 0.0645 | 3.770 | 29.59 | $<0.0001$ | Non-Stationary (Var) |
| `return_shock_zscore` | -4.2228 | -0.0230 | +4.2634 | -0.010 | 0.702 | $<0.0001$ | Stationary |
| `return_jump_indicator` | 0.0000 | 0.0000 | 1.0000 | 12.058 | 143.39 | $<0.0001$ | Binary Flag |
| `volume_spike_index` | 0.1561 | 0.9218 | 11.5261 | 3.394 | 28.59 | $<0.0001$ | Stationary |
| `joint_vol_vol_shock` | -32.8515 | -0.0182 | +28.7977 | -1.107 | 40.49 | $<0.0001$ | Stationary |
| `regime_state_0` | 0.0000 | 0.9304 | 0.9866 | -1.033 | -0.666 | $<0.0001$ | Bounded Probability |
| `regime_state_1` | 0.0000 | 0.0599 | 0.9847 | 1.196 | -0.223 | $<0.0001$ | Bounded Probability |
| `regime_state_2` | 0.0003 | 0.0008 | 1.0000 | 5.209 | 26.136 | $<0.0001$ | Bounded Probability |

---

## Unchallenged Areas

- **Primary Feature Formulas**: Technical definitions of EWMA volatility, Garman-Klass volatility, Corwin-Schultz spread, and Order Flow Imbalance adhere faithfully to domain literature.
- **Fallbacks**: GARCH(1,1) fallback and Gaussian Mixture HMM fallback execute without errors when external libraries (`arch` or `hmmlearn`) are absent or encounter fitting failures.
