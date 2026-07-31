# Handoff Report: 567-Dimensional State Vector Composition & Calculation Analysis

**Agent ID**: explorer_m1_2  
**Target Milestone**: M1 - Live Data & Inference Pipeline  
**Working Directory**: `f:/SURE Trust/Capstone Project/RL_Paper_Trading_Deployment/.agents/explorer_m1_2`  
**Date**: 2026-07-31  

---

## 1. Observation

### Source Code Artifacts Examined
- **`custom_env.py`**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/custom_env.py`
  - Lines 14–20: Definition of `DEFAULT_TECH_INDICATORS` (17 indicators).
  - Lines 88–95: Observation space dimensions definition `obs_dim = 1 + 28 + 28 + (28 * 17) + 3 + 3 + 28 = 567`.
  - Lines 113–136: `_prepare_matrices()` method pivot and stack logic.
  - Lines 137–169: `_get_observation(day)` state vector construction and `np.nan_to_num` handling.
  - Lines 270–287: Portfolio return memory, drawdown tracking, and downside volatility calculation.
- **`data_pipeline.py`**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data_pipeline.py`
  - Lines 31–35: List of 28 DJIA tickers: `['AAPL', 'AXP', 'BA', 'CAT', 'CSCO', 'CVX', 'DIS', 'GS', 'HD', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE', 'PFE', 'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT', 'XOM']`.
  - Lines 40–72: GARCH(1,1) conditional volatility calculation and fallback heuristic `fallback_garch11`.
  - Lines 74–109: Corwin-Schultz High-Low Bid-Ask Spread proxy calculation `compute_corwin_schultz_spread`.
  - Lines 111–186: Feature engineering function `engineer_asset_features`.
  - Lines 188–264: 3-State Gaussian HMM / GMM / KMeans regime assignment `fit_and_assign_market_regimes`.

### Direct Verification Script Output
Executing `verify_obs.py` against `processed_market_dynamics.csv` using `custom_env.StockTradingEnv`:
```text
Testing environment observation space...
Observation shape: (567,)
Observation dtype: float32
Expected obs dim: 567, Actual: 567
1. Cash norm shape: (1,), sample: [1.]
2. Shares scaled shape: (28,)
3. Prices shape: (28,)
4. Tech feats shape: (476,) (28 * 17 = 476)
5. Regime probs shape: (3,), sample: [3.0708037e-05 9.6557844e-01 3.4390859e-02]
6. Risk state shape: (3,), sample: [0. 1. 0.]
7. Prev actions shape: (28,)
Verification SUCCESSful!
```

---

## 2. Logic Chain & Component Breakdown

### 2.1 Overview of 567-Dimensional Observation Vector
The observation space is a 1D NumPy array of shape `(567,)` with `dtype=np.float32`. It is formed by concatenating 7 distinct groups:

| Sub-Vector Component | Slice Index Range | Dimension | Description / Formula |
| :--- | :--- | :--- | :--- |
| **1. Cash Norm** | `[0:1]` | 1 | `self.cash / self.initial_amount` |
| **2. Shares Scaled** | `[1:29]` | 28 | `self.shares * 1e-4` for 28 tickers in sorted order |
| **3. Current Prices** | `[29:57]` | 28 | Adjusted Close prices for 28 tickers in sorted order |
| **4. Technical Features** | `[57:533]` | 476 | 28 assets × 17 indicators = 476 values (flattened asset by asset) |
| **5. Market Regime Probs** | `[533:536]` | 3 | Probabilities for `[State 0 (Bullish), State 1 (Neutral), State 2 (Bearish)]` |
| **6. Risk State** | `[536:539]` | 3 | `[drawdown, peak_net_worth / initial_amount, downside_vol]` |
| **7. Prev Actions** | `[539:567]` | 28 | Continuous actions `[-1.0, 1.0]` from previous step for 28 tickers |

**Total Dimension**: $1 + 28 + 28 + 476 + 3 + 3 + 28 = 567$.

---

### 2.2 Ticker & Technical Feature Alignment
Tickers are strictly sorted alphabetically:
`['AAPL', 'AXP', 'BA', 'CAT', 'CSCO', 'CVX', 'DIS', 'GS', 'HD', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE', 'PFE', 'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT', 'XOM']`

#### Stacking and Flattening Order for Technical Features (`[57:533]`):
In `custom_env.py` (`_prepare_matrices`), `tech_array` is transposed to shape `(num_dates, 28, 17)`. When `self.tech_array[day].flatten()` is called in C-order, the features are flattened **ticker by ticker**.

For asset $i \in [0, 27]$, its 17 technical indicators occupy indices `57 + i*17` through `57 + (i+1)*17 - 1`:

```
Indices 57..73   : AAPL (Indicators 0..16)
Indices 74..90   : AXP  (Indicators 0..16)
...
Indices 516..532 : XOM  (Indicators 0..16)
```

The 17 Technical Indicators for each asset appear in this exact order:

| Index | Indicator Name | Category | Calculation Formula / Code |
| :--- | :--- | :--- | :--- |
| 0 | `return` | Price Return | `df['adj_close'].pct_change()` |
| 1 | `log_return` | Price Return | `np.log(df['adj_close'] / df['adj_close'].shift(1))` |
| 2 | `ewma_vol` | Volatility | EWMA of squared returns ($\alpha=0.06$, $\lambda=0.94$): `np.sqrt((clean_ret**2).ewm(alpha=0.06, adjust=False).mean())` |
| 3 | `volatility_ratio_5_21` | Volatility Ratio | Ratio of 5-day to 21-day rolling standard deviations: `rolling(5).std() / (rolling(21).std() + 1e-8)` |
| 4 | `garman_klass_vol` | Volatility | Garman-Klass volatility: $\sqrt{0.5 \ln(H/L)^2 - (2\ln 2 - 1) \ln(C/O)^2}$ |
| 5 | `garch_vol` | Volatility | GARCH(1,1) conditional volatility via `arch` library or `fallback_garch11` heuristic |
| 6 | `shadow_upper` | Price Action | Upper shadow relative to high-low range: `(high - max(open, close)) / (high - low + 1e-8)` |
| 7 | `shadow_lower` | Price Action | Lower shadow relative to high-low range: `(min(open, close) - low) / (high - low + 1e-8)` |
| 8 | `shadow_ratio` | Price Action | Ratio of upper to lower shadow clipped to `[0.0, 10.0]`: `np.clip(shadow_upper / (shadow_lower + 1e-8), 0.0, 10.0)` |
| 9 | `vwap` | Price / Volume | 21-day rolling Volume Weighted Average Price: `rolling(21).sum(TP * Vol) / rolling(21).sum(Vol)` |
| 10 | `vwap_distance` | Price / Volume | Fractional distance from VWAP: `(close - vwap_21) / (vwap_21 + 1e-8)` |
| 11 | `order_flow_imbalance` | Volume Proxy | Signed volume based on close-to-close change: `np.sign(close.diff().fillna(0)) * volume` |
| 12 | `corwin_schultz_spread` | Microstructure | Corwin-Schultz High-Low Bid-Ask Spread proxy smoothed via 5-day EMA (`ewm(span=5)`) |
| 13 | `return_shock_zscore` | News Shock | Z-score of return relative to 21-day rolling window: `(return - mu_21) / (sigma_21 + 1e-8)` |
| 14 | `return_jump_indicator` | News Shock | Binary jump indicator: `(abs(return_shock_zscore) > 3.0).astype(int)` |
| 15 | `volume_spike_index` | News Shock | Volume relative to 21-day SMA volume: `volume / (sma_v_21 + 1e-8)` |
| 16 | `joint_vol_vol_shock` | News Shock | Interaction term: `return_shock_zscore * volume_spike_index` |

---

### 2.3 Detailed Technical Indicator Calculation Specifications

#### 1. Price Returns
```python
df['return'] = df['adj_close'].pct_change()
df['log_return'] = np.log(df['adj_close'] / df['adj_close'].shift(1))
```

#### 2. EWMA Volatility
```python
clean_ret = df['return'].fillna(0.0)
ret_sq = clean_ret ** 2
ewma_var = ret_sq.ewm(alpha=0.06, adjust=False).mean()
df['ewma_vol'] = np.sqrt(np.maximum(0.0, ewma_var))
```

#### 3. Volatility Ratio (5d / 21d)
```python
vol_5d = df['return'].rolling(window=5).std(ddof=1)
vol_21d = df['return'].rolling(window=21).std(ddof=1)
df['volatility_ratio_5_21'] = vol_5d / (vol_21d + 1e-8)
```

#### 4. Garman-Klass Volatility
```python
high = np.maximum(df['high'], 1e-8)
low = np.maximum(df['low'], 1e-8)
open_p = np.maximum(df['open'], 1e-8)
close_p = np.maximum(df['close'], 1e-8)
h_l = np.log(high / low)
c_o = np.log(close_p / open_p)
gk_var = 0.5 * (h_l ** 2) - (2.0 * np.log(2.0) - 1.0) * (c_o ** 2)
df['garman_klass_vol'] = np.sqrt(np.maximum(0.0, gk_var))
```

#### 5. GARCH(1,1) Conditional Volatility
```python
def fallback_garch11(returns, alpha=0.05, beta=0.90):
    r = returns.values
    n = len(r)
    var_sample = np.var(r[1:]) if n > 1 else 1e-4
    omega = (1.0 - alpha - beta) * var_sample
    sigma2 = np.zeros(n)
    sigma2[0] = max(1e-6, var_sample)
    for t in range(1, n):
        sigma2[t] = omega + alpha * (r[t-1] ** 2) + beta * sigma2[t-1]
    return np.sqrt(np.maximum(1e-10, sigma2))

def compute_garch_volatility(returns):
    clean_ret = returns.fillna(0.0)
    if HAS_ARCH:
        try:
            am = arch_model(clean_ret * 100.0, vol='Garch', p=1, q=1, dist='Normal', rescale=False)
            res = am.fit(disp='off', show_warning=False)
            return res.conditional_volatility.values / 100.0
        except Exception:
            pass
    return fallback_garch11(clean_ret)
```

#### 6. Candlestick Shadows & Ratio
```python
max_oc = np.maximum(df['open'], df['close'])
min_oc = np.minimum(df['open'], df['close'])
hl_range = df['high'] - df['low'] + 1e-8

df['shadow_upper'] = (df['high'] - max_oc) / hl_range
df['shadow_lower'] = (min_oc - df['low']) / hl_range
df['shadow_ratio'] = np.clip(df['shadow_upper'] / (df['shadow_lower'] + 1e-8), 0.0, 10.0)
```

#### 7. VWAP & VWAP Distance
```python
tp = (df['high'] + df['low'] + df['close']) / 3.0
cum_vol_price = (tp * df['volume']).rolling(window=21).sum()
cum_vol = df['volume'].rolling(window=21).sum()
vwap_21 = np.where(cum_vol > 0, cum_vol_price / (cum_vol + 1e-8), df['close'])
df['vwap'] = vwap_21
df['vwap_distance'] = (df['close'] - vwap_21) / (vwap_21 + 1e-8)
```

#### 8. Order Flow Imbalance Proxy
```python
delta_close = df['close'].diff()
df['order_flow_imbalance'] = np.sign(delta_close.fillna(0.0)) * df['volume']
```

#### 9. Corwin-Schultz Spread Proxy
```python
def compute_corwin_schultz_spread(high, low):
    high_vals, low_vals = high.values, low.values
    n = len(high_vals)
    spread = np.zeros(n)
    k2 = 3.0 - 2.0 * np.sqrt(2.0)  # ~0.171572875
    
    for t in range(1, n):
        h_prev, l_prev = high_vals[t-1], low_vals[t-1]
        h_curr, l_curr = high_vals[t], low_vals[t]
        h2 = max(h_prev, h_curr)
        l2 = min(l_prev, l_curr)
        if l_prev <= 0 or l_curr <= 0 or l2 <= 0:
            continue
        gamma = (np.log(h2 / l2)) ** 2
        beta = (np.log(h_prev / l_prev)) ** 2 + (np.log(h_curr / l_curr)) ** 2
        alpha = (np.sqrt(2.0 * beta) - np.sqrt(beta)) / k2 - np.sqrt(gamma / k2)
        if np.isnan(alpha) or alpha < 0:
            s = 0.0
        else:
            s = 2.0 * (np.exp(alpha) - 1.0) / (1.0 + np.exp(alpha))
            s = max(0.0, s)
        spread[t] = s
    return spread

cs_raw = compute_corwin_schultz_spread(df['high'], df['low'])
df['corwin_schultz_spread'] = pd.Series(cs_raw, index=df.index).ewm(span=5, adjust=False).mean()
```

#### 10. News & Volume Shocks
```python
mu_21 = df['return'].rolling(window=21).mean()
sigma_21 = df['return'].rolling(window=21).std(ddof=1)
df['return_shock_zscore'] = (df['return'] - mu_21) / (sigma_21 + 1e-8)
df['return_jump_indicator'] = (df['return_shock_zscore'].abs() > 3.0).astype(int)

sma_v_21 = df['volume'].rolling(window=21).mean()
df['volume_spike_index'] = df['volume'] / (sma_v_21 + 1e-8)
df['joint_vol_vol_shock'] = df['return_shock_zscore'] * df['volume_spike_index']
```

---

### 2.4 HMM Market Regime Probability Calculation
Market regime probabilities are global across all 28 assets for any given trading day. The 3 states are fitted on standardized `['return', 'ewma_vol']` features across assets:

1. **Feature Input**: $X = [\text{return}, \text{ewma\_vol}]$
2. **Scaling**: $X_{\text{scaled}} = (X - \mu_X) / (\sigma_X + 1e-8)$
3. **Fallback Hierarchy**:
   - **Primary**: `GaussianHMM(n_components=3, covariance_type="full", n_iter=200, random_state=42)` fitted with `lengths` parameter per asset sequence. Computes posterior probabilities `predict_proba`.
   - **Secondary Fallback**: `GaussianMixture(n_components=3, random_state=42)` on $X_{\text{scaled}}$.
   - **Tertiary Fallback**: `KMeans(n_components=3, random_state=42, n_init=10)` on $X_{\text{scaled}}$. Computes distance-based exponential posteriors: $p_k = \frac{e^{-d_k}}{\sum_j e^{-d_j}}$.
4. **State Index Ordering & Mapping**:
   To ensure consistent semantic state mapping across fits:
   $$\text{score}_k = \mu_{\text{return}, k} - 2.0 \times \mu_{\text{ewma\_vol}, k}$$
   - **State 0 (Highest score)**: Bullish Low-Vol (`regime_state_0`)
   - **State 1 (Middle score)**: Neutral (`regime_state_1`)
   - **State 2 (Lowest score)**: Bearish High-Vol (`regime_state_2`)

Indices `[533:536]` contain: `[regime_state_0, regime_state_1, regime_state_2]`.

---

### 2.5 Risk State Calculation
Indices `[536:539]` represent 3 risk state metrics updated dynamically at each environment step:

1. **Drawdown** (`obs[536]`):
   $$\text{drawdown}_t = \max\left(0.0, \frac{\text{peak\_net\_worth}_t - \text{net\_worth}_t}{\text{peak\_net\_worth}_t + 1e-8}\right)$$
   Where $\text{peak\_net\_worth}_t = \max(\text{peak\_net\_worth}_{t-1}, \text{net\_worth}_t)$.
2. **Scaled Peak Net Worth** (`obs[537]`):
   $$\text{scaled\_peak}_t = \frac{\text{peak\_net\_worth}_t}{\text{initial\_amount}}$$
3. **Downside Volatility** (`obs[538]`):
   Calculated over the memory buffer `returns_memory` (last up to 21 daily portfolio returns $r_{p, \tau}$):
   $$\text{downside\_vol} = \sqrt{ \frac{1}{N} \sum_{\tau=1}^{N} \min(0.0, r_{p, \tau})^2 }$$
   If `returns_memory` is empty (e.g. at `reset()`), `downside_vol = 0.0`.

---

### 2.6 Prev Actions Vector
Indices `[539:567]` represent the continuous action vector assigned in the previous step:
- Size: 28 float32 values in range `[-1.0, 1.0]`.
- On `reset()`, initialized to `np.zeros(28, dtype=np.float32)`.
- At step $t$, updated to `action.copy()` (after clipping to `[-1.0, 1.0]`).

---

### 2.7 Array Assembly & `nan_to_num` Handling
In `custom_env.py` (`_get_observation`), vector assembly is executed as follows:

```python
cash_norm = np.array([self.cash / self.initial_amount], dtype=np.float32)
shares_scaled = (self.shares * 1e-4).astype(np.float32)
current_prices = self.price_array[day].astype(np.float32)
tech_feats = self.tech_array[day].flatten().astype(np.float32)
regime_probs = self.regime_array[day].astype(np.float32)
risk_state = np.array([self.drawdown, self.peak_net_worth / self.initial_amount, downside_vol], dtype=np.float32)

obs = np.hstack([
    cash_norm,        # [0:1]    (len 1)
    shares_scaled,    # [1:29]   (len 28)
    current_prices,   # [29:57]  (len 28)
    tech_feats,       # [57:533] (len 476)
    regime_probs,     # [533:536](len 3)
    risk_state,       # [536:539](len 3)
    self.prev_actions # [539:567](len 28)
], dtype=np.float32)

obs = np.nan_to_num(obs, nan=0.0, posinf=1e6, neginf=-1e6).astype(np.float32)
```

---

## 3. Caveats & Deployment Considerations

1. **Minimum Historical Window for Live Data Ingestion**:
   Calculating the 17 technical indicators requires at least **21 trading days** (ideally 30+ days) of past OHLCV data prior to the execution date to populate 21-day rolling windows (VWAP 21, rolling std 21d, Corwin-Schultz spread, return shock z-scores).
2. **Missing Ticker Protection**:
   The 28 tickers must follow the exact alphabetical order specified. If a ticker is missing or un-traded on a given day, forward-fill / backward-fill must be applied prior to state vector construction.
3. **`nan_to_num` Enforcement**:
   To prevent inference crashes in SB3 PPO (`optimal_trading_model.zip`), `np.nan_to_num(obs, nan=0.0, posinf=1e6, neginf=-1e6)` MUST be applied immediately before model prediction.

---

## 4. Conclusion
The observation space is deterministically structured as a 567-dimensional `float32` vector. This analysis provides the complete mathematical and programmatic specification needed for implementing live state vector construction in `trade_executor.py` for Milestone 1.

---

## 5. Verification Method

To verify the observation space structure independently:

1. Run the verification script:
   ```bash
   python "f:/SURE Trust/Capstone Project/RL_Paper_Trading_Deployment/.agents/explorer_m1_2/verify_obs.py"
   ```
2. Verify that output confirms shape `(567,)`, dtype `float32`, and non-NaN values for all 7 sub-vectors.
3. Invalidation conditions:
   - Total length $\neq 567$.
   - Any NaN or inf value remaining in observation vector.
   - Discrepancy in ticker alphabetical ordering or indicator flattening order.
