# Data Engineering Pipeline Review Report (Milestone 1)

**Reviewer**: Reviewer 1 (Data Engineering Specialist & Adversarial Critic)  
**Target Code**: `data_pipeline.py`  
**Target Output Dataset**: `data/processed_market_dynamics.csv`  
**Date**: 2026-07-31  

---

## Review Summary

**Verdict**: **APPROVE**

The data engineering pipeline implemented in `data_pipeline.py` is mathematically sound, robustly implemented, and adheres strictly to quantitative finance and data pipeline specifications for Milestone 1. The feature engineering covers all four core market dynamics modules (Volatility Clustering, Spoofing Proxies, News Shocks, and Market Regimes) with valid mathematical formulations, appropriate fallback mechanics, and clean NaN/date handling.

---

## Detailed Findings & Verification

### 1. Asset Inclusion & Exclusion Verification
- **Explicit List**: `DJIA_28_TICKERS` contains exactly 28 tickers: `['AAPL', 'AXP', 'BA', 'CAT', 'CSCO', 'CVX', 'DIS', 'GS', 'HD', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE', 'PFE', 'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT', 'XOM']`.
- **Exclusion of `UTX` & `DOW`**: `UTX` and `DOW` are excluded from `DJIA_28_TICKERS`. While `EXCLUDED_TICKERS = ['UTX', 'DOW']` is defined at line 37 as an unused global variable, iterating explicitly over `DJIA_28_TICKERS` in `run_pipeline()` guarantees that `UTX` and `DOW` are omitted from processing.

### 2. Volatility Clustering Features
- **EWMA Volatility (`ewma_vol`)**: Implements exponential smoothing with $\alpha = 0.06$ ($\lambda = 0.94$, standard RiskMetrics parameter). Applies variance calculation on clean returns and takes `np.sqrt(np.maximum(0.0, ewma_var))` to guarantee non-negative volatility values.
- **Volatility Ratio 5d/21d (`volatility_ratio_5_21`)**: Computed as `vol_5d / (vol_21d + 1e-8)` using sample standard deviation (`ddof=1`). Epsilon prevents division by zero during flat price periods.
- **Garman-Klass Volatility (`garman_klass_vol`)**: Uses the standard Garman-Klass (1980) formula:
  $$\sigma_{GK} = \sqrt{\max\left(0, 0.5 \left(\ln \frac{H}{L}\right)^2 - (2\ln 2 - 1) \left(\ln \frac{C}{O}\right)^2\right)}$$
  Correctly handles edge cases where high equals low or close equals open via logarithm division guards and clipping.
- **GARCH(1,1) Conditional Volatility (`garch_vol`)**: Uses `arch_model` when available with standard scaling ($r \times 100$). Includes a robust variance-targeting fallback (`fallback_garch11`) with parameters $\alpha=0.05, \beta=0.90, \omega=(1-\alpha-\beta)\text{Var}(r)$ if the `arch` package is absent or fails to converge.

### 3. Spoofing Proxies
- **Shadow Ratios (`shadow_upper`, `shadow_lower`, `shadow_ratio`)**: Computes upper and lower candle wick lengths relative to total high-low range $HL = H - L + 1e-8$. `shadow_ratio` correctly quantifies relative upper vs. lower wick imbalance.
- **VWAP Distance (`vwap_distance`)**: Calculates 21-day rolling Volume-Weighted Average Price using typical price $TP = (H + L + C) / 3$:
  $$\text{VWAP}_{21} = \frac{\sum_{i=0}^{20} TP_i \cdot V_i}{\sum_{i=0}^{20} V_i + \epsilon}, \quad \text{VWAP\_Distance} = \frac{C - \text{VWAP}_{21}}{\text{VWAP}_{21} + \epsilon}$$
- **Order Flow Imbalance (`order_flow_imbalance`)**: Implements the Lee-Ready trade-signed volume proxy: $\text{OFI}_t = \operatorname{sign}(\Delta \text{Close}_t) \times \text{Volume}_t$.
- **Corwin-Schultz Bid-Ask Spread (`corwin_schultz_spread`)**: Implements the full high-low spread estimator from Corwin & Schultz (2012):
  $$\gamma = \left[\ln\left(\frac{H_{t-1,t}}{L_{t-1,t}}\right)\right]^2, \quad \beta = \left[\ln\left(\frac{H_{t-1}}{L_{t-1}}\right)\right]^2 + \left[\ln\left(\frac{H_t}{L_t}\right)\right]^2$$
  $$\alpha = \frac{\sqrt{2\beta} - \sqrt{\beta}}{3 - 2\sqrt{2}} - \sqrt{\frac{\gamma}{3 - 2\sqrt{2}}}, \quad S = \max\left(0, \frac{2(e^\alpha - 1)}{1 + e^\alpha}\right)$$
  Properly handles negative $\alpha$ by setting spread to zero per the Corwin-Schultz specification.

### 4. News Shocks
- **Return Shock Z-Score (`return_shock_zscore`)**: Standardized return relative to 21-day rolling mean and standard deviation: $Z_t = (r_t - \mu_{21}) / (\sigma_{21} + \epsilon)$.
- **Return Jump Indicator (`return_jump_indicator`)**: Binary flags $\mathbb{I}(|Z_t| > 3.0)$ identifying price jumps beyond 3 standard deviations.
- **Volume Spike Index (`volume_spike_index`)**: Volume relative to 21-day moving average volume: $V_t / (\overline{V}_{21} + \epsilon)$.
- **Joint Volatility-Volume Shock (`joint_vol_vol_shock`)**: Interaction product $Z_t \times \text{VolumeSpike}_t$, capturing abnormal returns co-occurring with trading volume surges.

### 5. Market Regimes (3-State Model)
- **Model Hierarchy**: Attempts 3-state `GaussianHMM`, falls back to `GaussianMixture`, and finally `KMeans` with soft exponential probability weighting if dependencies are missing.
- **State Label Stabilization**: Sorts fitted regime components using the economic state score:
  $$\text{Score}_k = \mu_{\text{return}, k} - 2 \cdot \mu_{\text{volatility}, k}$$
  Maps highest score to State 0 (Bullish Low-Vol), middle to State 1 (Neutral), and lowest to State 2 (Bearish High-Vol). This guarantees label consistency across training runs.

### 6. Code Safety, Error Handling, and Alignment
- **NaN Handling**: Rolling features drop the initial 20 incomplete rows per asset (`dropna()`). The final dataset has a fallback `ffill().bfill().fillna(0.0)` guard to ensure zero NaNs in exported outputs.
- **Date Alignment**: Output dataset is sorted by `['date', 'tic']`, ensuring uniform multi-asset row ordering suitable for reinforcement learning environment observations.

---

## Integrity Check

- **Hardcoded Outputs**: None detected. All features are calculated dynamically from input price/volume series.
- **Facade Implementations**: None detected. Full mathematical estimators are used throughout.
- **Delegation Shortcuts**: None detected.
- **Self-Certifying Work**: None detected. Code was independently analyzed against mathematical finance definitions.

---

## Recommendations / Minor Code Hygiene

1. **Remove Unused Variable**: Remove line 37 (`EXCLUDED_TICKERS = ['UTX', 'DOW']`) or add an explicit assertion `assert all(t not in DJIA_28_TICKERS for t in EXCLUDED_TICKERS)` in `run_pipeline()` to clear dead code.
2. **Explicit Type Casting**: Ensure `date` column retains standard ISO format `YYYY-MM-DD` on CSV export (handled via `dt.strftime('%Y-%m-%d')`).
