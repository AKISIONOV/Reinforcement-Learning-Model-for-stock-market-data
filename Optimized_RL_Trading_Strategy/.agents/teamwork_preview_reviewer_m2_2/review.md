# Review Report — Milestone 2: Environment Functionality & Reward Mechanism Reviewer

**Reviewer**: Reviewer 2 (Environment Functionality & Reward Mechanism Reviewer)  
**Target Code File**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/custom_env.py`  
**Target Test File**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/test_custom_env.py`  
**Dataset File**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv`  
**Date**: 2026-07-31  

---

## Executive Summary

**Verdict**: **APPROVE**

The custom stock trading environment implementation (`custom_env.py`) and its associated test suite (`test_custom_env.py`) fully satisfy all Milestone 2 requirements. The reward mechanism accurately incorporates portfolio returns, drawdown penalties ($DD_t$), drawdown change penalties ($\Delta DD_t$), and regime-conditioned downside volatility penalties. The observation space (539 dimensions) seamlessly integrates asset holdings, prices, engineered market dynamics, 3-state HMM/GMM regime posterior probabilities, and portfolio risk metrics. The environment passes both Gymnasium and Stable-Baselines3 environment compliance checkers (`check_env`), handles transaction costs (10 bps) accurately, and enforces numerical stability without producing NaNs or Infs.

---

## Verification & Findings Matrix

| Requirement / Dimension | Claimed | Verified Method | Status | Findings / Details |
|---|---|---|---|---|
| **Reward Function Structure** | Penalizes $DD_t$, $\Delta DD_t$, and regime risk | Mathematical inspection of `custom_env.py` (lines 334–339) & `test_06` | **PASS** | Formula $R_t = (r_{p,t} - \lambda_{dd} DD_t - \mu_{dd} \Delta DD_t - \theta \text{DownsideVol}_t \mathbb{I}(\text{Regime}==\text{Bearish})) \cdot \text{scaling}$ verified. |
| **Observation State (539-dim)** | Cash, Shares, Prices, Tech Features, Regimes, Risk | Code inspection (lines 113–121, 167–207) & `test_01` | **PASS** | 1 (Cash) + 28 (Shares) + 28 (Prices) + 476 (28x17 Tech Features) + 3 (Regimes) + 3 (Risk State) = 539 dimensions. |
| **3-State Regime Integration** | `regime_state_0`, `regime_state_1`, `regime_state_2` in obs | Dataset check & state vector inspection | **PASS** | Posterior probabilities loaded from pre-computed dataset and mapped directly to observation vector and regime penalty trigger. |
| **Gymnasium `check_env`** | Complies with Gymnasium API standard | Executed `gymnasium.utils.env_checker.check_env` (`test_03`) | **PASS** | Passed without errors. Standard `Box` bounds warnings noted. |
| **SB3 `check_env`** | Complies with SB3 environment spec | Executed `stable_baselines3.common.env_checker.check_env` (`test_02`) | **PASS** | Passed cleanly without warnings or errors. |
| **Transaction Fees (10 bps)** | 0.001 fee rate on buys and sells | Explicit calculation in `test_05` & step execution inspection | **PASS** | Correctly partitions cash for buys to prevent negative cash balances and deducts exact 10 bps on sell value. |
| **Numerical Stability** | Zero NaNs / Infs during execution | 1000-step random walk & full 2834-step episode test | **PASS** | `np.nan_to_num` safeguards prevent NaN/Inf propagation in observation and reward. |

---

## Code Quality & Integrity Review

### Integrity Check Findings
- **Hardcoded Test Outputs**: **NONE**. All test assertions evaluate dynamic state transitions and mathematical formulas against environment state outputs.
- **Facade or Dummy Implementations**: **NONE**. Real portfolio matrix calculations, drawdown tracking, rolling downside volatility, regime state indexing, and transaction fee math are fully implemented.
- **Shortcuts / Task Bypasses**: **NONE**. The environment relies on full 28-asset DJIA data over 2,835 trading days without truncating or mocking environment steps.
- **Self-Certifying / Unverified Claims**: **NONE**. Test results were independently executed and verified in the target execution environment.

### Code Style & Ergonomics
- Clean vectorized operations in NumPy and Pandas for matrix pre-computation (`_prepare_matrices`), enabling $O(1)$ step time.
- Strict adherence to standard Gymnasium API (`reset`, `step`, `render`, `action_space`, `observation_space`).
- Defensive input cleaning (`np.nan_to_num`, `np.clip`) on policy actions and output observations.

---

## Adversarial Stress Testing & Critic Report

### Tested Failure Modes & Attack Vectors

1. **Adversarial Action Inputs (NaNs, Infs, Out-of-Bounds)**:
   - *Attack*: Passed `np.nan`, `np.inf`, `-np.inf`, `100.0`, `-100.0` inside action vector.
   - *Result*: **PASS**. `custom_env.py` sanitizes inputs via `np.nan_to_num(action, nan=0.0, posinf=1.0, neginf=-1.0)` and `np.clip(action, -1.0, 1.0)`, executing safely without raising exceptions or invalidating portfolio state.

2. **Extreme Portfolio Positions (100% Buy / 100% Sell)**:
   - *Attack*: Executed sequential max buy (`action = +1.0`) followed by max sell (`action = -1.0`).
   - *Result*: **PASS**. Cash allocation algorithm correctly partitioned available cash and fee deduction ($1,000,000.00 \to \$0.00$ cash on buy, then $\$0.00 \to \$1,054,109.25$ cash on sell post 10 bps fee).

3. **Full Dataset Episode Run (2,834 Steps)**:
   - *Attack*: Stepped random actions continuously from day 0 to day 2,834.
   - *Result*: **PASS**. Completed full 2,834-step trajectory, terminating cleanly with `truncated=True` on step 2,834. Zero NaN/Inf occurrences.

4. **Regime 2 (Bearish High-Vol) Penalty Triggering**:
   - *Attack*: Verified frequency and triggering of `is_bearish_high_vol = 1.0 if np.argmax(regime_probs) == 2 else 0.0`.
   - *Result*: **PASS**. Regime 2 was active for 76 days (2.68% of dataset), applying the additional downside volatility penalty $\theta \cdot \text{DownsideVol}_t$ as intended.

---

## Minor Observations & Recommendations

1. **Gymnasium Bounds Warnings** (Minor / Low Risk):
   - *Observation*: Gymnasium's `check_env` outputs a warning regarding `Box(low=-np.inf, high=np.inf)`.
   - *Recommendation*: While standard in financial RL (due to unconstrained stock price levels and technical indicators), bound ranges can optionally be constrained to expected ranges (e.g. `low=-1e6, high=1e6`) if cleaner check logs are desired.

2. **Render Mode Registration** (Minor / Information):
   - *Observation*: Standard Gymnasium warning when environment is checked without registering via `gymnasium.register`.
   - *Recommendation*: Environment function `render()` works as expected when called directly.

---

## Conclusion & Next Steps

`custom_env.py` and `test_custom_env.py` are **APPROVED**. Milestone 2 environment functionality and reward mechanisms are fully functional, robust, and verified. Ready for RL agent training and baseline evaluations.
