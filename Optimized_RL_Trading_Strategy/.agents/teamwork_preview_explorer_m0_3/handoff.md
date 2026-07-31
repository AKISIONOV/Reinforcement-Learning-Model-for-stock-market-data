# Handoff Report — Explorer 3 (Milestone 0 Architecture & Feature Design)

## 1. Observation
- Inspected existing codebase in `f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading`:
  - `AAPL.csv` ... `XOM.csv` (30 Dow Jones stock CSV files spanning 2009-01-02 to 2020-05-08).
  - Columns present in CSV files: `['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']` (observed via `view_file` on `AAPL.csv:1-10`).
  - Baseline extracted script `main_extracted.py` (588 lines) computes basic RSI, MACD, CCI, EMA12, EMA26 (lines 77-100).
- Inspected architecture roadmap in `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/orchestrator/PROJECT.md`:
  - Defined files: `data_pipeline.py`, `custom_env.py`, `train_optimized.py`, `evaluate.py`, `main.ipynb`.
  - Interface contracts require processed pandas DataFrame with columns `['date', 'tic', 'close', 'open', 'high', 'low', 'volume', 'ewma_vol', 'vol_ratio', 'order_imbalance', 'bid_ask_spread_proxy', 'news_shock_jump', 'regime']`.
- Produced complete mathematical formulation and design report in `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_explorer_m0_3/analysis.md` (301 lines).

## 2. Logic Chain
1. **Observation 1**: Baseline dataset contains standard OHLCV prices for 30 Dow Jones tickers without explicit high-frequency order book data (L2/L3) or external sentiment feeds.
2. **Step 1**: To satisfy the mandate for Volatility Clustering, Spoofing Proxies, News Shocks, and Intraday Market Regimes on daily/intraday OHLCV datasets:
   - Formulated mathematical GARCH(1,1) conditional variance ($\sigma_t^2 = \omega + \alpha \epsilon_{t-1}^2 + \beta \sigma_{t-1}^2$), RiskMetrics EWMA ($\lambda=0.94$), and short/long rolling volatility ratio ($w_s=5, w_l=20$).
   - Formulated Lee-Ready tick rule volume imbalance proxy ($\text{VIP}_t = \frac{2C_t - H_t - L_t}{H_t - L_t + \epsilon}$), Order Flow Imbalance ($\text{OFI}_t = \text{sign}(\Delta P_t) \cdot V_t$), Corwin-Schultz spread proxy, and a composite spoofing order pattern score ($S_{\text{spoof}}$).
   - Formulated non-parametric return shock jump indicator ($J_t = \mathbb{I}(|r_t - \mu_r| / \sigma_r > 3.0)$) and joint volume-volatility shock proxy ($S_{\text{news}}$).
   - Formulated GaussianHMM (3 components: Bullish Low-Vol, Neutral Ranging, Bearish High-Vol) and KMeans trend-volatility clustering.
3. **Observation 2**: RL trading environment requires expanding the observation space and aligning reward signals with risk management.
4. **Step 2**: Designed an expanded Gymnasium observation vector combining global portfolio state (32 dims), ticker-level feature vectors ($30 \times 18 = 540$ dims), and regime state probabilities (3 dims), yielding $D_{\text{obs}} = 575$ continuous features.
5. **Step 3**: Formulated a unified composite penalized reward function $R_t = r_{p, t} - \eta \cdot \text{Cost}_t - \lambda_{\text{DD}} \cdot \text{DD}_t - \mu_{\text{DD}} \cdot (\Delta \text{DD}_t)^2 - \theta \cdot \sigma_{p, t, W} \cdot \mathbb{I}(\text{Regime}_t = \text{Bearish High-Vol})$, incorporating rolling Sharpe and Sortino ratio components.
6. **Observation 3**: System environment target requires standalone CPU execution.
7. **Step 4**: Formulated CPU execution architecture in `train_optimized.py` using PyTorch thread constraints (`torch.set_num_threads(N)`), `device='cpu'`, and Stable-Baselines3 PPO with L3-cache-optimized mini-batches (`batch_size=128`, `n_steps=2048`).

## 3. Caveats
- GARCH(1,1) parameter fitting via `arch` library can occasionally fail to converge on highly stationary or illiquid periods; a robust fallback heuristic ($\alpha=0.05, \beta=0.90$) was specified to guarantee execution.
- Spoofing proxies constructed from OHLCV data represent behavioral approximations of order book manipulation rather than direct L3 order book cancellation logs.

## 4. Conclusion
The architectural design and mathematical framework for Milestone 0 is fully specified and validated. All required formulas, algorithm steps, Gymnasium space dimensions (575-dim), risk-adjusted reward functions, and CPU training configurations (`train_optimized.py`, `device='cpu'`) are documented in `analysis.md` and ready for Milestone 1 (Data Pipeline) and Milestone 2 (RL Gymnasium Env) implementation.

## 5. Verification Method
- Inspect design report file:
  `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_explorer_m0_3/analysis.md`
- Verify equations and dimensions:
  - Check GARCH, EWMA, and Volatility Ratio formulas in Section 1.1.
  - Check Spoofing proxies (VIP, OFI, Corwin-Schultz spread, Spoofing score) in Section 1.2.
  - Check Jump & News shock formulas in Section 1.3.
  - Check HMM and KMeans regime definitions in Section 1.4.
  - Check Gymnasium Box dimension ($32 + 30 \times 18 + 3 = 575$) in Section 2.1.
  - Check Composite Penalized Reward formula in Section 2.2.
  - Check SB3 PPO CPU configuration (`device='cpu'`) in Section 3.
