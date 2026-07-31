## 2026-07-31T11:31:31+05:30
You are Worker 4 for Milestone 2 (Gymnasium Trading Environment Adaptation).
Working directory for metadata: f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_worker_m2
Target project directory: f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy
Processed dataset path: f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Task & Requirements:
1. Create `custom_env.py` in `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy`.
2. Implement Gymnasium Environment `StockTradingEnv(gym.Env)`:
   - Observation Space: Gymnasium continuous `Box` containing:
     - Cash balance (1 dim, normalized by initial balance)
     - Shares held (28 dims, scaled)
     - Adjusted close prices (28 dims)
     - Engineered market dynamics features per ticker ($28 \times 17 = 476$ dims):
       - `return`, `ewma_vol`, `volatility_ratio_5_21`, `garman_klass_vol`, `garch_vol`, `shadow_upper`, `shadow_lower`, `shadow_ratio`, `vwap_distance`, `order_flow_imbalance`, `corwin_schultz_spread`, `return_shock_zscore`, `return_jump_indicator`, `volume_spike_index`, `joint_vol_vol_shock`
     - Global Market Regime probabilities (`regime_state_0`, `regime_state_1`, `regime_state_2`) (3 dims)
     - Portfolio risk state: current drawdown $\text{DD}_t$, peak portfolio value, rolling 21-day downside volatility (3 dims).
   - Action Space: Gymnasium continuous `Box(low=-1.0, high=1.0, shape=(28,), dtype=np.float32)` representing target buy/sell proportions for all 28 assets.
   - Transaction Fee: Enforce 10 bps fee ($0.001 \times \text{transaction value}$) on both buys and sells.
   - Drawdown-Penalized Reward Function:
     - Calculate step portfolio return $r_{p, t} = (V_t - V_{t-1}) / V_{t-1}$.
     - Update peak portfolio value $\text{Peak}_t = \max(\text{Peak}_{t-1}, V_t)$.
     - Compute drawdown $\text{DD}_t = (\text{Peak}_t - V_t) / \text{Peak}_t$.
     - Compute drawdown delta $\Delta \text{DD}_t = \max(0.0, \text{DD}_t - \text{DD}_{t-1})$.
     - Compute Sortino-style downside risk penalty or regime-weighted volatility penalty:
       $R_t = r_{p, t} - \lambda_{\text{DD}} \cdot \text{DD}_t - \mu_{\text{DD}} \cdot \Delta \text{DD}_t - \theta \cdot \text{DownsideVol}_t \cdot \mathbb{I}(\text{Regime} == \text{Bearish High-Vol})$.
     - Default parameters: $\lambda_{\text{DD}} = 0.5$, $\mu_{\text{DD}} = 2.0$, $\theta = 0.1$.
   - Gymnasium API Spec Compliance:
     - `reset(seed=None, options=None)` returns `(obs, info)`. Supports custom start date indexing or full episode resets.
     - `step(action)` returns `(obs, reward, terminated, truncated, info)`. Info dictionary includes `{'net_worth': V_t, 'portfolio_return': r_p, 'drawdown': DD_t, 'trades': n_trades}`.
3. Unit Test & Verification (`test_custom_env.py`):
   - Create `test_custom_env.py` to instantiate `StockTradingEnv` with `processed_market_dynamics.csv`.
   - Run `check_env(env)` from `stable_baselines3.common.env_checker` or `gymnasium.utils.env_checker`.
   - Run a random action episode (1000 steps) and verify step rewards, observations, transaction fees, drawdown tracking, zero NaNs/Infs.
   - Run `python test_custom_env.py` via command line and verify it passes 100%.
4. Write handoff report to `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_worker_m2/handoff.md`.
5. Send a message to the orchestrator (parent) when complete.
