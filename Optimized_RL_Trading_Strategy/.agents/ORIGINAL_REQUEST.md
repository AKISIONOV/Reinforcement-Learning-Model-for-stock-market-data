# Original User Request

## 2026-07-31T05:33:12Z

Train an optimal Deep RL model on an existing stock trading codebase to handle intraday regime shifts, spoofing, news shocks, and volatility clustering.

Working directory: f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy

## Requirements

### R1. Data Engineering for Market Dynamics
Modify the data pipeline to engineer features representing volatility clustering, spoofing (e.g., volume imbalance proxies), news shocks, and market regimes. Use the CSV data in the `Deep-Reinforcement-Learning-with-Stock-Trading` clone in the parent directory.

### R2. RL Environment Adaptation
Update the Gymnasium environment to consume the new features and modify the reward function to penalize massive P&L drawdowns (e.g., Sortino or Sharpe-based reward).

### R3. Model Training & Saving
Train the RL model (e.g., PPO or Ensemble) exclusively on CPU and save the best-performing model to the working directory. Output notebooks, a summary of files used, and a README.

## Acceptance Criteria

### Verification
- [ ] A script `train_optimized.py` must run without errors on CPU.
- [ ] The modified environment must correctly process the engineered features (shocks, volatility, spoofing, regimes).
- [ ] The final trained model must be saved in the directory.
- [ ] The generated README must explain how the features address the problem statement.
