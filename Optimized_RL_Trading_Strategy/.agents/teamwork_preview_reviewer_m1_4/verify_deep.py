import os
import pandas as pd
import numpy as np

def run_deep_verification():
    csv_path = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv"
    df = pd.read_csv(csv_path)
    
    print("=== ENVIRONMENT CHECK ===")
    try:
        from arch import arch_model
        print("arch package is INSTALLED")
    except ImportError:
        print("arch package is NOT INSTALLED (fallback used)")
        
    try:
        from hmmlearn.hmm import GaussianHMM
        print("hmmlearn package is INSTALLED")
    except ImportError:
        print("hmmlearn package is NOT INSTALLED (fallback used)")

    print("\n=== REGIME STATE CHARACTERISTICS ===")
    # Calculate weighted mean return and ewma_vol for each regime state
    for state in [0, 1, 2]:
        p = df[f'regime_state_{state}']
        mean_ret = np.average(df['return'], weights=p)
        mean_vol = np.average(df['ewma_vol'], weights=p)
        mean_garch = np.average(df['garch_vol'], weights=p)
        count_label = (df['regime_label'] == state).sum()
        print(f"State {state} (Label Count: {count_label}, {count_label/len(df)*100:.2f}%):")
        print(f"  Weighted Mean Return : {mean_ret:+.6f}")
        print(f"  Weighted Mean EWMA Vol: {mean_vol:.6f}")
        print(f"  Weighted Mean GARCH Vol: {mean_garch:.6f}")
        
    print("\n=== CORRELATIONS BETWEEN VOLATILITY PROXIES ===")
    vol_cols = ['ewma_vol', 'volatility_ratio_5_21', 'garman_klass_vol', 'garch_vol', 'corwin_schultz_spread']
    corr_matrix = df[vol_cols].corr()
    print(corr_matrix.to_string())

    print("\n=== ANTI-CHEATING / INTEGRITY DRILL ===")
    # 1. Check for constant columns (dummy data check)
    constant_cols = [c for c in df.columns if df[c].nunique() <= 1]
    print(f"Constant columns (should be empty): {constant_cols}")
    
    # 2. Check for hardcoded / duplicated values across tickers on same date
    # Select random date
    sample_date = df['date'].iloc[len(df)//2]
    df_sample = df[df['date'] == sample_date]
    print(f"Sample date ({sample_date}) returns across tickers unique count:", df_sample['return'].nunique())
    print(f"Sample date ({sample_date}) garch_vol across tickers unique count:", df_sample['garch_vol'].nunique())

    # 3. Check sequence continuity per ticker
    counts_per_tic = df.groupby('tic').size()
    print(f"Min rows per ticker: {counts_per_tic.min()}, Max rows per ticker: {counts_per_tic.max()}")
    print(f"All 28 tickers have exact same number of rows ({counts_per_tic.iloc[0]}): {counts_per_tic.nunique() == 1}")

if __name__ == '__main__':
    run_deep_verification()
