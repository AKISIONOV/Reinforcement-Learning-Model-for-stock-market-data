# Empirical Challenge Report: Milestone 1 Data Pipeline

**Target File**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data_pipeline.py`  
**Target Dataset**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv`  
**Author**: Challenger 1 (Empirical Challenger)  
**Date**: 2026-07-31  

---

## Challenge Summary

**Overall risk assessment**: **HIGH**

While `processed_market_dynamics.csv` currently contains clean output (79,380 rows, 0 NaNs, 0 Infs), adversarial empirical stress testing of `data_pipeline.py` revealed **two HIGH-severity vulnerabilities** and **one MEDIUM-severity numerical instability**, alongside a dataset elimination risk when processing edge-case market data.

---

## Challenges & Vulnerabilities

### [High] Challenge 1: Cross-Ticker Data Leakage via Global Forward Fill (`ffill()`)

- **Assumption challenged**: Global post-processing forward fill (`combined.ffill().bfill().fillna(0.0)`) preserves asset isolation after sorting by `['date', 'tic']`.
- **Attack scenario**: When `nan_count > 0` after feature concatenation in `run_pipeline`, the code executes:
  ```python
  combined['date'] = combined['date'].dt.strftime('%Y-%m-%d')
  combined = combined.sort_values(['date', 'tic']).reset_index(drop=True)
  if nan_count > 0:
      combined = combined.ffill().bfill().fillna(0.0)
  ```
  Sorting by `['date', 'tic']` places different assets on the same trading day in adjacent rows (Row $i$: Asset A, Row $i+1$: Asset B). A missing feature in Asset B at Row $i+1$ will be filled with Asset A's value from Row $i$.
- **Blast radius**: State leakage across tickers, invalidating independence in multi-asset reinforcement learning models.
- **Empirical Proof**: Test `T3.3` confirmed that when Asset B has a `NaN` on 2020-01-01 and Asset A has value `10.0` on 2020-01-01, global `.ffill()` overwrote Asset B's missing value with Asset A's `10.0`.
- **Mitigation**: Perform missing value imputation **per ticker before concatenation** or group by `tic` before fill:
  ```python
  combined = combined.groupby('tic', group_keys=False).apply(lambda df: df.ffill().bfill()).fillna(0.0)
  ```

---

### [High] Challenge 2: `Inf` Explosion in Garman-Klass Volatility when `high == 0.0`

- **Assumption challenged**: Logarithm denominators in Garman-Klass volatility computation are safe from zero values.
- **Attack scenario**: Lines 136–138 of `data_pipeline.py`:
  ```python
  h_l = np.log(df['high'] / np.maximum(df['low'], 1e-8))
  c_o = np.log(df['close'] / np.maximum(df['open'], 1e-8))
  gk_var = 0.5 * (h_l ** 2) - (2.0 * np.log(2.0) - 1.0) * (c_o ** 2)
  df['garman_klass_vol'] = np.sqrt(np.maximum(0.0, gk_var))
  ```
  If `high` drops to `0.0` (halted trading, bad tick data, zero-price edge cases), `df['high'] / np.maximum(df['low'], 1e-8) = 0.0`. `np.log(0.0)` produces `-inf`. Squaring `-inf` yields `+inf`, causing `garman_klass_vol` to become `+inf`.
- **Blast radius**: Neural network gradient explosion or training crash when feeding state features containing `+inf`.
- **Empirical Proof**: Test `T2.5` produced 6 `inf` values in `garman_klass_vol` when `high = 0.0`.
- **Mitigation**: Apply `np.maximum(..., 1e-8)` to `high` and `close` as well:
  ```python
  h_l = np.log(np.maximum(df['high'], 1e-8) / np.maximum(df['low'], 1e-8))
  c_o = np.log(np.maximum(df['close'], 1e-8) / np.maximum(df['open'], 1e-8))
  ```

---

### [Medium] Challenge 3: VWAP Distance Numerical Explosion ($10^9$) under Zero Volume

- **Assumption challenged**: Adding `1e-8` to rolling volume prevents extreme feature values in VWAP calculation.
- **Attack scenario**: Lines 155–159 of `data_pipeline.py`:
  ```python
  rolling_vol = df['volume'].rolling(window=21).sum()
  vwap_21 = rolling_tp_vol / (rolling_vol + 1e-8)
  df['vwap_distance'] = (df['close'] - vwap_21) / (vwap_21 + 1e-8)
  ```
  When volume is `0` over a 21-day window, `rolling_vol = 0`, giving `vwap_21 = 0 / 1e-8 = 0.0`. Subsequently, `vwap_distance = (close - 0) / (0 + 1e-8) = close / 1e-8 = close * 1e8`.
- **Blast radius**: At a stock price of \$100, `vwap_distance` reaches **9,780,000,000** ($9.78 \times 10^9$), completely distorting feature scaling for RL policy networks.
- **Empirical Proof**: Test `T1.3` recorded `vwap_distance` max magnitude of $9.78 \times 10^9$ when `volume = 0`.
- **Mitigation**: Clip `vwap_distance` to a reasonable numerical range (e.g. `[-10.0, 10.0]`) or fallback to `0.0` when `vwap_21 == 0`.

---

### [Low/Observation] Challenge 4: Data Elimination Risk on Short Sequences (<21 days) or Extended Zeroes

- **Assumption challenged**: `df.dropna().reset_index(drop=True)` safely removes initial 21-day rolling window NaNs.
- **Attack scenario**: Line 180:
  ```python
  df_clean = df.dropna().reset_index(drop=True)
  ```
  If an asset dataframe has <21 days or contains mid-series zero price sequences that generate NaNs in `pct_change()`, rolling windows propagate NaNs forward. `df.dropna()` purges **100% of rows**, silently dropping the entire asset from the pipeline.
- **Blast radius**: Total loss of asset data for newly listed tickers or assets with trading halts.
- **Empirical Proof**: Test `E1` and `E4` showed 50 out of 50 rows dropped when processing 10 consecutive zero prices or 15-day histories.
- **Mitigation**: Log warnings when rows are dropped and handle NaNs with targeted per-column fill logic before dropping rows.

---

## Stress Test Results Matrix

| Test ID | Test Description | Expected Behavior | Actual Behavior | Result | Severity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **T1.1** | Zero Prices Handling | Zero NaN / Inf values | No NaNs/Infs produced | **PASS** | NONE |
| **T1.2** | Negative Prices Handling | Zero NaN / Inf values | No NaNs/Infs produced | **PASS** | NONE |
| **T1.3** | Flat Zero Volume | Stable VWAP distance | `vwap_distance` exploded to $9.78 \times 10^9$ | **WARN** | MEDIUM |
| **T1.4** | Zero Volatility / Constant Price | Stable feature values | No NaNs/Infs produced | **PASS** | NONE |
| **T1.5** | Extreme Price Spikes (10,000x) | Stable feature values | No NaNs/Infs produced | **PASS** | NONE |
| **T1.6** | Malformed High < Low | Graceful handling | No NaNs/Infs produced | **PASS** | NONE |
| **T1.7** | Raw Input NaNs | Safe filtering | Input NaNs cleanly dropped | **PASS** | NONE |
| **T2.1** | GARCH Fallback vs `arch` | Consistent volatility output | Stable output across fallback | **PASS** | NONE |
| **T2.2** | Corwin-Schultz Spread Bounds | Finite spread values | Stable spread output | **PASS** | NONE |
| **T2.3** | Spoofing Proxy Bounds | `shadow_ratio` in $[0, 10]$ | `shadow_ratio` bounded in $[0.0, 10.0]$ | **PASS** | NONE |
| **T2.4** | News Shocks Zero Std | Finite Z-scores | `return_shock_zscore` stable | **PASS** | NONE |
| **T2.5** | Garman-Klass Zero High | Zero or finite volatility | **6 Infs produced** (`+inf`) | **FAIL** | HIGH |
| **T3.1** | Single-Asset Feature Isolation | Zero cross-asset variance | No state leakage across single assets | **PASS** | NONE |
| **T3.2** | HMM Sequence Lengths | Posteriors sum to 1.0 | Posterior probabilities sum to 1.0 | **PASS** | NONE |
| **T3.3** | Global `ffill()` Leakage | Asset-isolated forward fill | **Cross-ticker state leakage confirmed** | **FAIL** | HIGH |
| **T4.1** | Dataset Audit (`processed_market_dynamics.csv`) | 79,380 rows, 0 NaNs, 0 Infs | 79,380 rows, 0 NaNs, 0 Infs, valid labels | **PASS** | NONE |

---

## Unchallenged Areas

- **`arch` / GARCH optimization convergence internals**: Dependent on external C/Python `arch` library numerical solvers.
- **HMM model initializations**: Standard `random_state=42` used; convergence across arbitrary non-stationary distributions not fully stress-tested.
