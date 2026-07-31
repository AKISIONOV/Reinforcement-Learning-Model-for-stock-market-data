# Handoff Report — Milestone 2: Gymnasium Trading Environment Adaptation

## 1. Observation

### Codebase & Dataset State
- Target Project Directory: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy`
- Processed Dataset Path: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv`
- Total Rows in Dataset: `79,380` rows (2,835 unique dates across 28 DJIA tickers: `AAPL`, `AXP`, `BA`, `CAT`, `CSCO`, `CVX`, `DIS`, `GS`, `HD`, `IBM`, `INTC`, `JNJ`, `JPM`, `KO`, `MCD`, `MMM`, `MRK`, `MSFT`, `NKE`, `PFE`, `PG`, `TRV`, `UNH`, `V`, `VZ`, `WBA`, `WMT`, `XOM`).
- Market Dynamics Features: 17 columns per ticker (`return`, `log_return`, `ewma_vol`, `volatility_ratio_5_21`, `garman_klass_vol`, `garch_vol`, `shadow_upper`, `shadow_lower`, `shadow_ratio`, `vwap`, `vwap_distance`, `order_flow_imbalance`, `corwin_schultz_spread`, `return_shock_zscore`, `return_jump_indicator`, `volume_spike_index`, `joint_vol_vol_shock`).
- Global Market Regimes: 3 posterior probability columns (`regime_state_0`, `regime_state_1`, `regime_state_2`).

### Delivered Artifacts
1. `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/custom_env.py`
   - Defines `StockTradingEnv(gym.Env)` inheriting from `gymnasium.Env`.
   - Observation Space: `gymnasium.spaces.Box(low=-np.inf, high=np.inf, shape=(539,), dtype=np.float32)`.
     - Cash balance (1 dim, normalized by `initial_amount`).
     - Shares held (28 dims, scaled by `1e-4`).
     - Adjusted close prices (28 dims).
     - Engineered market dynamics features per ticker ($28 \times 17 = 476$ dims).
     - Global Market Regime probabilities ($3$ dims: state 0, state 1, state 2).
     - Portfolio risk state ($3$ dims: $\text{DD}_t$, $\text{Peak}_t / \text{initial\_amount}$, $\text{DownsideVol}_t$).
   - Action Space: `gymnasium.spaces.Box(low=-1.0, high=1.0, shape=(28,), dtype=np.float32)`.
   - Transaction Fee: 10 bps ($0.001 \times \text{transaction value}$) enforced on buys and sells.
   - Reward Function:
     $$R_t = r_{p, t} - \lambda_{\text{DD}} \cdot \text{DD}_t - \mu_{\text{DD}} \cdot \Delta \text{DD}_t - \theta \cdot \text{DownsideVol}_t \cdot \mathbb{I}(\text{Regime} == \text{Bearish High-Vol})$$
     With default parameters $\lambda_{\text{DD}} = 0.5$, $\mu_{\text{DD}} = 2.0$, $\theta = 0.1$.
   - API Compliance: `reset(seed=None, options=None)` returns `(obs, info)`; `step(action)` returns `(obs, reward, terminated, truncated, info)` with `info` containing `{'net_worth': V_t, 'portfolio_return': r_p, 'drawdown': DD_t, 'trades': n_trades}`.

2. `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/test_custom_env.py`
   - Suite of 8 unit tests verifying API compliance via `stable_baselines3.common.env_checker.check_env` and `gymnasium.utils.env_checker.check_env`, 1000-step random action episode execution, 10 bps fee enforcement, reward formula accuracy, custom start day resets, and episode truncation.

### Command Execution Results
- `python test_custom_env.py`:
```
test_01_environment_initialization (__main__.TestStockTradingEnv.test_01_environment_initialization) ... ok
test_02_stable_baselines3_env_checker (__main__.TestStockTradingEnv.test_02_stable_baselines3_env_checker) ... ok
test_03_gymnasium_env_checker (__main__.TestStockTradingEnv.test_03_gymnasium_env_checker) ... ok
test_04_random_action_episode_1000_steps (__main__.TestStockTradingEnv.test_04_random_action_episode_1000_steps) ... ok
test_05_transaction_fee_enforcement (__main__.TestStockTradingEnv.test_05_transaction_fee_enforcement) ... ok
test_06_reward_function_formula_accuracy (__main__.TestStockTradingEnv.test_06_reward_function_formula_accuracy) ... ok
test_07_custom_start_date_reset (__main__.TestStockTradingEnv.test_07_custom_start_date_reset) ... ok
test_08_full_episode_run (__main__.TestStockTradingEnv.test_08_full_episode_run) ... ok

----------------------------------------------------------------------
Ran 8 tests in 1.695s

OK
```

## 2. Logic Chain

1. **Pre-Indexing & Vectorization**:
   - The environment converts tabular market dynamics data into 3D NumPy arrays upon initialization: `price_array` $(N, 28)$, `tech_array` $(N, 28, 17)$, and `regime_array` $(N, 3)$.
   - This ensures $O(1)$ constant time step execution during training iterations without Pandas overhead.

2. **Order Execution & Fee Mechanics**:
   - Selling is executed prior to buying to free up cash. Cash generated from sells equals $\text{sell\_val} \times (1 - 0.001)$.
   - Buying partitions available cash into $\text{buy\_val}$ and fee where $\text{fee} = \text{target\_buy\_cash} \times (0.001 / 1.001)$, ensuring cash balance never goes below zero while transaction cost is exactly 10 bps of asset transaction value.

3. **Drawdown & Downside Risk Penalization**:
   - Peak net worth $\text{Peak}_t = \max(\text{Peak}_{t-1}, V_t)$ is tracked continuously.
   - Drawdown $\text{DD}_t = (\text{Peak}_t - V_t) / \text{Peak}_t$ and delta $\Delta \text{DD}_t = \max(0, \text{DD}_t - \text{DD}_{t-1})$ penalize portfolio value degradation.
   - Downside volatility is computed over a rolling 21-day window of negative step portfolio returns: $\text{DownsideVol}_t = \sqrt{\text{mean}(\min(0, r_p)^2)}$.
   - Bearish High-Vol regime flag $\mathbb{I}(\text{Regime} == \text{Bearish High-Vol})$ evaluates to $1.0$ when state 2 (`regime_state_2`) is the dominant regime.

4. **Gymnasium API Alignment**:
   - Return shapes and types strictly comply with Gymnasium standard specifications. `check_env` from both Stable-Baselines3 and Gymnasium validate action/observation space bounds, step signatures, and reset behavior.

## 3. Caveats

- Observation space bounds use `[-np.inf, np.inf]` which triggers standard Gymnasium logger warnings regarding unbounded continuous boxes (this is normal standard behavior for trading environments with unscaled price/net worth features).
- Ticker count is set to 28 based on the processed dataset; passing a dataset with a different number of tickers automatically adjusts `stock_dim` during initialization.

## 4. Conclusion

The `StockTradingEnv` in `custom_env.py` fully implements all Gymnasium Trading Environment Adaptation requirements for Milestone 2, passed 100% of unit tests in `test_custom_env.py`, and is ready for RL model training (PPO, A2C, DDPG, SAC, TD3).

## 5. Verification Method

To independently verify the implementation:
1. Open shell terminal in `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy`.
2. Run the test command:
   ```bash
   python test_custom_env.py
   ```
3. Confirm all 8 test cases output `ok` and total execution finishes with `OK`.
