# Code Review Report: Milestone 2 — Gymnasium Stock Trading Environment

**Target Code File**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/custom_env.py`  
**Target Test File**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/test_custom_env.py`  
**Reviewer**: Reviewer 1 (Milestone 2 Code Reviewer & Adversarial Critic)  
**Date**: 2026-07-31  

---

## Executive Summary

**Verdict**: **APPROVE**

The Gymnasium Stock Trading Environment implementation (`custom_env.py`) and its unit test suite (`test_custom_env.py`) fully satisfy all requirements for Milestone 2. The codebase exhibits strict adherence to the Gymnasium API standards, exact observation dimension scaling (539 dimensions), precise 10 bps transaction fee math on both buys and sells, accurate drawdown tracking, a mathematically sound risk-adjusted drawdown-penalized reward function, and robust failure mode handling with zero NaN/Inf leakage.

All 8 unit tests in `test_custom_env.py` executed cleanly and passed in 1.66 seconds. No integrity violations, shortcuts, or facade implementations were detected.

---

## Detailed Evaluation Dimensions

### 1. Gymnasium API Compliance
- **Inheritance & Structure**: `StockTradingEnv` inherits directly from `gymnasium.Env`.
- **Spaces**:
  - `action_space`: `spaces.Box(low=-1.0, high=1.0, shape=(28,), dtype=np.float32)`.
  - `observation_space`: `spaces.Box(low=-np.inf, high=np.inf, shape=(539,), dtype=np.float32)`.
- **Method Signatures**:
  - `reset(self, seed=None, options=None, start_day=None)` returns `(obs, info)`.
  - `step(self, action)` returns `(obs, reward, terminated, truncated, info)`.
- **Checker Verification**:
  - Stable-Baselines3 `check_env` (`test_02_stable_baselines3_env_checker`) passed with zero errors.
  - Gymnasium native `check_env` (`test_03_gymnasium_env_checker`) passed with zero errors.

### 2. Observation Vector Shape & Breakdown (539 Dimensions)
The observation vector is constructed via `_get_observation()` in `custom_env.py` (lines 167–211) as follows:
- **Cash balance**: 1 dim (`cash / initial_amount`)
- **Shares held**: 28 dims (`shares * 1e-4`)
- **Adjusted close prices**: 28 dims (`current_prices`)
- **Market dynamics features**: 476 dims (28 tickers $\times$ 17 engineered technical indicators)
- **Global market regime probabilities**: 3 dims (`regime_state_0`, `regime_state_1`, `regime_state_2`)
- **Portfolio risk state**: 3 dims ($DD_t$, $Peak_t / initial\_amount$, $DownsideVol_t$)

Total dimensions: $1 + 28 + 28 + 476 + 3 + 3 = 539$.

### 3. Action Space & Execution Logic
- Actions in $[-1.0, 1.0]$ represent target trading proportions across 28 DJIA assets.
- **Sell Logic**: Executed first. Negative actions sell a fraction $|a_i|$ of currently held shares $i$. Cash received is net of 10 bps transaction fees.
- **Buy Logic**: Executed second. Positive actions are normalized by $\sum_{a_i > 0} a_i$ to allocate available cash $C_t$. Cash spent is partitioned into transaction value $V_{buy}$ and fee $F_{buy} = V_{buy} \times 0.001$.
- **Numerical Safeguard**: Shares below $1e-6$ are excluded to prevent floating-point noise. Actions are cleaned with `np.nan_to_num` and clipped to $[-1.0, 1.0]$.

### 4. 10 bps Transaction Fee Enforcement
- **Buy Fee**: Target cash $C_{target}$ is partitioned such that $C_{target} = V_{buy} + F_{buy}$. Since $F_{buy} = 0.001 \times V_{buy}$, $F_{buy} = C_{target} \times \frac{0.001}{1.001}$. The fee ratio $\frac{F_{buy}}{V_{buy}} = 0.001$ (10 bps of transaction value).
- **Sell Fee**: For gross sell value $V_{sell}$, fee $F_{sell} = 0.001 \times V_{sell}$ (10 bps of transaction value).
- Tested and verified in `test_05_transaction_fee_enforcement`.

### 5. Reward Function Mathematical Formulation
The environment implements the risk-adjusted drawdown-penalized reward function:
$$R_t = \left( r_{p, t} - \lambda_{dd} \cdot DD_t - \mu_{dd} \cdot \Delta DD_t - \theta \cdot DownsideVol_t \cdot I(\text{Regime} == \text{Bearish High-Vol}) \right) \times \text{reward\_scaling}$$

Where:
- $r_{p, t} = \frac{NetWorth_t - NetWorth_{t-1}}{NetWorth_{t-1}}$
- $DD_t = \max\left(0, \frac{Peak_t - NetWorth_t}{Peak_t}\right)$
- $\Delta DD_t = \max(0, DD_t - DD_{t-1})$
- $DownsideVol_t = \sqrt{\frac{1}{N} \sum \min(0, r_{p, \tau})^2}$ over a rolling 21-day window
- $I(\text{Regime} == \text{Bearish High-Vol}) = 1.0$ when $\text{argmax}(\text{regime\_probs}) == 2$, else $0.0$.

Verified in `test_06_reward_function_formula_accuracy`.

---

## Verified Claims Matrix

| Claim / Specification | Verification Method | Status | Observation / Result |
|---|---|---|---|
| Gymnasium API Compliance | `python test_custom_env.py` (Tests 02, 03) | **PASS** | SB3 `check_env` & Gymnasium `check_env` pass cleanly |
| Observation Dimension (539) | `test_01_environment_initialization` & Code Inspection | **PASS** | Shape `(539,)` verified: 1+28+28+476+3+3 |
| Action Space Box(-1, 1, (28,)) | `test_01_environment_initialization` & Code Inspection | **PASS** | Shape `(28,)`, dtype `float32`, bounds `[-1.0, 1.0]` |
| 10 bps Fee on Buys and Sells | `test_05_transaction_fee_enforcement` | **PASS** | $Fee / Value = 0.001$ verified to 6 decimal places |
| Drawdown Reward Formulation | `test_06_reward_function_formula_accuracy` | **PASS** | Reward matches formula to 5 decimal places |
| Custom Reset Options | `test_07_custom_start_date_reset` | **PASS** | `options={'initial_step': 250}` and `start_day` work |
| 1000-Step Episode Robustness | `test_04_random_action_episode_1000_steps` | **PASS** | Zero NaNs/Infs, valid net worth & drawdown bounds |
| Integrity Check | Source Code Audit | **PASS** | No hardcoded triggers, facades, or shortcuts |

---

## Adversarial Stress Testing & Risk Analysis

1. **Out-of-Bounds Day Indexing**: `reset(start_day=...)` clamps inputs with `max(0, min(int(start_day), self.num_dates - 1))`, preventing array out-of-bounds indexing.
2. **NaN / Inf Action Injections**: Action vectors containing `NaN` or `Inf` are sanitized via `np.nan_to_num` and clipped to `[-1.0, 1.0]`.
3. **Missing Technical Indicators in DataFrame**: If the input DataFrame lacks a column from `DEFAULT_TECH_INDICATORS`, `_prepare_matrices()` defaults to a zero-filled array of matching shape without crashing.
4. **Ticker Count Variance**: If input dataset ticker count differs from default `stock_dim=28`, `__init__` dynamically adjusts `stock_dim` and updates observation space dimension accordingly.
5. **Zero / Sub-Zero Cash Exhaustion**: Buy allocation checks `allocatable_cash > 0` and requires `buy_shares > 1e-6`, preventing division-by-zero or micro-dust trades.

---

## Findings

### Critical / Major / Minor Findings
- **Critical**: None
- **Major**: None
- **Minor**:
  - *Observation Space Infinite Bounds Warning*: Gymnasium's `check_env` emits informative warnings regarding `low=-np.inf, high=np.inf` in observation space. This is standard for unnormalized continuous market indicators and risk metrics, but explicit finite bounds (e.g. `[-1e6, 1e6]`) could be specified in future iterations if strict bound enforcement is desired.

---

## Conclusion

The custom Gymnasium trading environment `custom_env.py` and test suite `test_custom_env.py` pass all quality, compliance, mathematical, and adversarial checks. **Verdict: APPROVE**.
