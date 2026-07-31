# Handoff Report — Milestone 2: Environment Functionality & Reward Mechanism Reviewer

**Agent**: Reviewer 2 (`teamwork_preview_reviewer_m2_2`)  
**Target Code File**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/custom_env.py`  
**Target Test File**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/test_custom_env.py`  
**Date**: 2026-07-31  

---

## 1. Observation

Direct evidence obtained during independent review:
- **Files Inspected**:
  - `custom_env.py` (362 lines): Custom Gymnasium stock trading environment class `StockTradingEnv`.
  - `test_custom_env.py` (215 lines): Unit test suite covering environment initialization, Gymnasium and SB3 `check_env`, random action episodes, fee enforcement, reward accuracy, custom start dates, and full episode execution.
  - `data/processed_market_dynamics.csv` (79,380 rows x 29 columns): Processed DJIA market data spanning 28 tickers across 2,835 dates with 17 technical indicators and 3-state HMM/GMM regime probabilities (`regime_state_0`, `regime_state_1`, `regime_state_2`).
- **Commands Executed & Verbatim Outputs**:
  - Command: `python test_custom_env.py`
    - Result: `Ran 8 tests in 1.754s - OK`
    - All 8 unit tests passed cleanly.
  - Command: `python -m unittest test_custom_env.py`
    - Result: `Ran 8 tests in 1.734s - OK`
  - Adversarial Stress Test Script:
    - NaN/Inf Action Handling: Handled cleanly without errors or NaN/Inf propagation (`reward=0.0175`, `obs nan count=0`).
    - Max Buy / Max Sell Sequence: Cash transformed from $\$1,000,000.00 \to \$0.00$ on buy, and $\$0.00 \to \$1,054,109.25$ on sell (10 bps transaction fee deducted).
    - Full Episode Run: Completed 2,834 steps across dataset without NaNs or exceptions (`Final Net Worth: $1,361,816.12`, `Final Drawdown: 0.2279`).
    - Bearish High-Vol Regime Days: State 2 active on 76 days (2.68% of 2,835 days).

---

## 2. Logic Chain

1. **Observation**: `custom_env.py` calculates portfolio net worth at step $t$ and step $t+1$, tracking peak net worth and drawdown $DD_t = \max(0, (Peak - NetWorth) / Peak)$ and drawdown change $\Delta DD_t = \max(0, DD_t - DD_{t-1})$.
2. **Observation**: Downside volatility is calculated over a rolling 21-day window of negative portfolio returns ($\sqrt{\text{mean}(\min(0, r_p)^2)}$), and penalized when `np.argmax(regime_probs) == 2` (Bearish High-Vol regime).
3. **Deduction**: The reward calculation in `step()` (lines 334–339) exactly matches the specified formula:
   $$R_t = (r_{p, t} - \lambda_{dd} DD_t - \mu_{dd} \Delta DD_t - \theta \text{DownsideVol}_t \mathbb{I}(\text{Regime} == \text{Bearish})) \cdot \text{scaling}$$
4. **Observation**: Observation space size is explicitly computed as $1 + 28 + 28 + (28 \times 17) + 3 + 3 = 539$ float32 values, and `_get_observation` produces an ndarray of shape `(539,)` matching this spec.
5. **Observation**: Both `stable_baselines3.common.env_checker.check_env` and `gymnasium.utils.env_checker.check_env` pass without throwing exceptions or failing assertions.
6. **Conclusion**: `custom_env.py` and `test_custom_env.py` meet all Milestone 2 functionality requirements, adhere to Gymnasium and SB3 API standards, accurately implement drawdown-penalized rewards and regime integration, and contain zero integrity violations or shortcuts.

---

## 3. Caveats

- **Gymnasium Box Bounds Warnings**: `check_env` emits standard warnings because `low=-np.inf` and `high=np.inf` are used for continuous spaces. This is standard in financial RL and does not affect functionality.
- **Data Dependency**: The environment requires `data/processed_market_dynamics.csv` containing columns `date`, `tic`, `adj_close`, the 17 technical indicators, and 3 regime probability columns (`regime_state_0`, `regime_state_1`, `regime_state_2`). If custom indicator lists or columns are passed, missing indicators default to 0.0 matrices.

---

## 4. Conclusion

- **Verdict**: **APPROVE**
- **Summary**: Environment functionality, reward mechanisms, 3-state regime probability integration, 539-dim observation vector, and transaction cost modeling are fully verified, robust, and compliant with Gymnasium / SB3 standards.

---

## 5. Verification Method

To independently verify these findings:

1. **Run Unit Test Suite**:
   ```powershell
   python test_custom_env.py
   ```
   *Expected Output*: `Ran 8 tests in ~1.7s` with status `OK`.

2. **Verify Checkers Manually**:
   ```powershell
   python -c "import pandas as pd; from custom_env import StockTradingEnv; from gymnasium.utils.env_checker import check_env as cg; from stable_baselines3.common.env_checker import check_env as cs; df=pd.read_csv('data/processed_market_dynamics.csv'); env=StockTradingEnv(df); cg(env); cs(env); print('All check_env calls passed successfully!')"
   ```
   *Expected Output*: `All check_env calls passed successfully!`.

3. **Check Output Reports**:
   - Review report: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_reviewer_m2_2/review.md`
   - Handoff report: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_reviewer_m2_2/handoff.md`
