# Forensic Audit Report — Milestone 2 (Environment & Reward Integrity)

**Work Product**: `custom_env.py` & `test_custom_env.py`  
**Profile**: General Project (Forensic Integrity & Reward Mechanism Audit)  
**Verdict**: CLEAN  

---

## 1. Executive Summary

An independent forensic integrity audit was conducted on `custom_env.py` and `test_custom_env.py` for Milestone 2 (Environment & Reward Integrity Audit). The environment implements a multi-asset Dow Jones Industrial Average (DJIA) stock trading simulation adhering strictly to the Gymnasium API standard.

The audit verified:
- Zero hardcoded reward values, fake facades, or shortcuts.
- Full enforcement of 10 bps (0.001) transaction costs on buys and sells.
- Mathematically accurate drawdown ($DD_t$), change in drawdown ($\Delta DD_t$), and regime-aware downside volatility penalties.
- Native Gymnasium API and Stable-Baselines3 (SB3) `check_env` compliance.
- Robust guardrails ensuring zero NaN/Inf propagation under edge cases.

---

## 2. Forensic Phase Results

| Check # | Forensic Check Name | Status | Details & Observations |
|:---:|:---|:---:|:---|
| **1** | Hardcoded Output & Facade Detection | **PASS** | Source code in `custom_env.py` contains dynamic state updates and portfolio valuation logic. No constant return shortcuts, pre-calculated outputs, or dummy facades exist. |
| **2** | Transaction Fee Enforcement | **PASS** | `buy_cost_pct` (0.001) and `sell_cost_pct` (0.001) are applied to exact transaction values. On buys, `fee = target_buy_cash * (buy_cost_pct / (1 + buy_cost_pct))` ensures `fee / buy_val = 0.001` (10 bps). Cash balance is properly deducted. |
| **3** | Drawdown & Risk Penalty Accuracy | **PASS** | Peak net worth tracking ($Peak_t = \max(Peak_{t-1}, NetWorth_t)$), relative drawdown ($DD_t$), step drawdown delta ($\Delta DD_t$), and rolling 21-day downside volatility ($\text{DownsideVol}_t$) are continuously calculated and penalized. |
| **4** | Gymnasium API & SB3 Compliance | **PASS** | Correct 5-tuple returned by `step()` (`obs, reward, terminated, truncated, info`), 2-tuple returned by `reset()` (`obs, info`). Passes both `gymnasium.utils.env_checker.check_env` and `stable_baselines3.common.env_checker.check_env`. |
| **5** | Matrix Pre-computation & Data Alignment | **PASS** | `_prepare_matrices()` correctly aligns price matrices `(num_dates, stock_dim)`, technical indicators `(num_dates, stock_dim, 17)`, and regime probabilities `(num_dates, 3)` for fast O(1) step lookups. |
| **6** | Robustness & Guardrails | **PASS** | `np.nan_to_num` and `np.clip` safeguard observation and reward outputs. Empirical stress testing confirmed graceful handling of NaN/Inf actions, out-of-bound start days, and negative net worth bankruptcy termination. |

---

## 3. Detailed Forensic Analysis

### A. Prohibited Pattern & Facade Inspection
- **Hardcoded Rewards**: Verified `custom_env.py` lines 334-340:
  ```python
  reward = (
      r_p
      - self.lambda_dd * self.drawdown
      - self.mu_dd * delta_dd
      - self.theta * downside_vol * is_bearish_high_vol
  ) * self.reward_scaling
  ```
  The step reward $R_t$ is dynamically computed per step using live portfolio returns $r_{p,t}$, drawdown levels $DD_t$, drawdown deltas $\Delta DD_t$, and downside volatility scaled by regime probability indicator $I(\text{Regime} == \text{Bearish High-Vol})$.
- **Facade Detection**: All methods (`reset`, `step`, `_get_observation`, `_prepare_matrices`, `render`) execute genuine calculation logic on pandas/numpy data arrays.

### B. Transaction Cost Verification
- **Sell Costs**: `sell_val = sell_shares * current_prices[i]`, `fee = sell_val * self.sell_cost_pct`, `cash += (sell_val - fee)`.
- **Buy Costs**: `fee = target_buy_cash * (self.buy_cost_pct / (1.0 + self.buy_cost_pct))`, `buy_val = target_buy_cash - fee`, `cash -= target_buy_cash`.
- Empirical test `test_05_transaction_fee_enforcement` proved `fee / buy_val == 0.001` (10 bps) and `sell_fee / sell_val == 0.001` (10 bps).

### C. Gymnasium API Alignment
- `action_space`: `Box(low=-1.0, high=1.0, shape=(28,), dtype=np.float32)`
- `observation_space`: `Box(low=-inf, high=inf, shape=(539,), dtype=np.float32)`
- Observation composition (539 dims):
  - Normalized cash: 1 dim
  - Scaled shares: 28 dims ($10^{-4}$ scaling)
  - Asset prices: 28 dims
  - Market dynamics features: 476 dims ($28 \times 17$)
  - Global market regime probabilities: 3 dims
  - Portfolio risk state ($DD_t$, $Peak_t / Initial$, $\text{DownsideVol}_t$): 3 dims

---

## 4. Empirical Test Verification Output

### Unit Test Execution Log (`test_custom_env.py`)
```
test_01_environment_initialization (test_custom_env.TestStockTradingEnv) ... ok
test_02_stable_baselines3_env_checker (test_custom_env.TestStockTradingEnv) ... ok
test_03_gymnasium_env_checker (test_custom_env.TestStockTradingEnv) ... ok
test_04_random_action_episode_1000_steps (test_custom_env.TestStockTradingEnv) ... ok
test_05_transaction_fee_enforcement (test_custom_env.TestStockTradingEnv) ... ok
test_06_reward_function_formula_accuracy (test_custom_env.TestStockTradingEnv) ... ok
test_07_custom_start_date_reset (test_custom_env.TestStockTradingEnv) ... ok
test_08_full_episode_run (test_custom_env.TestStockTradingEnv) ... ok

----------------------------------------------------------------------
Ran 8 tests in 4.992s

OK
```

### Empirical Stress Testing Log
```
Test 1 (NaN/Inf action input guardrail) ........ PASSED
Test 2 (Bankruptcy termination on net_worth <= 0) PASSED
Test 3 (Out-of-bounds start_day handling) ...... PASSED
```

---

## 5. Final Audit Verdict

**CLEAN**

The work product `custom_env.py` and test suite `test_custom_env.py` meet all integrity, API, transaction cost, and risk penalty requirements without any violations or shortcuts.
