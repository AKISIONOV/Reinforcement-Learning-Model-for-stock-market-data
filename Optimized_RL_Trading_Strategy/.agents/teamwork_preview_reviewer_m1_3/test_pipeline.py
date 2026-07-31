import sys
import os
sys.path.insert(0, r'f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy')
import pandas as pd
import numpy as np
import data_pipeline

csv_path = r'f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv'
df = pd.read_csv(csv_path)

print('=== TESTING DATA_PIPELINE FUNCTIONS ===')

# Check HAS_HMM and HAS_ARCH
print('HAS_ARCH:', data_pipeline.HAS_ARCH)
print('HAS_HMM:', data_pipeline.HAS_HMM)

# Test fit_and_assign_market_regimes
# Create sample combined df with 2 tickers of length 100 each
df_sample = pd.concat([
    pd.DataFrame({'tic': ['AAPL']*100, 'return': np.random.randn(100)*0.01, 'ewma_vol': np.abs(np.random.randn(100))*0.01}),
    pd.DataFrame({'tic': ['BA']*100, 'return': np.random.randn(100)*0.01, 'ewma_vol': np.abs(np.random.randn(100))*0.01})
], ignore_index=True)

res = data_pipeline.fit_and_assign_market_regimes(df_sample, lengths=[100, 100])
print('Sample regime columns added:', [c for c in res.columns if 'regime' in c])
print('Sample regime label counts:\n', res['regime_label'].value_counts())

# Check for hardcoded values or dummy logic in data_pipeline.py
print('\n=== CHECKING FOR HARDCODED OR DUMMY LOGIC IN DATA_PIPELINE.PY ===')
with open('data_pipeline.py', 'r') as f:
    code = f.read()

# Integrity checks
suspicious_patterns = [
    'pd.DataFrame(', # dynamic creation of dummy outputs?
    'return 10.0',
    'pass #',
    'mock',
    'fake',
    'dummy'
]
for pattern in suspicious_patterns:
    if pattern in code:
        print(f'Found pattern "{pattern}" in data_pipeline.py')

print('Code length:', len(code), 'lines:', len(code.splitlines()))
