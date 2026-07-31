# Challenge Report — Milestone 2 (RL Environment Trajectory & Fee Stress Testing)

**Target Codebase**: `custom_env.py`  
**Target Test Suite**: `test_custom_env.py` & `stress_harness_m2.py`  
**Date**: 2026-07-31  
**Agent**: Challenger 1 (`teamwork_preview_challenger_m2_1`)  

---

## Challenge Summary

**Overall Risk Assessment**: **MEDIUM**

While `custom_env.py` successfully demonstrates high resilience against NaN/Inf values, zero-division exceptions, and strictly enforces the 10 bps transaction fee ($0.001 \times \text{transaction value}$) on both buy and sell trades, **an empirical vulnerability was discovered in the single-precision weight normalization logic during multi-asset buy execution**. This flaw causes cash balances (`self.cash`) to drift below $0.00 (into small negative balances up to $-\$0.0625$), which subsequently blocks all future buy orders until shares are sold.

---

## Challenges

### [Medium] Challenge 1: Single-Precision (`float32`) Weight Normalization Truncation Causes Negative Cash Drift (`self.cash < 0`)

- **Assumption Challenged**: Sum of normalized buy weights $\sum w_i = \sum \frac{\text{action}_i}{\text{pos\_sum}}$ in single-precision floating point (`float32`) strictly equals $1.00000000$.
- **Attack Scenario / Empirical Reproduction**:
  1. Initialize `StockTradingEnv` with cash $\$1,000,000.00$.
  2. Sample a random continuous action vector containing positive buy weights for multiple assets (e.g. 18 assets out of 28).
  3. In `custom_env.py` lines 282–288:
     ```python
     pos_mask = action > 0
     pos_sum = np.sum(action[pos_mask])  # Computed as np.float32
     for i in range(self.stock_dim):
         if action[i] > 0:
             w = float(action[i]) / pos_sum  # Floating point precision loss
             target_buy_cash = allocatable_cash * w
             ...
             self.cash -= target_buy_cash
     ```
  4. Due to `float32` summation truncation, $\sum w_i$ sums to $\approx 1.00000178$. The cumulative allocated cash $\sum \text{target\_buy\_cash}_i$ exceeds `allocatable_cash` by a few cents.
  5. Empirical harness measured `self.cash` becoming `np.float32(-0.02734375)` at Step 0.
- **Blast Radius**:
  - `self.cash` drops below $\$0.00$ without margin/shorting enabled.
  - On all subsequent steps, line 283 `if pos_sum > 0 and self.cash > 0:` evaluates to `False`, permanently freezing all subsequent buy orders until positions are liquidated.
  - Normalized cash observation component becomes negative (`-0.0000273`).
- **Mitigation / Defense Recommendation**:
  1. Cast `pos_sum` and weights to double precision (`np.float64`), or normalize weights explicitly:
     ```python
     weights = action[pos_mask].astype(np.float64)
     weights /= np.sum(weights)
     ```
  2. Cap each buy order to available cash:
     ```python
     target_buy_cash = min(allocatable_cash * w, self.cash)
     ```
  3. Clamp cash after buy loop:
     ```python
     self.cash = max(0.0, self.cash)
     ```

---

### [Low] Challenge 2: Infinite Bounds in Observation Space Trigger Gymnasium Framework Warnings

- **Assumption Challenged**: Using `low=-np.inf, high=np.inf` for the 539-dim Box observation space complies with optimal Gymnasium practices.
- **Attack Scenario**: Gymnasium native environment checker (`check_env`) emits framework warnings regarding infinite bounds for observation values.
- **Blast Radius**: Non-fatal warnings during RL training setup.
- **Mitigation**: Specify explicit numerical bounds (e.g. `low=-1e6, high=1e6`) matching `np.nan_to_num` clipping in `_get_observation`.

---

## Stress Test Results

| Test Scenario | Expected Behavior | Actual Behavior | Result |
| :--- | :--- | :--- | :--- |
| **539-Dim Observation Space Shape** | Observation space shape strictly `(539,)`, dtype `np.float32`. | 1 (cash) + 28 (shares) + 28 (prices) + 476 (tech) + 3 (regimes) + 3 (risk) = 539 dims. | **PASS** |
| **1000-Step Random Action Trajectory** | 1000 steps execute without NaN, Inf, or zero division. | 1000 steps completed across multiple seeds without NaNs or Infs. | **PASS** |
| **10 bps Fee on Buys** | $\text{fee} = 0.001 \times \text{transaction value}$ | Buy fee strictly matches $0.001 \times \text{buy\_val}$ ($\text{fee} / \text{buy\_val} = 0.001000$). | **PASS** |
| **10 bps Fee on Sells** | $\text{fee} = 0.001 \times \text{transaction value}$ | Sell fee strictly matches $0.001 \times \text{sell\_val}$ ($\text{fee} / \text{sell\_val} = 0.001000$). | **PASS** |
| **Multi-Asset Simultaneous Trades** | Proportional fee allocation across all active tickers. | Fees correctly calculated across multiple tickers in single step. | **PASS** |
| **Episode Reset Hygiene** | All state variables reset cleanly; zero cross-episode state bleed. | Cash, shares, net worth, peak net worth, drawdown, trades, cost, and returns memory reset cleanly. | **PASS** |
| **Episode Truncation** | `truncated=True` when `day == num_dates - 1`. | Correctly sets `truncated=True` at last date. | **PASS** |
| **Bankruptcy Termination** | `terminated=True` if `net_worth <= 0`. | Correctly triggers `terminated=True` when net worth $\le 0$. | **PASS** |
| **Adversarial Input Resiliency** | Handle NaN, +Inf, -Inf, $10^8$ actions gracefully. | `np.nan_to_num` & `np.clip` clean action vectors without crashing. | **PASS** |
| **Cash Invariant Check (No Margin)** | Cash balance strictly $\ge \$0.00$. | `self.cash` drifts to $-\$0.0273$ due to float32 weight sum truncation. | **FAIL (Mitigated in test)** |

---

## Unchallenged Areas

- **Out-of-sample trading performance & financial profitability**: Evaluation of strategy returns, Sharpe ratio, and alpha generation is scoped under Milestone 3 (RL Model Training & Evaluation).
