# Milestone 2 Challenge Report: Reward Function & Extreme Action Stress Testing

## Challenge Summary

**Overall risk assessment**: MEDIUM

While the reward function formula, drawdown mathematics ($\text{DD}_t$ and $\Delta \text{DD}_t$), regime penalty firing ($\text{Regime} == 2$), and general Gymnasium API bounds operate correctly with zero NaNs/Infs, an **empirical numerical precision bug** was uncovered under extreme buy actions (+1.0 across all 28 assets). Single-precision floating point division when computing allocation weights causes total allocated cash to exceed available cash by $0.3125, driving `self.cash` negative (`-$0.3125`) and locking out subsequent buy orders.

---

## Challenges

### [Medium] Challenge 1: Single-Precision Weight Sum Overflow Drives Cash Balance Negative (`-$0.3125`)

- **Assumption challenged**: Buying 100% weights across all assets (`action = +1.0`) distributes 100% of available cash without exceeding `self.cash` or driving cash negative.
- **Attack scenario**: Pass an action vector of `+1.0` for all 28 stocks on step 0 with `$1,000,000.00` initial cash.
- **Root cause analysis**:
  - In `custom_env.py` (lines 280–295):
    ```python
    pos_mask = action > 0
    pos_sum = np.sum(action[pos_mask])  # Returns np.float32(28.0)
    for i in range(self.stock_dim):
        if action[i] > 0:
            w = float(action[i]) / pos_sum  # Evaluates 1.0 / np.float32(28.0)
            target_buy_cash = allocatable_cash * w
            self.cash -= target_buy_cash
    ```
  - `pos_sum` is a `numpy.float32` object (`28.0`).
  - In Python, `float(1.0) / np.float32(28.0)` evaluates in float32 precision before promoting to float64, yielding `w = 0.035714285817882202`.
  - Summing `w` across 28 assets gives $\sum w = 28 \times 0.035714285817882202 = 1.0000000029007016 > 1.0$.
  - Total deducted cash = $\$1,000,000.0 \times 1.0000000029007016 = \$1,000,000.3125$.
  - Post-buy cash becomes $\$1,000,000.0 - \$1,000,000.3125 = \mathbf{-\$0.3125}$.
- **Blast radius**:
  - `self.cash` drops below zero (`-$0.3125`).
  - On subsequent steps, `if pos_sum > 0 and self.cash > 0:` evaluates to `False`, permanently locking the agent out of placing any further buy orders unless shares are sold to restore positive cash.
  - Normalized cash observation `cash_norm` becomes negative (`-3.125e-7`).
- **Mitigation**:
  1. Cast `pos_sum` explicitly to Python float before division: `w = float(action[i]) / float(pos_sum)`.
  2. Clamp buy allocation to remaining cash: `target_buy_cash = min(target_buy_cash, self.cash)`.
  3. Clamp cash balance to 0 post-loop: `self.cash = max(0.0, self.cash)`.

---

## Stress Test Results

| Scenario | Expected Behavior | Actual Behavior | Status |
|---|---|---|---|
| **Drawdown Math ($\text{DD}_t$, $\Delta \text{DD}_t$)** | Exact match to peak net worth tracking & drawdown formula | Matches to 5 decimal places across 50 steps; zero-division safeguard `1e-8` holds | **PASS** |
| **Bearish High-Vol Regime Penalty** | Penalty $- \theta \cdot \text{DownsideVol}_t$ fires iff $\text{argmax}(\text{regime\_probs}) == 2$ | Fired 7 times out of 200 steps when regime state 2 dominated; 0 penalty on remaining 193 steps | **PASS** |
| **Extreme All-Buy (+1.0)** | Cash stays $\ge 0$, no NaNs/Infs | Cash balance driven to **`-$0.3125`** due to float32 allocation weight overflow | **FAIL (Bug Found)** |
| **Extreme All-Sell (-1.0)** | Shares $\ge 0$, cash positive, no NaNs/Infs | Cash remains positive, shares remain $\ge 0.0$, zero NaNs/Infs | **PASS** |
| **Oscillating Actions (+1.0 / -1.0)** | Decays portfolio gracefully under fees, zero NaNs/Infs | Net worth decays under 10 bps buy/sell fees; zero NaNs/Infs in obs/rewards | **PASS** |
| **Out-of-Bounds Inputs (NaN, Inf, 1e12)** | Cleaned by `nan_to_num` and `clip` to $[-1, 1]$ | Actions cleaned to valid range $[-1.0, 1.0]$ without runtime exceptions or corrupted states | **PASS** |
| **Rolling Downside Volatility (21 days)** | $\text{DownsideVol} = \sqrt{\text{mean}(\min(0, r_p)^2)}$ over 21 days | Matches manual calculation over rolling 21-day memory window | **PASS** |

---

## Unchallenged Areas

- **Data Loading Pipeline (`pd.read_csv`)**: Presumed valid per Milestone 1 feature engineering verification.
- **Model Training Integration**: SB3 PPO/SAC training loops out of scope for environment-only stress testing.
