import pandas as pd
import numpy as np
import sys

csv_path = r'f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv'
df = pd.read_csv(csv_path)

print('=== DATASET SHAPE & BASIC VERIFICATION ===')
print('Shape:', df.shape)
print('Total rows:', len(df))
print('Expected total rows (28 * 2835):', 28 * 2835)
print('Unique tickers:', df['tic'].nunique())
print('Tickers:', sorted(df['tic'].unique()))
print('Unique dates:', df['date'].nunique())
print('Min date:', df['date'].min(), 'Max date:', df['date'].max())
print('NaN count:', df.isna().sum().sum())
print('Inf count:', np.isinf(df.select_dtypes(include=np.number)).sum().sum())

# Date alignment check: each date should have exactly 28 tickers
date_counts = df.groupby('date')['tic'].nunique()
print('Dates with exactly 28 tickers:', (date_counts == 28).sum(), 'out of', len(date_counts))

# Ticker alignment check: each ticker should have exactly 2835 dates
tic_counts = df.groupby('tic')['date'].nunique()
print('Tickers with exactly 2835 dates:', (tic_counts == 2835).sum(), 'out of', len(tic_counts))

print('\n=== SHADOW RATIO VERIFICATION ===')
print('shadow_ratio min:', df['shadow_ratio'].min())
print('shadow_ratio max:', df['shadow_ratio'].max())
print('shadow_ratio > 10.0 count:', (df['shadow_ratio'] > 10.0).sum())
print('shadow_ratio == 10.0 (clipped) count:', (df['shadow_ratio'] == 10.0).sum())

print('\n=== CORWIN SCHULTZ SPREAD VERIFICATION ===')
print('corwin_schultz_spread min:', df['corwin_schultz_spread'].min())
print('corwin_schultz_spread max:', df['corwin_schultz_spread'].max())
print('corwin_schultz_spread mean:', df['corwin_schultz_spread'].mean())
zero_count = (df['corwin_schultz_spread'] == 0.0).sum()
zero_pct = zero_count / len(df) * 100
print(f'corwin_schultz_spread == 0 count: {zero_count} ({zero_pct:.2f}%)')
print('corwin_schultz_spread < 0 count:', (df['corwin_schultz_spread'] < 0.0).sum())

print('\n=== REGIME PROBABILITIES VERIFICATION ===')
for col in ['regime_state_0', 'regime_state_1', 'regime_state_2']:
    print(f'{col} - min: {df[col].min():.6f}, max: {df[col].max():.6f}, mean: {df[col].mean():.6f}')

prob_sum = df[['regime_state_0', 'regime_state_1', 'regime_state_2']].sum(axis=1)
print('Probabilities sum min:', prob_sum.min(), 'max:', prob_sum.max())
print('regime_label value counts:\n', df['regime_label'].value_counts())

print('\n=== COLUMNS LIST ===')
print(list(df.columns))
