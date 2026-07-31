import sys
import os
import pandas as pd
import numpy as np

# Ensure path is included
sys.path.insert(0, r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy")
import data_pipeline

print("Python executable:", sys.executable)
print("Testing HAS_ARCH:", data_pipeline.HAS_ARCH)
print("Testing HAS_HMM:", data_pipeline.HAS_HMM)

# 1. Run pipeline
SOURCE_DIR = r"f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading"
OUTPUT_FILE = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv"

data_pipeline.run_pipeline(SOURCE_DIR, OUTPUT_FILE)

df = pd.read_csv(OUTPUT_FILE)
print("\n--- Output CSV Summary ---")
print("Shape:", df.shape)
print("Columns:", list(df.columns))
print("Tickers:", df['tic'].nunique(), sorted(df['tic'].unique()))
print("Null count:", df.isna().sum().to_dict())
