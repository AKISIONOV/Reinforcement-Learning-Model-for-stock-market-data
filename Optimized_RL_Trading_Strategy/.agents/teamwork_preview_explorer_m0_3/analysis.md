# Technical Architecture & Algorithmic Specification Report

**Author**: Explorer 3 (Architecture & Feature Design)  
**Milestone**: M0 — Architecture & Feature Design  
**Target Repository**: `Optimized_RL_Trading_Strategy`  
**Date**: 2026-07-31  

---

## Executive Summary

This report delivers the complete mathematical formulations, algorithmic specifications, observation space designs, drawdown-penalized reward functions, and CPU training strategy for the **Optimized RL Trading Strategy** project. 

The strategy expands traditional OHLCV indicators with advanced quantitative features:
1. **Volatility Clustering**: GARCH(1,1), EWMA Volatility, and Rolling Volatility Ratio.
2. **Spoofing Proxies**: Volume Imbalance Proxy (VIP), Order Flow Imbalance (OFI), Corwin-Schultz Spread Proxy, and Spoofing Pattern Score.
3. **News Shocks**: Return Shock Jump Indicator and Joint Volume-Volatility News Spike Proxy.
4. **Intraday Market Regimes**: Gaussian Hidden Markov Model (GaussianHMM) and KMeans Trend-Volatility Clustering.

Furthermore, we define an expanded **Gymnasium Observation Space** (575 dimensions across 30 Dow Jones stocks), a **Drawdown-Penalized Sortino/Sharpe Reward Function**, and a **Standalone CPU Execution Strategy** (`train_optimized.py`, `device='cpu'`) powered by Stable-Baselines3.

---

## 1. Mathematical Definitions & Algorithmic Feature Specifications

### 1.1 Volatility Clustering Features

Volatility clustering reflects the empirical property of financial asset returns where high-volatility days are followed by high-volatility days, and low-volatility days are followed by low-volatility days.

#### A. GARCH(1,1) Model Specification
- **Log Return Definition**:
  $$r_t = \ln\left(\frac{P_t}{P_{t-1}}\right) = \mu + \epsilon_t, \quad \epsilon_t = \sigma_t z_t, \quad z_t \sim \text{i.i.d. } \mathcal{N}(0, 1)$$

- **Conditional Variance Recurrence Equation**:
  $$\sigma_t^2 = \omega + \alpha \epsilon_{t-1}^2 + \beta \sigma_{t-1}^2$$
  *Constraints*: $\omega > 0$, $\alpha \ge 0$, $\beta \ge 0$, and $\alpha + \beta < 1$ (stationarity condition).
  *Unconditional Variance*: $\sigma_{\text{uncond}}^2 = \frac{\omega}{1 - \alpha - \beta}$.

- **Estimation Algorithm**:
  1. Fit parameters $(\hat{\mu}, \hat{\omega}, \hat{\alpha}, \hat{\beta})$ on a rolling window of length $W = 252$ trading days via Maximum Likelihood Estimation (MLE) using the `arch` Python library (`arch_model(r_t, vol='Garch', p=1, q=1)`).
  2. Fallback heuristic (if MLE fails to converge or `arch` package is unavailable):
     $$\hat{\alpha} = 0.05, \quad \hat{\beta} = 0.90, \quad \hat{\omega} = (1 - \hat{\alpha} - \hat{\beta}) \cdot \text{Var}(r_{t-W:t})$$
  3. Forecast one-step-ahead conditional volatility:
     $$\hat{\sigma}_{t+1|t} = \sqrt{\hat{\omega} + \hat{\alpha} \hat{\epsilon}_t^2 + \hat{\beta} \hat{\sigma}_t^2}$$

#### B. Exponentially Weighted Moving Average (EWMA) Volatility
- **Formula (RiskMetrics Specification)**:
  $$\sigma_{t, \text{EWMA}}^2 = \lambda \sigma_{t-1, \text{EWMA}}^2 + (1 - \lambda) r_t^2$$
  where decay factor $\lambda = 0.94$ for daily data (or $\lambda = 0.97$ for higher frequency).

- **Vectorized Pandas Implementation**:
  $$\sigma_{t, \text{EWMA}} = \sqrt{ \text{EWM}_{\alpha=1-\lambda} (r_t^2) }$$
  ```python
  df['ewma_vol'] = np.sqrt((df['return']**2).ewm(alpha=1-0.94, adjust=False).mean())
  ```

#### C. Rolling Volatility Ratio
- **Definition**: Quantifies sudden short-term volatility expansion relative to long-term baseline volatility.
  $$\text{VR}_t^{(w_s, w_l)} = \frac{\sigma_{t, w_s}}{\sigma_{t, w_l}} = \frac{\sqrt{\frac{1}{w_s-1} \sum_{k=0}^{w_s-1} (r_{t-k} - \bar{r}_{s})^2}}{\sqrt{\frac{1}{w_l-1} \sum_{k=0}^{w_l-1} (r_{t-k} - \bar{r}_{l})^2}}$$
  *Parameters*: Short window $w_s = 5$ days, Long window $w_l = 20$ days (or 60 days).
  *Interpretation*: $\text{VR}_t > 1.5$ signals volatility regime expansion; $\text{VR}_t < 0.7$ signals volatility compression.

---

### 1.2 Spoofing & Microstructure Anomaly Proxies

In daily/intraday aggregate OHLCV data without full L2/L3 order book depth, spoofing proxies estimate order imbalance and price manipulation signals.

#### A. Volume Imbalance Proxy (VIP)
- **Bar-Level Intra-Bar Buy/Sell Volume Disaggregation (Lee-Ready / Tick-Rule Adaptation)**:
  $$V_{\text{buy}, t} = V_t \cdot \frac{C_t - L_t}{H_t - L_t + \epsilon}, \quad V_{\text{sell}, t} = V_t \cdot \frac{H_t - C_t}{H_t - L_t + \epsilon}$$
  where $\epsilon = 10^{-8}$ prevents division by zero.

- **Volume Imbalance Proxy Formula**:
  $$\text{VIP}_t = \frac{V_{\text{buy}, t} - V_{\text{sell}, t}}{V_t + \epsilon} = \frac{2 C_t - H_t - L_t}{H_t - L_t + \epsilon} \in [-1.0, +1.0]$$

#### B. Order Flow Imbalance Proxy (OFI)
- **Formula**: Measures net order flow pressure direction multiplied by bar volume:
  $$\text{OFI}_t = \text{sign}(C_t - C_{t-1}) \times V_t$$
- **Rolling Normalized OFI**:
  $$\text{OFI}_{\text{norm}, t} = \frac{\text{OFI}_t - \text{SMA}(\text{OFI}_t, W)}{\text{std}(\text{OFI}_t, W) + \epsilon}$$

#### C. Bid-Ask Spread Proxy (Corwin-Schultz Estimator)
- **Corwin-Schultz (2012) High-Low Spread Estimator**:
  $$\gamma_t = \left[ \ln\left(\frac{\max(H_t, H_{t+1})}{\min(L_t, L_{t+1})}\right) \right]^2, \quad \beta_t = \left[ \ln\left(\frac{H_t}{L_t}\right) \right]^2 + \left[ \ln\left(\frac{H_{t+1}}{L_{t+1}}\right) \right]^2$$
  $$\alpha_t = \frac{\sqrt{2\beta_t} - \sqrt{\beta_t}}{3 - 2\sqrt{2}} - \sqrt{\frac{\gamma_t}{3 - 2\sqrt{2}}}$$
  $$\text{Spread}_{\text{CS}, t} = \frac{2 (e^{\alpha_t} - 1)}{1 + e^{\alpha_t}}$$
- **Simplified Relative High-Low Range Spread**:
  $$\text{Spread}_{\text{proxy}, t} = \frac{H_t - L_t}{\frac{1}{2}(H_t + L_t)}$$

#### D. Spoofing Order Pattern Score ($S_{\text{spoof}}$)
- Spoofing involves submitting massive unexecuted bid/ask volume imbalance followed by immediate price reversal.
- **Pattern Score Formula**:
  $$S_{\text{spoof}, t} = \left| \text{Z-score}(\text{VIP}_t) \right| \times \left( \frac{V_t}{\text{SMA}(V_t, W)} \right) \times \mathbb{I}\Big( \text{sign}(r_{t+1}) \neq \text{sign}(r_t) \text{ and } |r_t| > 2 \sigma_r \Big)$$
  *Score Properties*: Non-negative score $S_{\text{spoof}, t} \ge 0$. High values indicate anomalous liquidity placement and price reversion risks.

---

### 1.3 News Shock & Jump Indicators

#### A. Return Shock Jump Indicator ($J_t$)
- **Non-Parametric Standardized Return Jump Test**:
  $$J_t = \mathbb{I}\left( \frac{|r_t - \mu_r(W)|}{\sigma_r(W)} > \theta_{\text{jump}} \right)$$
  where $\theta_{\text{jump}} = 3.0$ standard deviations.
- **Continuous Shock Intensity**:
  $$J_{\text{cont}, t} = \max\left(0, \frac{|r_t - \mu_r(W)|}{\sigma_r(W)} - \theta_{\text{jump}}\right)$$

#### B. Sentiment / Joint Volume-Volatility Spike Proxy ($S_{\text{news}}$)
- Captures unexpected market-moving news events without external text sentiment APIs.
- **Formula**:
  $$S_{\text{news}, t} = \left( \frac{r_t - \mu_r(W)}{\sigma_{t, \text{EWMA}}} \right)^2 \times \ln\left(1 + \frac{V_t}{\text{SMA}(V, W)}\right)$$
- **Normalized & Clipped Proxy**:
  $$\text{NewsShockProxy}_t = \text{clip}\left( \frac{S_{\text{news}, t} - \mu_S(W)}{\sigma_S(W)}, 0, 5.0 \right)$$

---

### 1.4 Intraday Market Regimes

#### A. Gaussian Hidden Markov Model (GaussianHMM)
- **State Space**: $K = 3$ hidden regimes:
  - **State 0 (Bullish Low-Vol)**: High mean return $\mu_r > 0$, low variance $\sigma_r^2$.
  - **State 1 (Neutral / Ranging)**: Mean return $\mu_r \approx 0$, moderate variance.
  - **State 2 (Bearish High-Vol)**: Negative mean return $\mu_r < 0$, high variance $\sigma_r^2$.

- **Observation Feature Vector**:
  $$\mathbf{x}_t = [r_t, \sigma_{t, \text{EWMA}}, \text{Spread}_{\text{proxy}, t}]^T \in \mathbb{R}^3$$

- **Inference & Implementation**:
  ```python
  from hmmlearn.hmm import GaussianHMM
  model = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
  model.fit(X_train)
  regime_labels = model.predict(X_all)
  regime_probs = model.predict_proba(X_all)  # Output 3 continuous probabilities
  ```

#### B. KMeans Trend-Volatility Regime Clustering
- Fast, non-probabilistic fallback clustering.
- Feature Space: $Z_t = [\text{Z-score}(\text{SMA}_{20}(r_t)), \text{Z-score}(\sigma_{t, 20})]^T$.
- Centroids $\mathbf{c}_0, \mathbf{c}_1, \mathbf{c}_2, \mathbf{c}_3$ computed on training set; assigned via Euclidean distance:
  $$k_t^* = \arg\min_{k \in \{0,1,2,3\}} \| Z_t - \mathbf{c}_k \|_2$$

---

## 2. Gymnasium Environment & Drawdown Penalty Reward Design

### 2.1 State Observation Space Expansion

#### Feature Matrix Breakdown per Ticker $i \in \{1 \dots N\}$:
Each asset $i$ at timestep $t$ is represented by 18 features:
1. $C_{i,t}$ (Close Price / Initial Price)
2. $O_{i,t}$ (Open / Close ratio)
3. $H_{i,t}$ (High / Close ratio)
4. $L_{i,t}$ (Low / Close ratio)
5. $V_{i,t}$ (Volume z-score)
6. $\text{RSI}_{i,t}$ (Relative Strength Index 14)
7. $\text{MACD}_{i,t}$ (MACD line)
8. $\text{CCI}_{i,t}$ (Commodity Channel Index)
9. $\text{ADX}_{i,t}$ (Average Directional Index)
10. $\hat{\sigma}_{i,t,\text{GARCH}}$ (GARCH(1,1) Volatility)
11. $\sigma_{i,t,\text{EWMA}}$ (EWMA Volatility)
12. $\text{VR}_{i,t}$ (Rolling Volatility Ratio)
13. $\text{VIP}_{i,t}$ (Volume Imbalance Proxy)
14. $\text{OFI}_{i,t}$ (Order Flow Imbalance Proxy)
15. $\text{Spread}_{i,t}$ (Bid-Ask Spread Proxy)
16. $S_{i,t,\text{spoof}}$ (Spoofing Pattern Score)
17. $J_{i,t}$ (Return Shock Jump Indicator)
18. $S_{i,t,\text{news}}$ (News Shock Proxy)

#### Global Portfolio State Vector:
$$\mathbf{p}_t = [ \text{Cash}_t / V_{\text{initial}}, w_{1,t}, w_{2,t}, \dots, w_{N,t}, \text{DD}_t ] \in \mathbb{R}^{N+2}$$

#### Market Regime State Vector:
$$\mathbf{m}_t = [ P(S_t=0), P(S_t=1), P(S_t=2) ] \in \mathbb{R}^3$$

#### Total Observation Space Dimension:
For $N = 30$ Dow Jones tickers:
$$D_{\text{obs}} = (N + 2) + N \times 18 + K = (30 + 2) + 30 \times 18 + 3 = 32 + 540 + 3 = 575 \text{ dimensions}$$

#### Gymnasium Definition (`custom_env.py`):
```python
import gymnasium as gym
from gymnasium import spaces
import numpy as np

class CustomTradingEnv(gym.Env):
    def __init__(self, df, num_stock=30, initial_amount=1000000):
        super().__init__()
        self.num_stock = num_stock
        self.initial_amount = initial_amount
        
        # Action space: Continuous allocation weight change per stock [-1.0, +1.0]
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(self.num_stock,), dtype=np.float32)
        
        # Observation space: 575 continuous features
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(575,), dtype=np.float32)
```

---

### 2.2 Drawdown Penalty & Risk-Adjusted Reward Formulations

#### A. Step Return & Portfolio Value
$$V_t = \text{Cash}_t + \sum_{i=1}^N a_{i,t} P_{i,t}$$
$$r_{p, t} = \frac{V_t - V_{t-1}}{V_{t-1}}$$

#### B. Peak Value & Drawdown Recurrence
$$H_t = \max_{0 \le \tau \le t} V_\tau$$
$$\text{DD}_t = \frac{H_t - V_t}{H_t} \in [0, 1)$$
$$\Delta \text{DD}_t = \max\left(0, \text{DD}_t - \text{DD}_{t-1}\right)$$

#### C. Sharpe & Sortino Ratios (Rolling Window $W = 60$)
- **Rolling Mean Return**: $\bar{r}_{p, t, W} = \frac{1}{W} \sum_{\tau=t-W+1}^t r_{p, \tau}$
- **Rolling Volatility**: $\sigma_{p, t, W} = \sqrt{\frac{1}{W-1} \sum_{\tau=t-W+1}^t (r_{p, \tau} - \bar{r}_{p, t, W})^2}$
- **Rolling Downside Deviation**:
  $$\sigma_{\text{downside}, t, W} = \sqrt{ \frac{1}{W} \sum_{\tau=t-W+1}^t \min\left(0, r_{p, \tau} - r_f\right)^2 }$$
- **Sharpe Ratio Reward Component**:
  $$R_{\text{Sharpe}, t} = \frac{\bar{r}_{p, t, W} - r_f}{\sigma_{p, t, W} + 10^{-6}}$$
- **Sortino Ratio Reward Component**:
  $$R_{\text{Sortino}, t} = \frac{\bar{r}_{p, t, W} - r_f}{\sigma_{\text{downside}, t, W} + 10^{-6}}$$

#### D. Unified Composite Penalized Reward Function Formula
$$R_t = r_{p, t} - \eta \cdot \sum_{i=1}^N |a_{i,t} - a_{i,t-1}| \cdot P_{i,t} - \lambda_{\text{DD}} \cdot \text{DD}_t - \mu_{\text{DD}} \cdot (\Delta \text{DD}_t)^2 - \theta \cdot \sigma_{p, t, W} \cdot \mathbb{I}(\text{Regime}_t = \text{Bearish High-Vol})$$

*Hyperparameter Coefficients*:
- Transaction fee factor $\eta = 0.001$ (10 bps per trade).
- Linear drawdown penalty coefficient $\lambda_{\text{DD}} = 0.5$.
- Quadratic peak drawdown penalty coefficient $\mu_{\text{DD}} = 2.0$.
- Bearish volatility penalty coefficient $\theta = 0.1$.

---

## 3. Standalone CPU Execution Strategy Design (`train_optimized.py`)

### 3.1 Hard Hardware Constraint (`device='cpu'`)
To ensure reliable, reproducible execution across workstation environments without relying on CUDA/GPU availability, training is explicitly bound to CPU execution.

```python
import torch
import os

# Force PyTorch to single/multi-thread CPU execution
device = "cpu"
num_threads = os.cpu_count() or 4
torch.set_num_threads(num_threads)
os.environ["OMP_NUM_THREADS"] = str(num_threads)
os.environ["MKL_NUM_THREADS"] = str(num_threads)
```

### 3.2 Stable-Baselines3 PPO Configuration

```python
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import EvalCallback

def train_cpu_agent(env, total_timesteps=100000, save_dir="trained_models"):
    os.makedirs(save_dir, exist_ok=True)
    
    vec_env = DummyVecEnv([lambda: env])
    
    model = PPO(
        policy="MlpPolicy",
        env=vec_env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=128,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        verbose=1,
        device="cpu",  # FORCED CPU DEVICE
        policy_kwargs=dict(net_arch=dict(pi=[256, 256], vf=[256, 256]))
    )
    
    eval_callback = EvalCallback(
        vec_env,
        best_model_save_path=save_dir,
        log_path=save_dir,
        eval_freq=5000,
        deterministic=True,
        render=False
    )
    
    model.learn(total_timesteps=total_timesteps, callback=eval_callback)
    model.save(os.path.join(save_dir, "ppo_dow30_cpu"))
    return model
```

### 3.3 Target File Architecture & Interaction Diagram

```
Optimized_RL_Trading_Strategy/
├── data_pipeline.py        <-- Generates GARCH, EWMA, Spoofing, Shock, Regime features
├── custom_env.py           <-- Defines 575-dim state & Drawdown Penalized Reward
├── train_optimized.py      <-- Runs CPU SB3 PPO training loop & saves ppo_dow30_cpu.zip
├── evaluate.py             <-- Evaluates portfolio metrics (Sortino, Sharpe, Max Drawdown)
└── trained_models/         <-- Stores trained agent weights
```

---

## 4. Verification & Validation Framework

1. **Feature Consistency Test**: Ensure zero NaN values across GARCH rolling windows, EWMA, and HMM state probability outputs in `data_pipeline.py`.
2. **Environment Compliance Test**: Run `gymnasium.utils.env_checker.check_env(CustomTradingEnv())` to verify gym API contract compliance.
3. **CPU Execution Test**: Verify PyTorch model tensor allocations are on `torch.device('cpu')` during training.
4. **Reward Penalty Sensitivity Test**: Compare agent equity curve under $\lambda_{\text{DD}}=0.0$ vs $\lambda_{\text{DD}}=0.5$ to confirm drawdown reduction.

---

*Report concluded.*
