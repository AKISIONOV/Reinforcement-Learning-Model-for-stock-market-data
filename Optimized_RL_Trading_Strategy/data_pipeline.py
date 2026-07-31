"""
Data Pipeline for Market Dynamics (Milestone 1)
-----------------------------------------------
Loads daily stock CSVs for 28 DJIA assets (excluding UTX and DOW),
engineers market dynamics features (volatility clustering, spoofing proxies,
news shocks, intraday market regimes), and exports processed dataset.
"""

import os
import glob
import numpy as np
import pandas as pd

# Optional package imports with fallback support
try:
    from arch import arch_model
    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False

try:
    from hmmlearn.hmm import GaussianHMM
    HAS_HMM = True
except ImportError:
    HAS_HMM = False

from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans

# 28 DJIA assets list
DJIA_28_TICKERS = [
    'AAPL', 'AXP', 'BA', 'CAT', 'CSCO', 'CVX', 'DIS', 'GS', 'HD', 'IBM',
    'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE', 'PFE',
    'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT', 'XOM'
]

EXCLUDED_TICKERS = ['UTX', 'DOW']


def fallback_garch11(returns, alpha=0.05, beta=0.90):
    """
    Robust fallback heuristic for GARCH(1,1) conditional volatility.
    sigma_t^2 = omega + alpha * r_{t-1}^2 + beta * sigma_{t-1}^2
    omega = (1 - alpha - beta) * var_sample
    """
    r = returns.values
    n = len(r)
    var_sample = np.var(r[1:]) if n > 1 else 1e-4
    omega = (1.0 - alpha - beta) * var_sample
    
    sigma2 = np.zeros(n)
    sigma2[0] = max(1e-6, var_sample)
    
    for t in range(1, n):
        sigma2[t] = omega + alpha * (r[t-1] ** 2) + beta * sigma2[t-1]
        
    return np.sqrt(np.maximum(1e-10, sigma2))


def compute_garch_volatility(returns):
    """Calculates GARCH(1,1) conditional volatility using arch package if present, or fallback."""
    clean_ret = returns.fillna(0.0)
    if HAS_ARCH:
        try:
            am = arch_model(clean_ret * 100.0, vol='Garch', p=1, q=1, dist='Normal', rescale=False)
            res = am.fit(disp='off', show_warning=False)
            cond_vol = res.conditional_volatility / 100.0
            return cond_vol.values
        except Exception:
            pass
    return fallback_garch11(clean_ret)


def compute_corwin_schultz_spread(high, low):
    """
    Computes Corwin-Schultz High-Low Bid-Ask Spread Proxy.
    """
    high_vals = high.values
    low_vals = low.values
    n = len(high_vals)
    spread = np.zeros(n)
    
    k2 = 3.0 - 2.0 * np.sqrt(2.0) # ~0.171572875
    
    for t in range(1, n):
        h_prev, l_prev = high_vals[t-1], low_vals[t-1]
        h_curr, l_curr = high_vals[t], low_vals[t]
        
        h2 = max(h_prev, h_curr)
        l2 = min(l_prev, l_curr)
        
        if l_prev <= 0 or l_curr <= 0 or l2 <= 0:
            continue
            
        gamma = (np.log(h2 / l2)) ** 2
        beta = (np.log(h_prev / l_prev)) ** 2 + (np.log(h_curr / l_curr)) ** 2
        
        alpha = (np.sqrt(2.0 * beta) - np.sqrt(beta)) / k2 - np.sqrt(gamma / k2)
        
        if np.isnan(alpha) or alpha < 0:
            s = 0.0
        else:
            s = 2.0 * (np.exp(alpha) - 1.0) / (1.0 + np.exp(alpha))
            s = max(0.0, s)
            
        spread[t] = s
        
    return spread


def engineer_asset_features(df):
    """
    Engineers volatility clustering, spoofing proxies, and news shocks for a single asset dataframe.
    """
    df = df.copy()
    
    # 1. Basic returns
    df['return'] = df['adj_close'].pct_change()
    df['log_return'] = np.log(df['adj_close'] / df['adj_close'].shift(1))
    
    # Fill return initial row with 0 for rolling calculations before trimming
    clean_ret = df['return'].fillna(0.0)
    
    # 2. Volatility Clustering
    # EWMA Volatility (lambda = 0.94 => alpha = 1 - 0.94 = 0.06)
    ret_sq = clean_ret ** 2
    ewma_var = ret_sq.ewm(alpha=0.06, adjust=False).mean()
    df['ewma_vol'] = np.sqrt(np.maximum(0.0, ewma_var))
    
    # Rolling Volatility Ratio (5d / 21d)
    vol_5d = df['return'].rolling(window=5).std(ddof=1)
    vol_21d = df['return'].rolling(window=21).std(ddof=1)
    df['volatility_ratio_5_21'] = vol_5d / (vol_21d + 1e-8)
    
    # Garman-Klass Volatility
    high = np.maximum(df['high'], 1e-8)
    low = np.maximum(df['low'], 1e-8)
    open_p = np.maximum(df['open'], 1e-8)
    close_p = np.maximum(df['close'], 1e-8)
    h_l = np.log(high / low)
    c_o = np.log(close_p / open_p)
    gk_var = 0.5 * (h_l ** 2) - (2.0 * np.log(2.0) - 1.0) * (c_o ** 2)
    df['garman_klass_vol'] = np.sqrt(np.maximum(0.0, gk_var))
    
    # GARCH(1,1) Conditional Volatility
    df['garch_vol'] = compute_garch_volatility(df['return'])
    
    # 3. Spoofing Proxies
    max_oc = np.maximum(df['open'], df['close'])
    min_oc = np.minimum(df['open'], df['close'])
    hl_range = df['high'] - df['low'] + 1e-8
    
    df['shadow_upper'] = (df['high'] - max_oc) / hl_range
    df['shadow_lower'] = (min_oc - df['low']) / hl_range
    df['shadow_ratio'] = np.clip(df['shadow_upper'] / (df['shadow_lower'] + 1e-8), 0.0, 10.0)
    
    # VWAP distance = (Close - VWAP) / VWAP
    tp = (df['high'] + df['low'] + df['close']) / 3.0
    cum_vol_price = (tp * df['volume']).rolling(window=21).sum()
    cum_vol = df['volume'].rolling(window=21).sum()
    vwap_21 = np.where(cum_vol > 0, cum_vol_price / (cum_vol + 1e-8), df['close'])
    df['vwap'] = vwap_21
    df['vwap_distance'] = (df['close'] - vwap_21) / (vwap_21 + 1e-8)
    
    # Order Flow Imbalance Proxy = Sign(delta Close) * Volume
    delta_close = df['close'].diff()
    df['order_flow_imbalance'] = np.sign(delta_close.fillna(0.0)) * df['volume']
    
    # Bid-Ask spread proxy (Corwin-Schultz) smoothed with 5-day rolling EMA
    cs_raw = compute_corwin_schultz_spread(df['high'], df['low'])
    df['corwin_schultz_spread'] = pd.Series(cs_raw, index=df.index).ewm(span=5, adjust=False).mean()
    
    # 4. News Shocks
    mu_21 = df['return'].rolling(window=21).mean()
    sigma_21 = df['return'].rolling(window=21).std(ddof=1)
    df['return_shock_zscore'] = (df['return'] - mu_21) / (sigma_21 + 1e-8)
    df['return_jump_indicator'] = (df['return_shock_zscore'].abs() > 3.0).astype(int)
    
    sma_v_21 = df['volume'].rolling(window=21).mean()
    df['volume_spike_index'] = df['volume'] / (sma_v_21 + 1e-8)
    df['joint_vol_vol_shock'] = df['return_shock_zscore'] * df['volume_spike_index']
    
    # Handle initial 21-day window NaNs by dropping initial rolling window rows
    df_clean = df.dropna().reset_index(drop=True)
    return df_clean


def fit_and_assign_market_regimes(combined_df, lengths=None):
    """
    Fits 3-State Gaussian HMM (or GMM/KMeans fallback) on return & vol features across assets.
    Passes sequence lengths to GaussianHMM.fit(X_scaled, lengths=lengths) to prevent cross-asset
    boundary state transition contamination.
    Returns posterior probabilities for State 0 (Bullish Low-Vol), State 1 (Neutral), State 2 (Bearish High-Vol).
    """
    if lengths is None and 'tic' in combined_df.columns:
        lengths = [len(df_tic) for _, df_tic in combined_df.groupby('tic', sort=False)]

    features = combined_df[['return', 'ewma_vol']].values
    
    # Z-score scaling for regime model fitting
    mean_f = np.mean(features, axis=0)
    std_f = np.std(features, axis=0) + 1e-8
    X_scaled = (features - mean_f) / std_f
    
    posteriors = None
    means_scaled = None
    
    # Attempt 1: GaussianHMM
    if HAS_HMM:
        try:
            hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=200, random_state=42)
            if lengths is not None:
                hmm.fit(X_scaled, lengths=lengths)
                posteriors = hmm.predict_proba(X_scaled, lengths=lengths)
            else:
                hmm.fit(X_scaled)
                posteriors = hmm.predict_proba(X_scaled)
            means_scaled = hmm.means_
        except Exception as e:
            print(f"GaussianHMM fit failed ({e}), falling back...")
            posteriors = None
            
    # Attempt 2: GaussianMixture
    if posteriors is None:
        try:
            gmm = GaussianMixture(n_components=3, random_state=42)
            gmm.fit(X_scaled)
            posteriors = gmm.predict_proba(X_scaled)
            means_scaled = gmm.means_
        except Exception:
            pass

    # Attempt 3: KMeans fallback
    if posteriors is None:
        kmeans = KMeans(n_components=3, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        dists = kmeans.transform(X_scaled)
        exp_dists = np.exp(-dists)
        posteriors = exp_dists / np.sum(exp_dists, axis=1, keepdims=True)
        means_scaled = kmeans.cluster_centers_

    # Map state components to consistent labels:
    # State 0: Bullish Low-Vol (High Return, Low Vol)
    # State 1: Neutral
    # State 2: Bearish High-Vol (Low Return, High Vol)
    unscaled_means = means_scaled * std_f + mean_f
    
    # Score for each component k: mean_return - 2.0 * mean_vol
    scores = [unscaled_means[k, 0] - 2.0 * unscaled_means[k, 1] for k in range(3)]
    sorted_indices = np.argsort(scores)[::-1] # descending order
    
    best_idx = sorted_indices[0]    # State 0: Bullish Low-Vol
    neutral_idx = sorted_indices[1] # State 1: Neutral
    worst_idx = sorted_indices[2]   # State 2: Bearish High-Vol
    
    combined_df['regime_state_0'] = posteriors[:, best_idx]
    combined_df['regime_state_1'] = posteriors[:, neutral_idx]
    combined_df['regime_state_2'] = posteriors[:, worst_idx]
    
    ordered_posteriors = posteriors[:, [best_idx, neutral_idx, worst_idx]]
    combined_df['regime_label'] = np.argmax(ordered_posteriors, axis=1)
    
    return combined_df


def run_pipeline(source_dir, output_file):
    print(f"Loading stock data from: {source_dir}")
    
    processed_dfs = []
    included_count = 0
    
    for symbol in DJIA_28_TICKERS:
        file_path = os.path.join(source_dir, f"{symbol}.csv")
        if not os.path.exists(file_path):
            print(f"Warning: File for ticker {symbol} not found at {file_path}")
            continue
            
        df = pd.read_csv(file_path)
        # Standardize column names
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        df['tic'] = symbol
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Engineer features
        df_feat = engineer_asset_features(df)
        processed_dfs.append(df_feat)
        included_count += 1
        print(f"Processed {symbol}: {len(df_feat)} rows")
        
    print(f"Successfully processed {included_count} assets.")
    
    # Combine all assets
    combined = pd.concat(processed_dfs, ignore_index=True)
    
    # Fit and assign market regimes
    print("Fitting market regimes (3-State model)...")
    lengths = [len(df_tic) for df_tic in processed_dfs]
    combined = fit_and_assign_market_regimes(combined, lengths=lengths)
    
    # Format date and sort by date, tic
    combined['date'] = combined['date'].dt.strftime('%Y-%m-%d')
    combined = combined.sort_values(['date', 'tic']).reset_index(drop=True)
    
    # Check for NaNs
    nan_count = combined.isna().sum().sum()
    print(f"Combined dataset shape: {combined.shape}")
    print(f"Total NaNs in dataset: {nan_count}")
    
    if nan_count > 0:
        print("Cleaning remaining NaNs...")
        non_tic_cols = [c for c in combined.columns if c != 'tic']
        combined[non_tic_cols] = combined.groupby('tic')[non_tic_cols].ffill().groupby(combined['tic'])[non_tic_cols].bfill()
        combined = combined.fillna(0.0)
        
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    combined.to_csv(output_file, index=False)
    print(f"Exported processed market dynamics dataset to: {output_file}")
    
    # Self-verification summary
    tickers_present = combined['tic'].nunique()
    date_count = combined['date'].nunique()
    print("--- Verification Summary ---")
    print(f"Tickers present: {tickers_present} (Expected: 28)")
    print(f"Unique dates: {date_count} (Expected: ~2836)")
    print(f"Total rows: {len(combined)}")
    print(f"Columns: {list(combined.columns)}")
    print("----------------------------")


if __name__ == '__main__':
    SOURCE_DIRECTORY = r"f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading"
    OUTPUT_FILE = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv"
    run_pipeline(SOURCE_DIRECTORY, OUTPUT_FILE)
