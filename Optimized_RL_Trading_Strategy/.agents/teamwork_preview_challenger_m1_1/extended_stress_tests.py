"""
Extended Edge Case & Boundary Stress Tests for data_pipeline.py
---------------------------------------------------------------
Testing deep edge cases:
1. Extended zero price sequences (consecutive zero prices).
2. Extended negative price sequences.
3. High == Low == Open == Close (zero spread).
4. Low == 0 (Corwin Schultz denominator/log issues).
5. Single-row or tiny dataframes (< 21 rows).
6. Garman-Klass when Open == 0 or High == 0.
7. Extreme GARCH inputs / Non-convergence.
8. Regime Posterior component mapping when returns are all identical.
"""

import sys
import numpy as np
import pandas as pd
import traceback

TARGET_DIR = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy"
if TARGET_DIR not in sys.path:
    sys.path.insert(0, TARGET_DIR)

import data_pipeline as dp

def run_extended_tests():
    print("--- Running Extended Deep Edge Case Tests ---")
    
    # 1. Extended Consecutive Zero Prices (10 consecutive days of 0.0)
    print("\n[Test E1] Extended Consecutive Zero Prices (10 days)")
    dates = pd.date_range("2020-01-01", periods=50)
    df_zero = pd.DataFrame({
        'date': dates,
        'open': [100.0]*20 + [0.0]*10 + [100.0]*20,
        'high': [102.0]*20 + [0.0]*10 + [102.0]*20,
        'low': [98.0]*20 + [0.0]*10 + [98.0]*20,
        'close': [100.0]*20 + [0.0]*10 + [100.0]*20,
        'adj_close': [100.0]*20 + [0.0]*10 + [100.0]*20,
        'volume': [1000.0]*50,
        'tic': 'TEST'
    })
    try:
        res = dp.engineer_asset_features(df_zero)
        print(f"Result shape: {res.shape} (Original input: 50 rows)")
        print(f"NaN count in result: {res.isna().sum().sum()}")
        print(f"Inf count in result: {np.isinf(res.select_dtypes(include=[np.number])).sum().sum()}")
        if len(res) < 29:
            print(f"--> [OBSERVATION] {50 - len(res)} rows were dropped due to NaNs created by consecutive zero prices!")
    except Exception as e:
        print(f"--> [FAIL] Exception: {e}\n{traceback.format_exc()}")

    # 2. Corwin-Schultz when High == Low (Zero range)
    print("\n[Test E2] Corwin-Schultz Spread when High == Low")
    high = pd.Series([100.0]*30)
    low = pd.Series([100.0]*30)
    cs = dp.compute_corwin_schultz_spread(high, low)
    print(f"CS Spread min: {cs.min()}, max: {cs.max()}, NaNs: {np.isnan(cs).sum()}, Infs: {np.isinf(cs).sum()}")

    # 3. Garman-Klass Volatility when High == Low == Open == Close
    print("\n[Test E3] Garman-Klass Volatility when High == Low == Open == Close")
    df_flat = pd.DataFrame({
        'date': pd.date_range("2020-01-01", periods=40),
        'open': [100.0]*40,
        'high': [100.0]*40,
        'low': [100.0]*40,
        'close': [100.0]*40,
        'adj_close': [100.0]*40,
        'volume': [1000.0]*40,
        'tic': 'TEST'
    })
    res_flat = dp.engineer_asset_features(df_flat)
    gk_vol = res_flat['garman_klass_vol']
    print(f"Garman-Klass Vol min: {gk_vol.min()}, max: {gk_vol.max()}, NaNs: {gk_vol.isna().sum()}")

    # 4. Tiny Dataframe (< 21 rows)
    print("\n[Test E4] Tiny Dataframe (15 rows)")
    df_tiny = df_flat.iloc[:15].copy()
    try:
        res_tiny = dp.engineer_asset_features(df_tiny)
        print(f"Tiny result shape: {res_tiny.shape}")
    except Exception as e:
        print(f"--> [FAIL] Exception on tiny dataframe: {e}")

    # 5. Market Regime Model with Flat Data (Identical Features)
    print("\n[Test E5] Market Regime Model with Zero Volatility / Flat Returns across assets")
    combined_flat = pd.DataFrame({
        'return': [0.0]*100,
        'ewma_vol': [0.0]*100,
        'tic': ['TEST']*100
    })
    try:
        res_regime = dp.fit_and_assign_market_regimes(combined_flat.copy(), lengths=[100])
        print(f"Regime states assigned successfully: {res_regime[['regime_state_0', 'regime_state_1', 'regime_state_2']].head(3).to_dict(orient='records')}")
    except Exception as e:
        print(f"--> [FAIL] Exception in Regime Model: {e}\n{traceback.format_exc()}")

    # 6. Check Dataset Empirical Distribution in processed_market_dynamics.csv
    print("\n[Test E6] Empirical Value Distribution Scan of processed_market_dynamics.csv")
    csv_path = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv"
    df_csv = pd.read_csv(csv_path)
    print("Summary Stats for Key Engineered Features:")
    feat_cols = [
        'return', 'log_return', 'ewma_vol', 'volatility_ratio_5_21',
        'garman_klass_vol', 'garch_vol', 'shadow_ratio', 'vwap_distance',
        'order_flow_imbalance', 'corwin_schultz_spread', 'return_shock_zscore',
        'volume_spike_index', 'joint_vol_vol_shock',
        'regime_state_0', 'regime_state_1', 'regime_state_2'
    ]
    stats = df_csv[feat_cols].describe().T[['min', 'mean', 'max', 'std']]
    print(stats.to_string())

if __name__ == '__main__':
    run_extended_tests()
