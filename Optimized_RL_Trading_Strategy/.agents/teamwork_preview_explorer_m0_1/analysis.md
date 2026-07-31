# Comprehensive Codebase & Technical Exploration Report (Milestone 0)

**Author:** Explorer 1 (Milestone 0 Codebase Exploration)  
**Target Repository:** `f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading`  
**Working Directory:** `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_explorer_m0_1`  
**Date:** July 31, 2026  

---

## 1. Executive Summary

This report delivers a thorough, read-only audit of the parent repository located at `f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading`. 

The primary goal of Milestone 0 is to investigate existing Python scripts, modules, custom RL environments, algorithm implementations, notebooks, data files, and python dependencies, while identifying critical flaws, architectural gaps, and improvement opportunities for the target project `Optimized_RL_Trading_Strategy`.

### Key Findings Summary:
1. **Repository Inventory**: The parent repository consists of 34 root items and a `notebooks/` subfolder (total 67 files). The primary codebase resides in `main.ipynb` (600 KB Jupyter Notebook) and its extracted counterpart `main_extracted.py` (22 KB script). A reference paper (`Documents/ssrn-3690996 (2).pdf`) and 30 stock CSV files are included.
2. **Environment & DRL Framework**: The parent codebase uses `gymnasium` (imported as `gym`) to define a multi-asset `StockTradingEnv`, trained via **Stable-Baselines3** (`PPO`, `A2C`, `DDPG`) and a simple continuous action-averaging `EnsembleAgent`.
3. **Data Health & Assets**: Data represents the 30 Dow Jones Industrial Average (DJIA) constituents spanning `2009-01-01` to `2020-05-08`. Two critical anomalies exist: `UTX.csv` is empty (0 records, 42 bytes due to Raytheon merger), and `DOW.csv` is truncated (288 records starting March 2019 due to spin-off). 28 tickers are clean (2,857 records).
4. **Critical Code Deficiencies Identified**:
   - **Non-Stationary Reward Function**: Reward is formulated as `reward = net_worth - initial_balance` (cumulative net profit) rather than per-step returns ($r_t = \frac{V_t - V_{t-1}}{V_{t-1}}$), distorting RL value estimation.
   - **Missing Transaction Costs**: Despite claims in `README.md`, `StockTradingEnv.step()` applies **zero fee/commission percentage** during buy/sell trades.
   - **Evaluation Environment Bug**: `test_and_visualize_agents(env, test_agents, test_data)` mistakenly passes the training `env` instance instead of `test_env` / `validation_env`, resulting in backtesting execution on training data.
   - **Redundant Indicators**: RSI (14) is calculated twice inside `add_technical_indicators()`.
5. **Environment Dependencies**: Primary dependencies used in parent repo are `stable-baselines3`, `gymnasium`, `pandas`, `numpy`, `matplotlib`, `yfinance`, `torch`. Target modules for `Optimized_RL_Trading_Strategy` will additionally require `hmmlearn` (HMM market regimes), `statsmodels` / `arch` (GARCH volatility), and standard ML tools.

---

## 2. Parent Repository Structure & File Inventory

### 2.1 File System Structure

```
f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading/
├── README.md                      # Overview of DRL stock trading project & SSRN paper reference
├── main.ipynb                     # Main 600 KB Jupyter Notebook containing full pipeline
├── main_extracted.py              # Extracted 22 KB python script corresponding to main.ipynb
├── Documents/
│   └── ssrn-3690996 (2).pdf       # Research paper: "Deep Reinforcement Learning for Automated Stock Trading"
├── notebooks/                     # Mirror copy of main.ipynb and 30 stock CSVs
│   ├── main.ipynb
│   └── *.csv (30 files)
└── *.csv                          # 30 Dow Jones constituent stock CSV datasets (AAPL.csv ... XOM.csv)
```

### 2.2 Detailed Asset CSV Inventory

| Ticker | File Name | Size (Bytes) | Row Count | Start Date | End Date | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AAPL** | `AAPL.csv` | 316,594 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **AXP** | `AXP.csv` | 306,098 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **BA** | `BA.csv` | 303,681 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **CAT** | `CAT.csv` | 303,796 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **CSCO** | `CSCO.csv` | 314,229 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **CVX** | `CVX.csv` | 308,119 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **DIS** | `DIS.csv` | 308,123 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **DOW** | `DOW.csv` | 30,723 | 288 | 2019-03-20 | 2020-05-07 | **Truncated** (Spin-off 2019) |
| **GS** | `GS.csv` | 307,191 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **HD** | `HD.csv` | 309,168 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **IBM** | `IBM.csv` | 318,839 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **INTC** | `INTC.csv` | 312,864 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **JNJ** | `JNJ.csv` | 307,428 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **JPM** | `JPM.csv` | 310,291 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **KO** | `KO.csv` | 311,246 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **MCD** | `MCD.csv` | 304,617 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **MMM** | `MMM.csv` | 315,158 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **MRK** | `MRK.csv` | 316,179 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **MSFT** | `MSFT.csv` | 311,996 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **NKE** | `NKE.csv` | 307,578 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **PFE** | `PFE.csv` | 321,148 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **PG** | `PG.csv` | 303,809 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **TRV** | `TRV.csv` | 309,318 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **UNH** | `UNH.csv` | 307,486 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **UTX** | `UTX.csv` | 42 | **0** | N/A | N/A | **Empty Header** (Raytheon Merger) |
| **V** | `V.csv` | 307,181 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **VZ** | `VZ.csv` | 312,021 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **WBA** | `WBA.csv` | 305,476 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **WMT** | `WMT.csv` | 319,614 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |
| **XOM** | `XOM.csv` | 304,258 | 2,857 | 2009-01-02 | 2020-05-07 | Complete |

---

## 3. Detailed Technical Analysis of Existing Pipeline (`main_extracted.py`)

### 3.1 Data Preparation & Technical Indicators
- **Data Splitting**:
  - Training Period: `2009-01-01` to `2015-12-31`
  - Validation Period: `2016-01-01` to `2016-12-31`
  - Test Period: `2017-01-01` to `2020-05-08`
- **Indicator Computations (`add_technical_indicators`)**:
  - `RSI` (14-period Relative Strength Index)
  - `EMA12`, `EMA26`, `MACD`, `Signal` (EMA9 of MACD)
  - `CCI` (20-period Commodity Channel Index)
  - `ADX` (14-period Average Directional Index with `+DI` and `-DI`)
  - Features retained per stock (10 features): `['Open', 'High', 'Low', 'Close', 'Volume', 'MACD', 'Signal', 'RSI', 'CCI', 'ADX']`

### 3.2 Gymnasium Environment (`StockTradingEnv`)
- **Class Signature**: `class StockTradingEnv(gym.Env)`
- **Action Space**: `spaces.Box(low=-1, high=1, shape=(len(tickers),), dtype=np.float32)`.
  - continuous vector where action $a_i > 0$ means buy fraction of cash balance, $a_i < 0$ means sell fraction of held shares.
- **Observation Space**: `spaces.Box(low=-np.inf, high=np.inf, shape=(obs_shape,), dtype=np.float32)`.
  - Observation size calculation: $10 \times N + 2 + N + 2 = 11N + 4$. For $N=30$, size = 334.
  - State vector elements: `[stock_features_0..N-1, balance, shares_held_0..N-1, net_worth, max_net_worth, current_step]`.
- **Step Dynamics**:
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

### 3.3 Agents & Training Routine
- **Framework**: Stable-Baselines3 (`from stable_baselines3 import PPO, A2C, DDPG`)
- **Vectorized Env**: `DummyVecEnv([lambda: StockTradingEnv(data)])`
- **Agents**:
  - `PPOAgent`: `PPO("MlpPolicy", env, verbose=1)`
  - `A2CAgent`: `A2C("MlpPolicy", env, verbose=1)`
  - `DDPGAgent`: `DDPG("MlpPolicy", env, verbose=1)`
  - `EnsembleAgent`: Custom class averaging predicted action vectors across PPO, A2C, and DDPG models:
    $$\mathbf{a}_{\text{ensemble}} = \frac{1}{3} (\mathbf{a}_{\text{PPO}} + \mathbf{a}_{\text{A2C}} + \mathbf{a}_{\text{DDPG}})$$

---

## 4. Flaws, Bugs & Architectural Vulnerabilities in Parent Repo

1. **Non-Stationary Cumulative Profit Reward Signal**:
   - In `StockTradingEnv.step()` (line 245 of `main_extracted.py`):
     `reward = self.net_worth - self.initial_balance`
   - *Issue*: `net_worth - initial_balance` measures overall total profit from day 0 to day $t$. At step $t=500$, the reward signal is dominated by cumulative history rather than the immediate action taken at step $t$. This breaks Markov Decision Process (MDP) assumptions, leading to instability during PPO/A2C policy gradient updates.
   - *Fix*: Replace with per-step rate of return minus risk/drawdown penalties:
     $$r_{t} = \frac{V_t - V_{t-1}}{V_{t-1}} - \text{Penalties}$$

2. **Missing Transaction Fees**:
   - In `step()` (lines 228-240 of `main_extracted.py`):
     `cost = shares_to_buy * current_prices[ticker]`
     `sale = shares_to_sell * current_prices[ticker]`
     No fee percentage (e.g. 0.1% or 10 bps) is deducted. This causes the RL agent to overtrade violently, resulting in unrealistic backtest performance.
   - *Fix*: Apply transaction fee factor $\eta = 0.001$:
     $$\text{cost} = \text{shares} \times P_t \times (1 + \eta), \quad \text{sale} = \text{shares} \times P_t \times (1 - \eta)$$

3. **Evaluation Backtesting Code Bug**:
   - In lines 551-565 of `main_extracted.py`:
     ```python
     test_env = DummyVecEnv([lambda: StockTradingEnv(test_data)])
     # BUG HERE:
     test_and_visualize_agents(env, test_agents, test_data, n_tests=n_tests)
     ```
     `env` (the training environment instance) is passed to `test_and_visualize_agents` instead of `test_env`. The evaluation function executes steps on training data while logging test labels!

4. **Corrupted Stock File Ingestion Risk**:
   - `UTX.csv` is 42 bytes (empty data). While `StockTradingEnv` filters out empty DataFrames via `{k: v for k, v in data.items() if not v.empty}`, `DOW.csv` has only 288 rows. If `loc['2009-01-01':'2015-12-31']` is called on `DOW`, it returns an empty slice, causing variable observation vector shapes.
   - *Fix*: Explicitly clean and exclude `UTX` and `DOW` in `data_pipeline.py`, locking the active asset universe to 28 verified clean stocks.

5. **RSI Code Duplication**:
   - In `add_technical_indicators()`, lines 79-83 and lines 92-96 compute `df['RSI']` identically twice.

---

## 5. Identification of Existing Libraries & Environment Availability

| Library Name | Status in Codebase | Role in Parent Repo | Target Role in `Optimized_RL_Trading_Strategy` |
| :--- | :--- | :--- | :--- |
| `stable_baselines3` | Used | Core DRL framework (PPO, A2C, DDPG) | Core DRL trainer (`train_optimized.py`, CPU bound) |
| `gymnasium` | Used | Environment interface (`gym.Env`, `spaces.Box`) | Custom environment (`custom_env.py`) |
| `pandas` | Used | Data handling & feature calculation | Panel data transformation in `data_pipeline.py` |
| `numpy` | Used | Matrix operations & array indexing | Feature math & state vector construction |
| `matplotlib` | Used | Metric plotting & equity curve visualization | Backtesting plots in `evaluate.py` & `main.ipynb` |
| `yfinance` | Used | Data download script | Optional data refresh utility |
| `torch` | Dependency | PyTorch backend for SB3 | CPU execution runtime (`torch.set_num_threads`) |
| `hmmlearn` | Target Needed | Not in parent repo | GaussianHMM 3-state market regime classification |
| `statsmodels` / `arch` | Target Needed | Not in parent repo | GARCH(1,1) conditional volatility fitting |
| `finrl` | Context Ref | Conceptual paper foundation | Benchmark comparison reference |

*Note on Execution Environment*: In accordance with tool interaction protocols, automated Python inline check script (`run_command`) timed out waiting for user prompt approval. All library dependencies and code inspections were successfully completed statically.

---

## 6. Strategic Recommendations & Alignment with Target Architecture

To transition from the legacy parent repo to `Optimized_RL_Trading_Strategy`, the team must implement four core modules:

1. **`data_pipeline.py` (Milestone 1)**:
   - Filter out `UTX` and `DOW`, utilizing the 28 clean DJIA constituent stocks.
   - Expand standard indicators to include:
     - Volatility Clustering: EWMA ($\lambda=0.94$), Rolling Volatility Ratio ($5\text{d}/20\text{d}$), GARCH(1,1).
     - Spoofing Proxies: Volume Imbalance Proxy (VIP), Order Flow Imbalance (OFI), Corwin-Schultz Spread.
     - News Shocks: Z-score return shocks, volume-volatility joint jump spikes.
     - Regimes: 3-State Gaussian Hidden Markov Model (Bullish Low-Vol, Ranging, Bearish High-Vol).

2. **`custom_env.py` (Milestone 2)**:
   - Expand observation space to 575 dimensions ($28 \text{ stocks} \times 18 \text{ features} + 30 \text{ portfolio} + 3 \text{ regime}$).
   - Formulate Step Return + Drawdown Penalty Reward:
     $$R_t = r_{p,t} - \eta \sum |a_{i,t} - a_{i,t-1}| P_{i,t} - \lambda_{\text{DD}} \text{DD}_t - \mu_{\text{DD}} (\Delta \text{DD}_t)^2 - \theta \sigma_{p,t} \mathbb{I}(\text{Bearish})$$
   - Implement strict Gymnasium compliance (`terminated, truncated, info`).

3. **`train_optimized.py` (Milestone 3)**:
   - Force CPU training (`device='cpu'`) with `stable_baselines3.PPO` for reproducibility.
   - Add `EvalCallback` and checkpoint saving to `trained_models/ppo_dow30_cpu.zip`.

4. **`evaluate.py` & `main.ipynb` (Milestone 4)**:
   - Fix evaluation script bugs, ensuring backtesting runs strictly on out-of-sample test datasets.
   - Compute Sharpe, Sortino, Max Drawdown, and Cumulative Return metrics.

---

*Analysis report concluded.*
