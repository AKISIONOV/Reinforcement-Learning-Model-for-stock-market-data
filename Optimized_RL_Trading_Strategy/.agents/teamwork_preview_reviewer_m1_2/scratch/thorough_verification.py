import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy")
import data_pipeline

SOURCE_DIR = r"f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading"
OUTPUT_FILE = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv"

print("--- Step 1: Running Data Pipeline ---")
data_pipeline.run_pipeline(SOURCE_DIR, OUTPUT_FILE)

print("\n--- Step 2: Loading Exported CSV ---")
df = pd.read_csv(OUTPUT_FILE)

print(f"Dataset shape: {df.shape}")
print(f"Columns ({len(df.columns)}): {list(df.columns)}")

# Check 1: Ticker count & list
tickers = sorted(df['tic'].unique())
print(f"\nTickers ({len(tickers)}): {tickers}")
expected_tickers = sorted(data_pipeline.DJIA_28_TICKERS)
print(f"Tickers match expected DJIA 28 exactly: {tickers == expected_tickers}")

# Check 2: Row count per ticker & date alignment
ticker_counts = df.groupby('tic').size()
print("\nRow count per ticker:")
print(ticker_counts.value_counts())

date_counts = df.groupby('date')['tic'].nunique()
print(f"Dates with all 28 tickers: {(date_counts == 28).sum()} / {len(date_counts)}")
if not (date_counts == 28).all():
    missing_dates = date_counts[date_counts < 28]
    print("Dates missing some tickers:", missing_dates)

# Check 3: Date range
print(f"Date range: min={df['date'].min()}, max={df['date'].max()}")

# Check 4: Nulls / Inf check
null_sums = df.isna().sum()
inf_sums = np.isinf(df.select_dtypes(include=[np.number])).sum()
print("\nNull count total:", null_sums.sum())
print("Inf count total:", inf_sums.sum())

# Check 5: Feature variance & scaling summary
numeric_cols = df.select_dtypes(include=[np.number]).columns
stats = []
for c in numeric_cols:
    val = df[c]
    stats.append({
        'column': c,
        'mean': val.mean(),
        'std': val.std(),
        'min': val.min(),
        'max': val.max(),
        'zero_var': val.std() == 0 or np.isnan(val.std()),
        'zeros_pct': (val == 0).mean() * 100
    })

stats_df = pd.DataFrame(stats)
print("\n--- Feature Statistics Summary ---")
print(stats_df.to_string())

# Check 6: Check regime probabilities sum to 1.0
regime_sum = df[['regime_state_0', 'regime_state_1', 'regime_state_2']].sum(axis=1)
print(f"\nRegime probabilities sum min={regime_sum.min():.6f}, max={regime_sum.max():.6f}")

# Check 7: Fallback testing
print("\n--- Step 3: Fallback Mechanisms Test ---")
# Test GARCH fallback directly
sample_ret = df[df['tic'] == 'AAPL']['return']
garch_pkg = data_pipeline.compute_garch_volatility(sample_ret)
garch_fb = data_pipeline.fallback_garch11(sample_ret)
print(f"GARCH output min/max (pkg/fb): min={garch_fb.min():.6f}, max={garch_fb.max():.6f}")
print(f"GARCH HAS_ARCH={data_pipeline.HAS_ARCH}, HAS_HMM={data_pipeline.HAS_HMM}")

# Test HMM fallback (force HAS_HMM = False)
orig_has_hmm = data_pipeline.HAS_HMM
data_pipeline.HAS_HMM = False
df_gmm_fallback = data_pipeline.fit_and_assign_market_regimes(df.copy())
print("GMM fallback successful! regime_label unique:", df_gmm_fallback['regime_label'].unique())
data_pipeline.HAS_HMM = orig_has_hmm

# Check 8: Data Leakage Test (Regime fitting with future lookahead vs causal window)
print("\n--- Step 4: Data Leakage & Integrity Check ---")
# Fit on full dataset vs fit on first half
half_len = len(df) // 2
df_half = df.iloc[:half_len].copy()
df_half_fitted = data_pipeline.fit_and_assign_market_regimes(df_half)

full_posteriors_half = df.iloc[:half_len][['regime_state_0', 'regime_state_1', 'regime_state_2']].values
half_posteriors = df_half_fitted[['regime_state_0', 'regime_state_1', 'regime_state_2']].values

diff = np.abs(full_posteriors_half - half_posteriors).max()
print(f"Max difference in regime posteriors when truncated (Full vs Half): {diff:.6f}")
if diff > 0.01:
    print("WARNING: Severe temporal lookahead leakage detected in market regime state assignment!")

print("\n--- Verification Complete ---")
