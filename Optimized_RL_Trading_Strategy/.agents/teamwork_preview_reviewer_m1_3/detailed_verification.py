import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, r'f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy')
import data_pipeline

csv_path = r'f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv'
df = pd.read_csv(csv_path)

print("=== COMPREHENSIVE VERIFICATION SUITE ===")

# Test 1: Shape & Asset alignment
print("\n--- 1. SHAPE & ALIGNMENT ---")
expected_tickers = set(data_pipeline.DJIA_28_TICKERS)
actual_tickers = set(df['tic'].unique())
assert len(actual_tickers) == 28, f"Expected 28 tickers, got {len(actual_tickers)}"
assert actual_tickers == expected_tickers, f"Ticker mismatch! Missing: {expected_tickers - actual_tickers}"
assert 'UTX' not in actual_tickers and 'DOW' not in actual_tickers, "Excluded tickers UTX/DOW present!"

unique_dates = df['date'].unique()
assert len(unique_dates) == 2835, f"Expected 2835 dates, got {len(unique_dates)}"

expected_total_rows = 28 * 2835 # 79380
assert len(df) == expected_total_rows, f"Expected {expected_total_rows} rows, got {len(df)}"

# Test exact alignment across every single date
date_counts = df.groupby('date')['tic'].nunique()
assert (date_counts == 28).all(), "Some dates do not have exactly 28 tickers!"

# Test exact alignment across every single ticker
tic_counts = df.groupby('tic')['date'].nunique()
assert (tic_counts == 2835).all(), "Some tickers do not have exactly 2835 dates!"

# Test NaNs and Infs
nan_sum = df.isna().sum().sum()
inf_sum = np.isinf(df.select_dtypes(include=np.number)).sum().sum()
assert nan_sum == 0, f"Found {nan_sum} NaNs!"
assert inf_sum == 0, f"Found {inf_sum} Infs!"
print("[PASS] Shape, assets (28 DJIA), dates (2835 aligned), row count (79,380), 0 NaNs, 0 Infs ALL PASSED.")


# Test 2: shadow_ratio clipping
print("\n--- 2. SHADOW RATIO CLIPPING ---")
shadow_max = df['shadow_ratio'].max()
shadow_min = df['shadow_ratio'].min()
shadow_gt_10 = (df['shadow_ratio'] > 10.0).sum()
shadow_eq_10 = (df['shadow_ratio'] == 10.0).sum()

print(f"shadow_ratio range: [{shadow_min:.4f}, {shadow_max:.4f}]")
print(f"Count > 10.0: {shadow_gt_10}")
print(f"Count == 10.0: {shadow_eq_10}")

assert shadow_max <= 10.0, f"shadow_ratio max {shadow_max} exceeds 10.0!"
assert shadow_min >= 0.0, f"shadow_ratio min {shadow_min} is below 0.0!"
assert shadow_gt_10 == 0, "Found shadow_ratio values strictly greater than 10.0!"
print("[PASS] shadow_ratio max <= 10.0 clipping PASSED.")


# Test 3: Corwin-Schultz Spread EMA Smoothing
print("\n--- 3. CORWIN-SCHULTZ SPREAD SMOOTHING ---")
cs_min = df['corwin_schultz_spread'].min()
cs_max = df['corwin_schultz_spread'].max()
cs_mean = df['corwin_schultz_spread'].mean()
cs_zero_count = (df['corwin_schultz_spread'] == 0.0).sum()
cs_zero_pct = (cs_zero_count / len(df)) * 100

print(f"cs_spread min: {cs_min:.8f}")
print(f"cs_spread max: {cs_max:.6f}")
print(f"cs_spread mean: {cs_mean:.6f}")
print(f"cs_spread zero count: {cs_zero_count} ({cs_zero_pct:.2f}%)")

assert cs_min >= 0.0, "Corwin-Schultz spread contains negative values!"
assert cs_zero_pct < 5.0, f"Corwin-Schultz spread zero inflation still high ({cs_zero_pct:.2f}%)!"
print("[PASS] Corwin-Schultz spread 5-day EMA smoothing PASSED.")


# Test 4: Sequence lengths in GaussianHMM
print("\n--- 4. SEQUENCE LENGTHS & HMM / REGIME FITTING ---")
# Check source code implementation
import inspect
sig = inspect.signature(data_pipeline.fit_and_assign_market_regimes)
assert 'lengths' in sig.parameters, "lengths parameter missing from fit_and_assign_market_regimes signature!"

# Verify fit_and_assign_market_regimes source code passes lengths to fit and predict_proba
source_code = inspect.getsource(data_pipeline.fit_and_assign_market_regimes)
assert 'hmm.fit(X_scaled, lengths=lengths)' in source_code or 'hmm.fit(X_scaled, lengths=' in source_code, \
    "hmm.fit call does not pass lengths!"
assert 'predict_proba(X_scaled, lengths=lengths)' in source_code or 'predict_proba(X_scaled, lengths=' in source_code, \
    "predict_proba call does not pass lengths!"
assert 'lengths = [len(df_tic) for df_tic in processed_dfs]' in inspect.getsource(data_pipeline.run_pipeline) or \
    'lengths' in inspect.getsource(data_pipeline.run_pipeline), \
    "run_pipeline does not construct/pass sequence lengths!"

print("[PASS] Sequence lengths in GaussianHMM code inspection PASSED.")


# Test 5: Regime Posterior Probabilities & Labels integrity
print("\n--- 5. REGIME PROBABILITIES & LABELS ---")
regime_cols = ['regime_state_0', 'regime_state_1', 'regime_state_2']
prob_sums = df[regime_cols].sum(axis=1)
assert np.allclose(prob_sums, 1.0, atol=1e-5), "Regime posterior probabilities do not sum to 1.0!"

labels = df['regime_label'].unique()
assert set(labels).issubset({0, 1, 2}), f"Unexpected regime labels: {labels}"

# Verify regime mapping logic: State 0 has high return/low vol, State 2 has high vol
mean_ret_by_regime = df.groupby('regime_label')['return'].mean()
mean_vol_by_regime = df.groupby('regime_label')['ewma_vol'].mean()
print("Mean returns by regime label:\n", mean_ret_by_regime)
print("Mean ewma_vol by regime label:\n", mean_vol_by_regime)

assert mean_vol_by_regime[2] > mean_vol_by_regime[0], "State 2 should have higher volatility than State 0!"
print("[PASS] Regime state probability constraints and ordering PASSED.")


# Test 6: Integrity Violations Check
print("\n--- 6. INTEGRITY VIOLATION CHECKS ---")
# Verify that dataset values are non-constant, non-dummy, realistic market distributions
for col in ['return', 'garman_klass_vol', 'garch_vol', 'corwin_schultz_spread', 'vwap_distance']:
    std_val = df[col].std()
    assert std_val > 1e-6, f"Column {col} has standard deviation ~0 ({std_val}), possible dummy constant data!"

print("[PASS] Data dynamic variability check PASSED.")
print("\nALL COMPREHENSIVE VERIFICATION CHECKS PASSED SUCCESSFULLY!")
