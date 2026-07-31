import sys
import os
import numpy as np
import pandas as pd

# Add Optimized_RL_Trading_Strategy to path
sys.path.append(r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy")

from custom_env import StockTradingEnv, DEFAULT_TECH_INDICATORS
from data_pipeline import DJIA_28_TICKERS

print("Testing environment observation space...")
data_path = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv"

if os.path.exists(data_path):
    env = StockTradingEnv(df=data_path)
    obs, info = env.reset()
    print(f"Observation shape: {obs.shape}")
    print(f"Observation dtype: {obs.dtype}")
    print(f"Expected obs dim: 567, Actual: {len(obs)}")
    
    # Check components
    cash_norm = obs[0:1]
    shares_scaled = obs[1:29]
    prices = obs[29:57]
    tech_feats = obs[57:533]
    regime_probs = obs[533:536]
    risk_state = obs[536:539]
    prev_actions = obs[539:567]
    
    print(f"1. Cash norm shape: {cash_norm.shape}, sample: {cash_norm}")
    print(f"2. Shares scaled shape: {shares_scaled.shape}")
    print(f"3. Prices shape: {prices.shape}")
    print(f"4. Tech feats shape: {tech_feats.shape} (28 * 17 = {28*17})")
    print(f"5. Regime probs shape: {regime_probs.shape}, sample: {regime_probs}")
    print(f"6. Risk state shape: {risk_state.shape}, sample: {risk_state}")
    print(f"7. Prev actions shape: {prev_actions.shape}")
    
    assert len(obs) == 567, "Obs dim mismatch!"
    print("Verification SUCCESSful!")
else:
    print(f"Data path not found at {data_path}")
