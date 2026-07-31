# Handoff Report — Milestone 0 (Codebase Exploration)

**Author:** Explorer 1  
**Target Working Directory:** `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_explorer_m0_1`  
**Date:** July 31, 2026  
**Handoff Type:** Hard (Task Complete)  

---

## 1. Observation

Direct observations from inspecting `f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading`:

1. **File Inventory & Structure**:
   - `README.md` (2,561 bytes, lines 1-51): Describes stock trading with DRL using `stable-baselines3`, `gymnasium`, `numpy`, `pandas`, `matplotlib`, referencing SSRN paper 3690996.
   - `main.ipynb` (600,936 bytes) & `main_extracted.py` (22,136 bytes, 588 lines): Main pipeline script.
   - `Documents/ssrn-3690996 (2).pdf`: Research paper PDF.
   - 30 stock CSV files in root and mirrored in `notebooks/`.

2. **Data Anomalies Observed**:
   - `UTX.csv`: File size 42 bytes. Line 1: `Date,Open,High,Low,Close,Adj Close,Volume`. Zero data rows (empty).
   - `DOW.csv`: File size 30,723 bytes, 288 data rows starting `2019-03-20`.
   - Remaining 28 CSV files (AAPL, AXP, BA, CAT, CSCO, CVX, DIS, GS, HD, IBM, INTC, JNJ, JPM, KO, MCD, MMM, MRK, MSFT, NKE, PFE, PG, TRV, UNH, V, VZ, WBA, WMT, XOM): Each has 2,857 data rows spanning `2009-01-02` to `2020-05-07`.

3. **Code Base Observations (`main_extracted.py`)**:
   - Line 148: `class StockTradingEnv(gym.Env):` inherits from Gymnasium.
   - Line 245: `reward = self.net_worth - self.initial_balance` — Cumulative profit reward formulation.
   - Lines 229-239:
     ```python
     if action > 0: # Buy
         shares_to_buy = int(self.balance * action / current_prices[ticker])
         cost = shares_to_buy * current_prices[ticker]
         self.balance -= cost
         self.shares_held[ticker] += shares_to_buy
     elif action < 0: # Sell
         shares_to_sell = int(self.shares_held[ticker] * abs(action))
         sale = shares_to_sell * current_prices[ticker]
         self.balance += sale
         self.shares_held[ticker] -= shares_to_sell
     ```
     No transaction cost or fee percentage applied.
   - Lines 561 & 580:
     ```python
     # Line 561:
     test_and_visualize_agents(env, test_agents, test_data, n_tests=n_tests)
     ```
     `env` (the training environment instance created on line 531) is passed to `test_and_visualize_agents` instead of `test_env` (defined on line 551).
   - Lines 79-83 and 92-96: `df['RSI']` is calculated twice in `add_technical_indicators()`.

4. **Tool Command Observation**:
   - Running inline python check `python -c "import finrl, stable_baselines3..."` via `run_command` timed out waiting for user permission prompt. Statically verified code imports instead.

---

## 2. Logic Chain

1. **Observation 1 & 2** show that the parent codebase contains 30 stock CSVs, but `UTX.csv` is empty (0 rows) and `DOW.csv` has only 288 rows.
2. **Logic Step 1**: Standard slicing `loc['2009-01-01':'2015-12-31']` on `DOW` returns an empty DataFrame, while `UTX` is completely empty. If empty DataFrames are passed without filtering, state tensor matrix shapes will mismatch across dates. Thus, the active universe for continuous 2009–2020 modeling must be filtered to the 28 clean assets.
3. **Observation 3 (Line 245)** shows `reward = self.net_worth - self.initial_balance`.
4. **Logic Step 2**: Cumulative net profit grows monotonically over time when profitable. At step $t=1000$, the reward value depends on past history from step $t=0$, violating the Markov property ($P(S_{t+1}|S_t, A_t)$). This causes unstable value function fitting. The reward must be reformulated as step-by-step return ($r_t = \frac{V_t - V_{t-1}}{V_{t-1}}$) minus risk/drawdown penalties.
5. **Observation 3 (Lines 229-239)** shows zero fee subtraction on trades.
6. **Logic Step 3**: Real-world trading incurs bid-ask spread and broker commissions (e.g. 10 bps). Without fee deduction, agents learn high-frequency churn strategies that fail in production. Transaction fee factor $\eta=0.001$ must be enforced in `step()`.
7. **Observation 3 (Line 561)** shows `test_and_visualize_agents` called with `env` instead of `test_env`.
8. **Logic Step 4**: Passing `env` causes out-of-sample backtesting to execute steps on `training_data` while labeling results as test data. This corrupts evaluation metrics and must be fixed in `evaluate.py`.

---

## 3. Caveats

1. **Runtime Verification**: `run_command` timed out on permission approval; python environment execution checks were performed via static analysis of imported packages.
2. **External Data Refresh**: The codebase relies on historical CSV files provided in the directory (`2009-2020`). Fetching fresh post-2020 data via `yfinance` was not performed during this exploration milestone.

---

## 4. Conclusion

The parent repository `Deep-Reinforcement-Learning-with-Stock-Trading` provides a functional starting point for multi-asset RL stock trading using Stable-Baselines3 (`PPO`, `A2C`, `DDPG`) and Gymnasium. However, it contains severe algorithmic flaws (non-stationary cumulative profit reward, zero transaction costs, evaluation environment leak bug, corrupted UTX/DOW CSV handling).

For Milestone 1–4 implementation in `Optimized_RL_Trading_Strategy`:
1. **Milestone 1 (`data_pipeline.py`)**: Use 28 clean DJIA stocks; compute GARCH(1,1), EWMA vol, rolling vol ratio, VWAP shadow imbalance, jump shocks, and 3-state HMM regimes.
2. **Milestone 2 (`custom_env.py`)**: Build 575-dim Gymnasium env with step return + drawdown penalty reward and 10 bps transaction fee.
3. **Milestone 3 (`train_optimized.py`)**: Implement CPU-only SB3 PPO trainer (`device='cpu'`) with `EvalCallback`.
4. **Milestone 4 (`evaluate.py`, `main.ipynb`)**: Build out-of-sample backtesting suite and documentation.

---

## 5. Verification Method

To independently verify these observations and conclusions:

1. **Inspect Parent Script**: View `f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading/main_extracted.py` at:
   - Line 245 to verify `reward = self.net_worth - self.initial_balance`.
   - Lines 228-240 to verify absence of transaction fees.
   - Line 561 to verify `test_and_visualize_agents(env, test_agents, test_data)` passes `env` instead of `test_env`.
2. **Inspect Asset CSVs**: View `f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading/UTX.csv` to confirm 42-byte file size and zero data rows.
3. **Inspect Output Analysis Report**: View `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_explorer_m0_1/analysis.md`.
