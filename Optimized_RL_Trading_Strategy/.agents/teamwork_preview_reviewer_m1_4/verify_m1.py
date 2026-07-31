import os
import pandas as pd
import numpy as np

def run_verification():
    csv_path = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv"
    print(f"Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    
    print("\n--- 1. OVERVIEW & INTEGRITY ---")
    print("Shape:", df.shape)
    print("Columns:", list(df.columns))
    nan_count = df.isna().sum().sum()
    inf_count = np.isinf(df.select_dtypes(include=np.number)).sum().sum()
    print(f"Total NaNs: {nan_count}")
    print(f"Total Infs: {inf_count}")
    
    print("\n--- 2. TICKERS CHECK ---")
    tickers = sorted(df['tic'].unique().tolist())
    print(f"Unique Tickers Count: {len(tickers)}")
    print(f"Tickers List: {tickers}")
    print(f"UTX present: {'UTX' in tickers}")
    print(f"DOW present: {'DOW' in tickers}")
    
    expected_tickers = [
        'AAPL', 'AXP', 'BA', 'CAT', 'CSCO', 'CVX', 'DIS', 'GS', 'HD', 'IBM',
        'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE', 'PFE',
        'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT', 'XOM'
    ]
    print(f"Exactly matches 28 DJIA expected list? {tickers == sorted(expected_tickers)}")
    
    print("\n--- 3. DATE & ALIGNMENT CHECK ---")
    unique_dates = df['date'].nunique()
    min_date = df['date'].min()
    max_date = df['date'].max()
    print(f"Min Date: {min_date}, Max Date: {max_date}, Total Unique Dates: {unique_dates}")
    
    # Check date alignment across tickers
    date_tic_counts = df.groupby('date')['tic'].nunique()
    unaligned_dates = (date_tic_counts != 28).sum()
    print(f"Dates without exactly 28 tickers: {unaligned_dates}")
    
    print("\n--- 4. MARKET DYNAMICS FEATURE VERIFICATION ---")
    
    # Category 1: Volatility Clustering
    vol_cols = ['ewma_vol', 'volatility_ratio_5_21', 'garman_klass_vol', 'garch_vol']
    print("\n[Volatility Clustering Statistics]")
    print(df[vol_cols].describe().T[['min', 'mean', 'max', 'std']])
    
    # Category 2: Spoofing Proxies
    spoof_cols = ['shadow_upper', 'shadow_lower', 'shadow_ratio', 'vwap', 'vwap_distance', 'order_flow_imbalance', 'corwin_schultz_spread']
    print("\n[Spoofing Proxies Statistics]")
    print(df[spoof_cols].describe().T[['min', 'mean', 'max', 'std']])
    
    # Category 3: News Shocks
    news_cols = ['return_shock_zscore', 'return_jump_indicator', 'volume_spike_index', 'joint_vol_vol_shock']
    print("\n[News Shocks Statistics]")
    print(df[news_cols].describe().T[['min', 'mean', 'max', 'std']])
    print("Return Jump count (|z| > 3):", df['return_jump_indicator'].sum(), f"({df['return_jump_indicator'].mean()*100:.2f}%)")
    
    # Category 4: Intraday Regimes
    regime_cols = ['regime_state_0', 'regime_state_1', 'regime_state_2', 'regime_label']
    print("\n[Market Regimes Statistics]")
    print(df[regime_cols].describe().T[['min', 'mean', 'max', 'std']])
    
    # Check sum of posteriors
    posterior_sums = df['regime_state_0'] + df['regime_state_1'] + df['regime_state_2']
    print("Posterior probability sum check (min, max):", posterior_sums.min(), posterior_sums.max())
    print("Regime label counts:")
    print(df['regime_label'].value_counts(normalize=True).sort_index())

if __name__ == '__main__':
    run_verification()
