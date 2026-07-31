# Handoff Report: SB3 Model Loading & Action Interpretation Analysis (M1)

## 1. Observation
- **Model Zip File Location**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/optimal_trading_model.zip` (also accessible at workspace root or `trained_models/best_model.zip`).
- **Zip Internal Contents**:
  - `data` (JSON metadata describing spaces, policy class, hyperparams)
  - `policy.pth` (PyTorch state dict for ActorCriticPolicy network)
  - `policy.optimizer.pth`
  - `pytorch_variables.pth`
  - `system_info.txt` & `_stable_baselines3_version` (Version: `2.9.0`)
- **Model Spaces**:
  - **Observation Space**: `Box(-inf, inf, (567,), float32)`
  - **Action Space**: `Box(-1.0, 1.0, (28,), float32)`
- **Environment Source Code**: `f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/custom_env.py` (lines 81–95, 205–264).
- **Verified Package Versions in Environment**:
  - `stable-baselines3`: `2.9.0`
  - `torch`: `2.10.0+cpu`
  - `gymnasium`: `1.3.0`
  - `pandas`: `3.0.3`
  - `numpy`: `2.4.0`

---

## 2. Logic Chain

### 2.1 Dependencies Required
For loading `optimal_trading_model.zip` and performing inference, the minimum required dependencies are:
- `stable-baselines3 >= 2.0.0` (provides `PPO.load`)
- `torch >= 2.0.0` (PyTorch CPU backend for model evaluation)
- `gymnasium >= 0.29.0` (used internally by SB3 for Box spaces)
- `numpy >= 1.24.0` (state vector array manipulation)
- `pandas >= 2.0.0` (market data frame processing)

### 2.2 Model Loading & Inference Pattern
When performing inference, SB3 does **not** require instantiating or registering the original Gymnasium environment because observation and action spaces are restored from `data` JSON in the zip.

```python
import numpy as np
from stable_baselines3 import PPO

def load_trading_model(model_path: str, device: str = "cpu") -> PPO:
    """
    Loads trained SB3 PPO model from zip archive.
    
    Args:
        model_path: Path to optimal_trading_model.zip
        device: PyTorch device ('cpu' recommended)
    Returns:
        Loaded PPO model instance ready for predict()
    """
    model = PPO.load(model_path, device=device)
    return model

def predict_action(model: PPO, obs_vector: np.ndarray) -> np.ndarray:
    """
    Feeds 567-dim observation vector into model and outputs 28-dim continuous action vector.
    
    Args:
        model: Loaded PPO model
        obs_vector: (567,) float32 numpy array
    Returns:
        action: (28,) float32 numpy array in range [-1.0, 1.0]
    """
    # Sanitize inputs (handle NaNs/Infs if any)
    obs_clean = np.nan_to_num(obs_vector, nan=0.0, posinf=1e6, neginf=-1e6).astype(np.float32)
    
    # SB3 predict
    action, _states = model.predict(obs_clean, deterministic=True)
    
    # Clip explicitly to valid Box range [-1.0, 1.0]
    action = np.clip(action, -1.0, 1.0).astype(np.float32)
    return action
```

### 2.3 Action Interpretation & Weight Mapping Logic
The output action $A = [a_0, a_1, \dots, a_{27}] \in [-1.0, 1.0]^{28}$ maps directly to portfolio trading execution as defined in `custom_env.py` (lines 205–264):

1. **Sell Orders ($a_i < 0$)**:
   - Fraction of existing shares to sell: $\text{sell\_ratio}_i = \min(1.0, |a_i|)$.
   - Shares sold: $\text{sell\_shares}_i = \text{current\_shares}_i \times \text{sell\_ratio}_i$.
   - Realized cash proceeds (net of 10 bps fee): $\Delta \text{Cash} = \text{sell\_shares}_i \times P_i \times (1 - 0.001)$.

2. **Buy / Allocation Target Weights ($a_i > 0$)**:
   - For assets with positive signals ($a_i > 0$), normalized buy allocation weight relative to cash:
     $$w_i = \frac{a_i}{\sum_{j: a_j > 0} a_j}$$
   - Available portfolio cash is allocated across positive-signal assets in proportion $w_i$.
   - Target dollar allocation for buying asset $i$:
     $$\text{Target Buy Cash}_i = \text{Available Cash} \times w_i$$
   - Net buy value after 10 bps transaction fee: $\text{Buy Val}_i = \frac{\text{Target Buy Cash}_i}{1.001}$.
   - Shares acquired: $\text{Shares Bought}_i = \frac{\text{Buy Val}_i}{P_i}$.

3. **Hold Signals ($a_i = 0$)**:
   - Position remains unchanged (no buy or sell execution).

4. **Target Portfolio Weight Conversion (for Rebalancing / Dashboard)**:
   - To compute normalized equity allocation weights $W_{\text{target}} = [w_0, w_1, \dots, w_{27}]$:
     ```python
     pos_mask = action > 0
     pos_sum = np.sum(action[pos_mask])
     target_weights = np.zeros(28, dtype=np.float32)
     if pos_sum > 0:
         target_weights[pos_mask] = action[pos_mask] / pos_sum
     ```

### 2.4 Custom Environment Registration Analysis
- **Issue Identification**:
  Passing string identifiers (e.g. `PPO.load(path, env="StockTradingEnv-v0")`) will fail with `gymnasium.error.UnregisteredEnv` because `StockTradingEnv` is an un-registered custom Python class.
- **Resolution**:
  1. For **Inference / Deployment** (e.g. `trade_executor.py`): Call `PPO.load(path, device='cpu')` **without** passing an `env` parameter. SB3 successfully deserializes the policy network and spaces directly from `data` JSON inside the zip.
  2. For **Evaluation / Training**: Pass the instantiated environment object `StockTradingEnv(...)` or `DummyVecEnv([lambda: StockTradingEnv(...)])` directly to `PPO.load(path, env=eval_env)`.

---

## 3. Caveats
- **All Negative/Zero Actions Edge Case**: If all elements in `action` are $\le 0$, $\sum_{j: a_j > 0} a_j = 0$. The mapping must handle `pos_sum == 0` gracefully by setting `target_weights` to 0 (100% cash allocation).
- **Circuit Breaker Override**: In `custom_env.py`, if portfolio return $< -5\%$, a circuit breaker forces `action = -1.0` (sell all). Execution logic should account for emergency liquidation flags.
- **Bearish Volatility Scaling**: When the market regime is Bearish/High Volatility (Regime state index 2), action magnitude is clipped to $[-0.5, 0.5]$ to prevent aggressive leverage/exposure.

---

## 4. Conclusion
- `optimal_trading_model.zip` can be loaded cleanly using `stable_baselines3.PPO.load(path, device="cpu")`.
- No custom environment registration is required for model loading or inference.
- Continuous actions $A \in [-1.0, 1.0]^{28}$ decompose into:
  - Negative values ($a_i < 0$): Sell fraction $|a_i|$ of position $i$.
  - Positive values ($a_i > 0$): Allocate $w_i = \frac{a_i}{\sum_{a_k > 0} a_k}$ of available cash to asset $i$.
- State input must be a float32 numpy array of shape `(567,)`.

---

## 5. Verification Method

To verify model loading and action mapping independently, run:

```bash
python -c "
import numpy as np
from stable_baselines3 import PPO

# 1. Load model
model = PPO.load('f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/optimal_trading_model.zip', device='cpu')

# 2. Dummy 567-dim observation state
obs = np.random.randn(567).astype(np.float32)

# 3. Predict action
action, _ = model.predict(obs, deterministic=True)
print('Action shape:', action.shape)
print('Action range:', action.min(), 'to', action.max())

# 4. Map to target weights
pos_mask = action > 0
pos_sum = np.sum(action[pos_mask])
target_weights = np.zeros(28, dtype=np.float32)
if pos_sum > 0:
    target_weights[pos_mask] = action[pos_mask] / pos_sum

print('Target weights sum:', target_weights.sum())
"
```

Expected output:
- Action shape: `(28,)`
- Action range: bounded within `[-1.0, 1.0]`
- Target weights sum: `1.0` (or `0.0` if no positive actions)
