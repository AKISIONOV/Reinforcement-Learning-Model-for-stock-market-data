"""
RL Paper Trading Execution Engine (trade_executor.py)
------------------------------------------------------
Executes RL PPO trading strategy on 28 DJIA assets with:
- yfinance live data fetching & historical CSV fallback.
- Complete 17 technical indicators + 3-state HMM market regime probabilities.
- Exact 567-dimensional observation state vector assembly.
- SB3 PPO model loading and inference.
- Dual-Mode Execution (Alpaca Paper Trading API vs Mock Execution Mode with 10 bps fee model).
- CSV trade and daily portfolio snapshot logging to logs/paper_trade_log.csv.
"""

import os
import sys
import io
import time
import datetime
import warnings

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

warnings.filterwarnings('ignore')

# Optional Supabase import for Cloud Database logging
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

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
from stable_baselines3 import PPO

# Load environment variables from .env
load_dotenv()

# Canonical 28 DJIA Tickers (alphabetically sorted)
DJIA_28_TICKERS = [
    'AAPL', 'AXP', 'BA', 'CAT', 'CSCO', 'CVX', 'DIS', 'GS', 'HD', 'IBM',
    'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK', 'MSFT', 'NKE', 'PFE',
    'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT', 'XOM'
]

# 17 Default Technical Indicators
DEFAULT_TECH_INDICATORS = [
    'return', 'log_return', 'ewma_vol', 'volatility_ratio_5_21',
    'garman_klass_vol', 'garch_vol', 'shadow_upper', 'shadow_lower',
    'shadow_ratio', 'vwap', 'vwap_distance', 'order_flow_imbalance',
    'corwin_schultz_spread', 'return_shock_zscore', 'return_jump_indicator',
    'volume_spike_index', 'joint_vol_vol_shock'
]

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STRATEGY_DIR = os.path.join(os.path.dirname(BASE_DIR), "Optimized_RL_Trading_Strategy")
if not os.path.exists(STRATEGY_DIR):
    STRATEGY_DIR = BASE_DIR

MODEL_PATH = os.path.join(STRATEGY_DIR, "optimal_trading_model.zip")
if not os.path.exists(MODEL_PATH):
    MODEL_PATH = os.path.join(BASE_DIR, "optimal_trading_model.zip")

HISTORICAL_DATA_PATH = os.path.join(STRATEGY_DIR, "data", "processed_market_dynamics.csv")
if not os.path.exists(HISTORICAL_DATA_PATH):
    HISTORICAL_DATA_PATH = os.path.join(BASE_DIR, "data", "processed_market_dynamics.csv")

LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE_PATH = os.path.join(LOG_DIR, "paper_trade_log.csv")


# =====================================================================
# 1. Market Data Ingestion & Fallback
# =====================================================================

def fetch_aligned_market_data(period: str = "60d", interval: str = "1d") -> pd.DataFrame:
    """
    Fetches recent OHLCV data for 28 DJIA tickers using yfinance with robust fallback
    to historical CSV if network download fails or tickers are missing/delisted.
    Returns date-ticker aligned DataFrame.
    """
    tickers = sorted(DJIA_28_TICKERS)
    df_long = None

    try:
        import yfinance as yf
        print(f"[INFO] Fetching live market data for {len(tickers)} DJIA tickers via yfinance...")
        df_raw = yf.download(
            tickers=tickers,
            period=period,
            interval=interval,
            group_by="column",
            auto_adjust=False,
            threads=True,
            progress=False
        )

        if df_raw is not None and not df_raw.empty and len(df_raw) >= 5:
            if isinstance(df_raw.columns, pd.MultiIndex):
                df_long = df_raw.stack(level=1, future_stack=True).reset_index()
            else:
                df_long = df_raw.reset_index()

            rename_dict = {}
            for col in df_long.columns:
                c_str = str(col).lower().strip()
                if c_str in ['date', 'datetime']:
                    rename_dict[col] = 'date'
                elif c_str in ['ticker', 'tic', 'symbol']:
                    rename_dict[col] = 'tic'
                elif c_str in ['adj close', 'adj_close']:
                    rename_dict[col] = 'adj_close'
                elif c_str in ['close', 'high', 'low', 'open', 'volume']:
                    rename_dict[col] = c_str

            df_long = df_long.rename(columns=rename_dict)
            df_long['date'] = pd.to_datetime(df_long['date']).dt.strftime('%Y-%m-%d')
            print(f"[INFO] Successfully fetched yfinance data ({len(df_long)} records).")
        else:
            raise ValueError("yfinance output is empty or insufficient.")

    except Exception as e:
        print(f"[WARNING] yfinance data fetch failed/incomplete ({e}). Utilizing historical CSV fallback.")
        df_long = None

    if df_long is None or df_long.empty:
        if not os.path.exists(HISTORICAL_DATA_PATH):
            raise FileNotFoundError(f"Historical dataset not found at {HISTORICAL_DATA_PATH}")
        hist_df = pd.read_csv(HISTORICAL_DATA_PATH)
        hist_df['date'] = pd.to_datetime(hist_df['date']).dt.strftime('%Y-%m-%d')
        recent_dates = sorted(hist_df['date'].unique())[-60:]
        df_long = hist_df[hist_df['date'].isin(recent_dates)][
            ['date', 'tic', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
        ].copy()
        print(f"[INFO] Loaded historical CSV fallback ({len(df_long)} records across {len(recent_dates)} dates).")

    # Re-align on complete Cartesian product (dates x 28 tickers)
    unique_dates = sorted(df_long['date'].unique())
    grid = pd.MultiIndex.from_product([unique_dates, tickers], names=['date', 'tic']).to_frame().reset_index(drop=True)
    aligned_df = pd.merge(grid, df_long, on=['date', 'tic'], how='left')

    numeric_cols = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
    for col in numeric_cols:
        if col not in aligned_df.columns:
            aligned_df[col] = np.nan

    aligned_df[numeric_cols] = aligned_df.groupby('tic')[numeric_cols].ffill()
    aligned_df[numeric_cols] = aligned_df.groupby('tic')[numeric_cols].bfill()

    # Impute any ticker completely missing from live feed (e.g., delisted ticker like WBA returning 404)
    if aligned_df[numeric_cols].isna().any().any():
        if os.path.exists(HISTORICAL_DATA_PATH):
            hist_df = pd.read_csv(HISTORICAL_DATA_PATH)
            hist_df['date'] = pd.to_datetime(hist_df['date']).dt.strftime('%Y-%m-%d')
            for tic in tickers:
                tic_mask = aligned_df['tic'] == tic
                if aligned_df.loc[tic_mask, 'adj_close'].isna().all():
                    tic_hist = hist_df[hist_df['tic'] == tic].sort_values('date').iloc[-1]
                    for col in numeric_cols:
                        val = tic_hist[col] if col in tic_hist else 100.0
                        aligned_df.loc[tic_mask, col] = val

    aligned_df[numeric_cols] = aligned_df[numeric_cols].fillna(100.0)
    aligned_df = aligned_df.sort_values(['date', 'tic']).reset_index(drop=True)
    return aligned_df


# =====================================================================
# 2. Technical Indicators & Market Regime Calculation
# =====================================================================

def fallback_garch11(returns: pd.Series, alpha: float = 0.05, beta: float = 0.90) -> np.ndarray:
    """Fallback heuristic for GARCH(1,1) conditional volatility."""
    r = returns.values
    n = len(r)
    var_sample = np.var(r[1:]) if n > 1 else 1e-4
    omega = (1.0 - alpha - beta) * var_sample
    sigma2 = np.zeros(n)
    sigma2[0] = max(1e-6, var_sample)
    for t in range(1, n):
        sigma2[t] = omega + alpha * (r[t-1] ** 2) + beta * sigma2[t-1]
    return np.sqrt(np.maximum(1e-10, sigma2))


def compute_garch_volatility(returns: pd.Series) -> np.ndarray:
    """Calculates GARCH(1,1) conditional volatility."""
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


def compute_corwin_schultz_spread(high: pd.Series, low: pd.Series) -> np.ndarray:
    """Computes Corwin-Schultz High-Low Bid-Ask Spread Proxy."""
    high_vals, low_vals = high.values, low.values
    n = len(high_vals)
    spread = np.zeros(n)
    k2 = 3.0 - 2.0 * np.sqrt(2.0)

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


def engineer_asset_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineers all 17 technical indicators for a single asset dataframe."""
    df = df.copy()
    df['return'] = df['adj_close'].pct_change()
    df['log_return'] = np.log(df['adj_close'] / df['adj_close'].shift(1))
    clean_ret = df['return'].fillna(0.0)

    # 1. EWMA Volatility
    ret_sq = clean_ret ** 2
    ewma_var = ret_sq.ewm(alpha=0.06, adjust=False).mean()
    df['ewma_vol'] = np.sqrt(np.maximum(0.0, ewma_var))

    # 2. Volatility Ratio 5/21
    vol_5d = df['return'].rolling(window=5).std(ddof=1)
    vol_21d = df['return'].rolling(window=21).std(ddof=1)
    df['volatility_ratio_5_21'] = vol_5d / (vol_21d + 1e-8)

    # 3. Garman-Klass Volatility
    high = np.maximum(df['high'], 1e-8)
    low = np.maximum(df['low'], 1e-8)
    open_p = np.maximum(df['open'], 1e-8)
    close_p = np.maximum(df['close'], 1e-8)
    h_l = np.log(high / low)
    c_o = np.log(close_p / open_p)
    gk_var = 0.5 * (h_l ** 2) - (2.0 * np.log(2.0) - 1.0) * (c_o ** 2)
    df['garman_klass_vol'] = np.sqrt(np.maximum(0.0, gk_var))

    # 4. GARCH(1,1) Volatility
    df['garch_vol'] = compute_garch_volatility(df['return'])

    # 5. Candlestick Shadows & Ratio
    max_oc = np.maximum(df['open'], df['close'])
    min_oc = np.minimum(df['open'], df['close'])
    hl_range = df['high'] - df['low'] + 1e-8
    df['shadow_upper'] = (df['high'] - max_oc) / hl_range
    df['shadow_lower'] = (min_oc - df['low']) / hl_range
    df['shadow_ratio'] = np.clip(df['shadow_upper'] / (df['shadow_lower'] + 1e-8), 0.0, 10.0)

    # 6. VWAP & Distance
    tp = (df['high'] + df['low'] + df['close']) / 3.0
    cum_vol_price = (tp * df['volume']).rolling(window=21).sum()
    cum_vol = df['volume'].rolling(window=21).sum()
    vwap_21 = np.where(cum_vol > 0, cum_vol_price / (cum_vol + 1e-8), df['close'])
    df['vwap'] = vwap_21
    df['vwap_distance'] = (df['close'] - vwap_21) / (vwap_21 + 1e-8)

    # 7. Order Flow Imbalance
    delta_close = df['close'].diff()
    df['order_flow_imbalance'] = np.sign(delta_close.fillna(0.0)) * df['volume']

    # 8. Corwin-Schultz Spread
    cs_raw = compute_corwin_schultz_spread(df['high'], df['low'])
    df['corwin_schultz_spread'] = pd.Series(cs_raw, index=df.index).ewm(span=5, adjust=False).mean()

    # 9. Return Shock Z-Score & Jump Indicator
    mu_21 = df['return'].rolling(window=21).mean()
    sigma_21 = df['return'].rolling(window=21).std(ddof=1)
    df['return_shock_zscore'] = (df['return'] - mu_21) / (sigma_21 + 1e-8)
    df['return_jump_indicator'] = (df['return_shock_zscore'].abs() > 3.0).astype(int)

    # 10. Volume Spike Index & Joint Shock
    sma_v_21 = df['volume'].rolling(window=21).mean()
    df['volume_spike_index'] = df['volume'] / (sma_v_21 + 1e-8)
    df['joint_vol_vol_shock'] = df['return_shock_zscore'] * df['volume_spike_index']

    # Clean NaNs resulting from pct_change / rolling windows
    df = df.bfill().ffill().fillna(0.0)

    return df


def fit_and_assign_market_regimes(combined_df: pd.DataFrame) -> pd.DataFrame:
    """Fits 3-State HMM (or GMM/KMeans fallback) to extract market regime probabilities."""
    features = combined_df[['return', 'ewma_vol']].values
    features = np.nan_to_num(features, nan=0.0, posinf=1e6, neginf=-1e6)
    mean_f = np.mean(features, axis=0)
    std_f = np.std(features, axis=0) + 1e-8
    X_scaled = (features - mean_f) / std_f

    posteriors = None
    means_scaled = None

    if HAS_HMM:
        try:
            lengths = [len(df_tic) for _, df_tic in combined_df.groupby('tic', sort=False)]
            hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=200, random_state=42)
            hmm.fit(X_scaled, lengths=lengths)
            posteriors = hmm.predict_proba(X_scaled, lengths=lengths)
            means_scaled = hmm.means_
        except Exception:
            posteriors = None

    if posteriors is None:
        try:
            gmm = GaussianMixture(n_components=3, random_state=42)
            gmm.fit(X_scaled)
            posteriors = gmm.predict_proba(X_scaled)
            means_scaled = gmm.means_
        except Exception:
            pass

    if posteriors is None:
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        dists = kmeans.transform(X_scaled)
        exp_dists = np.exp(-dists)
        posteriors = exp_dists / np.sum(exp_dists, axis=1, keepdims=True)
        means_scaled = kmeans.cluster_centers_

    unscaled_means = means_scaled * std_f + mean_f
    scores = [unscaled_means[k, 0] - 2.0 * unscaled_means[k, 1] for k in range(3)]
    sorted_indices = np.argsort(scores)[::-1]

    best_idx = sorted_indices[0]    # State 0: Bullish Low-Vol
    neutral_idx = sorted_indices[1] # State 1: Neutral
    worst_idx = sorted_indices[2]   # State 2: Bearish High-Vol

    combined_df['regime_state_0'] = posteriors[:, best_idx]
    combined_df['regime_state_1'] = posteriors[:, neutral_idx]
    combined_df['regime_state_2'] = posteriors[:, worst_idx]

    ordered_posteriors = posteriors[:, [best_idx, neutral_idx, worst_idx]]
    combined_df['regime_label'] = np.argmax(ordered_posteriors, axis=1)

    return combined_df


def prepare_market_dataset() -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Loads, engineers features, and formats matrices for observation construction."""
    raw_df = fetch_aligned_market_data()
    processed_dfs = []

    for tic, df_tic in raw_df.groupby('tic', sort=False):
        df_tic = df_tic.sort_values('date').reset_index(drop=True)
        df_feat = engineer_asset_features(df_tic)
        processed_dfs.append(df_feat)

    combined_df = pd.concat(processed_dfs, ignore_index=True)
    combined_df = fit_and_assign_market_regimes(combined_df)

    combined_df['date'] = combined_df['date'].astype(str)
    combined_df = combined_df.sort_values(['date', 'tic']).reset_index(drop=True)

    tickers = sorted(combined_df['tic'].unique())
    dates = sorted(combined_df['date'].unique())

    # Build 3D arrays
    price_pivot = combined_df.pivot(index='date', columns='tic', values='adj_close').ffill().bfill().fillna(100.0)
    price_array = price_pivot.values.astype(np.float32)

    tech_list = []
    for feat in DEFAULT_TECH_INDICATORS:
        p = combined_df.pivot(index='date', columns='tic', values=feat).ffill().bfill().fillna(0.0)
        tech_list.append(p.values)
    tech_stacked = np.stack(tech_list, axis=0)
    tech_array = np.transpose(tech_stacked, (1, 2, 0)).astype(np.float32)

    regime_cols = ['regime_state_0', 'regime_state_1', 'regime_state_2']
    regime_df = combined_df.groupby('date')[regime_cols].first().reindex(dates).ffill().bfill().fillna(1.0 / 3.0)
    regime_array = regime_df.values.astype(np.float32)

    return combined_df, price_array, tech_array, regime_array, dates


# =====================================================================
# 3. Exact 567-Dimensional Observation Vector Construction
# =====================================================================

def construct_observation_vector(
    cash: float,
    shares: np.ndarray,
    initial_amount: float,
    price_row: np.ndarray,
    tech_matrix_row: np.ndarray,
    regime_row: np.ndarray,
    drawdown: float,
    peak_net_worth: float,
    returns_memory: list[float],
    prev_actions: np.ndarray
) -> np.ndarray:
    """
    Assembles the exact 567-dimensional observation vector:
    1. Cash Norm [0:1] (1)
    2. Shares Scaled [1:29] (28)
    3. Current Prices [29:57] (28)
    4. Technical Features [57:533] (476 = 28 * 17)
    5. Market Regime Probs [533:536] (3)
    6. Risk State [536:539] (3)
    7. Prev Actions [539:567] (28)
    """
    cash_norm = np.array([cash / initial_amount], dtype=np.float32)
    shares_scaled = (shares * 1e-4).astype(np.float32)
    current_prices = price_row.astype(np.float32)
    tech_feats = tech_matrix_row.flatten().astype(np.float32)
    regime_probs = regime_row.astype(np.float32)

    if len(returns_memory) > 0:
        recent_ret = np.array(returns_memory, dtype=np.float32)
        neg_ret = np.minimum(0.0, recent_ret)
        downside_vol = float(np.sqrt(np.mean(neg_ret ** 2)))
    else:
        downside_vol = 0.0

    risk_state = np.array(
        [drawdown, peak_net_worth / initial_amount, downside_vol],
        dtype=np.float32
    )

    obs = np.hstack([
        cash_norm,
        shares_scaled,
        current_prices,
        tech_feats,
        regime_probs,
        risk_state,
        prev_actions.astype(np.float32)
    ], dtype=np.float32)

    obs = np.nan_to_num(obs, nan=0.0, posinf=1e6, neginf=-1e6).astype(np.float32)
    assert obs.shape == (567,), f"Observation vector shape mismatch! Expected (567,), got {obs.shape}"
    return obs


# =====================================================================
# 4. Alpaca API & Execution Engines
# =====================================================================

class AlpacaExecutionEngine:
    """Handles live Alpaca paper trading execution via REST API."""
    def __init__(self, key_id: str, secret_key: str, base_url: str):
        self.key_id = key_id
        self.secret_key = secret_key
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json"
        }

    def validate_connection(self) -> tuple[bool, str]:
        """Validates API credentials against /v2/account."""
        url = f"{self.base_url}/v2/account"
        try:
            res = requests.get(url, headers=self.headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                acc_status = data.get('status', 'UNKNOWN')
                cash = data.get('cash', '0')
                return True, f"Connected to Account ID: {data.get('id')}, Status: {acc_status}, Cash: ${float(cash):,.2f}"
            else:
                return False, f"HTTP {res.status_code}: {res.text}"
        except Exception as e:
            return False, str(e)

    def submit_order(self, ticker: str, qty: float, side: str) -> dict:
        """Submits paper trading order to Alpaca REST API."""
        url = f"{self.base_url}/v2/orders"
        payload = {
            "symbol": ticker,
            "qty": str(round(qty, 4)),
            "side": side.lower(),
            "type": "market",
            "time_in_force": "day"
        }
        res = requests.post(url, headers=self.headers, json=payload, timeout=5)
        return res.json()


# =====================================================================
# 5. Dual-Mode Execution & Strategy Runner
# =====================================================================

def run_paper_trading():
    """Main execution loop for model inference & portfolio execution."""
    print("=" * 70)
    print("      RL PAPER TRADING DEPLOYMENT EXECUTION ENGINE")
    print("=" * 70)

    # 1. Load PPO Model
    print(f"[INFO] Loading RL PPO model from: {MODEL_PATH}")
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"PPO Model file not found at {MODEL_PATH}")
    model = PPO.load(MODEL_PATH, device="cpu")
    print(f"[INFO] SB3 Model loaded successfully. Action Dim: {model.action_space.shape[0]}, Obs Dim: {model.observation_space.shape[0]}")

    # 2. Check Alpaca Credentials & Execution Mode
    apca_key = os.getenv("APCA_API_KEY_ID", "").strip()
    apca_secret = os.getenv("APCA_API_SECRET_KEY", "").strip()
    apca_base_url = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets").strip()
    trading_mode_cfg = os.getenv("TRADING_MODE", "paper").strip().lower()

    execution_mode = "MOCK"
    alpaca_client = None

    if apca_key and apca_secret and not apca_key.startswith("YOUR_") and trading_mode_cfg == "paper":
        alpaca_client = AlpacaExecutionEngine(apca_key, apca_secret, apca_base_url)
        is_valid, msg = alpaca_client.validate_connection()
        if is_valid:
            execution_mode = "ALPACA_PAPER"
            print(f"[SUCCESS] Alpaca API Authenticated! {msg}")
            print("[INFO] Active Mode: ALPACA PAPER TRADING MODE")
        else:
            print(f"[WARNING] Alpaca API Connection Failed: {msg}")
            print("[WARNING] Automatically entering MOCK EXECUTION MODE.")
    else:
        print("[WARNING] Alpaca API credentials missing or placeholder values in environment/.env.")
        print("[WARNING] Automatically entering MOCK EXECUTION MODE.")

    # 2b. Check Supabase Credentials for Cloud Logging
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()
    supabase_client = None

    if HAS_SUPABASE and supabase_url and supabase_key and not supabase_url.startswith("YOUR_"):
        try:
            supabase_client = create_client(supabase_url, supabase_key)
            print("[SUCCESS] Authenticated with Supabase Cloud Database!")
        except Exception as e:
            print(f"[WARNING] Failed to initialize Supabase client: {e}")

    # 3. Load & Prepare Market Data
    print("[INFO] Preparing market dataset, technical indicators, and HMM market regimes...")
    combined_df, price_array, tech_array, regime_array, dates = prepare_market_dataset()
    num_dates = len(dates)
    stock_dim = len(DJIA_28_TICKERS)
    print(f"[INFO] Prepared dataset across {num_dates} market dates ({dates[0]} to {dates[-1]}).")

    # 4. Initialize Portfolio State
    initial_amount = 1e6
    cash = initial_amount
    shares = np.zeros(stock_dim, dtype=np.float32)
    net_worth = initial_amount
    peak_net_worth = initial_amount
    drawdown = 0.0
    returns_memory = []
    prev_actions = np.zeros(stock_dim, dtype=np.float32)
    fee_pct = 0.001 # 10 bps fee model

    # Ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)
    log_headers = [
        "timestamp", "date", "ticker", "action_type", "raw_action",
        "target_weight", "shares", "price", "trade_value", "fee",
        "portfolio_cash", "portfolio_net_worth", "daily_return", "drawdown",
        "market_regime", "execution_mode"
    ]
    log_df = pd.DataFrame(columns=log_headers)
    log_df.to_csv(LOG_FILE_PATH, index=False)

    print(f"[INFO] Initialized Portfolio: Cash=${cash:,.2f}, Net Worth=${net_worth:,.2f}")
    print(f"[INFO] Logging paper trades to: {LOG_FILE_PATH}")
    print("-" * 70)

    # 5. Run Execution Loop across recent market dates
    # We execute over the last 10 trading days for verification
    start_step = max(0, num_dates - 10)
    trade_logs = []

    regime_names = {0: "Bullish Low-Vol", 1: "Neutral", 2: "Bearish High-Vol"}

    for step in range(start_step, num_dates):
        current_date = dates[step]
        price_row = price_array[step]
        tech_row = tech_array[step]
        regime_row = regime_array[step]
        active_regime_idx = int(np.argmax(regime_row))
        active_regime_name = regime_names.get(active_regime_idx, "Neutral")

        # Step A: Construct 567-dim state observation
        obs = construct_observation_vector(
            cash=cash,
            shares=shares,
            initial_amount=initial_amount,
            price_row=price_row,
            tech_matrix_row=tech_row,
            regime_row=regime_row,
            drawdown=drawdown,
            peak_net_worth=peak_net_worth,
            returns_memory=returns_memory,
            prev_actions=prev_actions
        )

        # Step B: PPO Model Inference
        action, _ = model.predict(obs, deterministic=True)
        action = np.clip(action, -1.0, 1.0).astype(np.float32)

        # Step C: Circuit breaker / Regime position limit constraints
        if len(returns_memory) > 0 and returns_memory[-1] < -0.05:
            action = -np.ones(stock_dim, dtype=np.float32) # Liquidate everything
        elif active_regime_idx == 2:
            action = np.clip(action, -0.5, 0.5)

        prev_actions = action.copy()

        # Target portfolio allocation weights
        pos_mask = action > 0
        pos_sum = float(np.sum(action[pos_mask]))
        target_weights = np.zeros(stock_dim, dtype=np.float32)
        if pos_sum > 0:
            target_weights[pos_mask] = action[pos_mask] / pos_sum

        # Step D: Trade Execution (Sells then Buys)
        timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        prev_net_worth = net_worth
        step_trades = 0

        # Sell Executions
        for i in range(stock_dim):
            ticker = DJIA_28_TICKERS[i]
            a_val = float(action[i])
            p_val = float(price_row[i])

            if a_val < 0 and shares[i] > 0:
                sell_ratio = min(1.0, abs(a_val))
                sell_shares = shares[i] * sell_ratio
                if sell_shares > 1e-6:
                    sell_val = sell_shares * p_val
                    fee = sell_val * fee_pct
                    cash += (sell_val - fee)
                    shares[i] -= sell_shares
                    step_trades += 1

                    if execution_mode == "ALPACA_PAPER" and alpaca_client:
                        try:
                            alpaca_client.submit_order(ticker, sell_shares, "sell")
                        except Exception as ex:
                            print(f"[ALPACA ERROR] Sell order failed for {ticker}: {ex}")

                    trade_logs.append({
                        "timestamp": timestamp_str,
                        "date": current_date,
                        "ticker": ticker,
                        "action_type": "SELL",
                        "raw_action": round(a_val, 4),
                        "target_weight": 0.0,
                        "shares": round(float(sell_shares), 4),
                        "price": round(p_val, 2),
                        "trade_value": round(sell_val, 2),
                        "fee": round(fee, 2),
                        "portfolio_cash": round(cash, 2),
                        "portfolio_net_worth": round(net_worth, 2),
                        "daily_return": round(float(returns_memory[-1]) if returns_memory else 0.0, 6),
                        "drawdown": round(drawdown, 6),
                        "market_regime": active_regime_name,
                        "execution_mode": execution_mode
                    })

        # Buy Executions
        if pos_sum > 0 and cash > 0:
            allocatable_cash = float(cash)
            for i in range(stock_dim):
                ticker = DJIA_28_TICKERS[i]
                a_val = float(action[i])
                p_val = float(price_row[i])

                if a_val > 0 and cash > 0:
                    w = float(a_val) / pos_sum
                    target_buy_cash = min(allocatable_cash * w, float(cash))
                    fee = target_buy_cash * (fee_pct / (1.0 + fee_pct))
                    buy_val = target_buy_cash - fee
                    buy_shares = buy_val / p_val

                    if buy_shares > 1e-6:
                        shares[i] += buy_shares
                        cash -= target_buy_cash
                        step_trades += 1

                        if execution_mode == "ALPACA_PAPER" and alpaca_client:
                            try:
                                alpaca_client.submit_order(ticker, buy_shares, "buy")
                            except Exception as ex:
                                print(f"[ALPACA ERROR] Buy order failed for {ticker}: {ex}")

                        trade_logs.append({
                            "timestamp": timestamp_str,
                            "date": current_date,
                            "ticker": ticker,
                            "action_type": "BUY",
                            "raw_action": round(a_val, 4),
                            "target_weight": round(float(target_weights[i]), 4),
                            "shares": round(float(buy_shares), 4),
                            "price": round(p_val, 2),
                            "trade_value": round(buy_val, 2),
                            "fee": round(fee, 2),
                            "portfolio_cash": round(cash, 2),
                            "portfolio_net_worth": round(net_worth, 2),
                            "daily_return": round(float(returns_memory[-1]) if returns_memory else 0.0, 6),
                            "drawdown": round(drawdown, 6),
                            "market_regime": active_regime_name,
                            "execution_mode": execution_mode
                        })

        cash = max(0.0, cash)

        # Step E: Update Portfolio Net Worth & Risk Metrics
        next_prices = price_array[min(step + 1, num_dates - 1)]
        net_worth = float(cash + np.sum(shares * next_prices))
        daily_ret = (net_worth - prev_net_worth) / (prev_net_worth + 1e-8)
        returns_memory.append(daily_ret)
        if len(returns_memory) > 21:
            returns_memory.pop(0)

        peak_net_worth = max(peak_net_worth, net_worth)
        drawdown = max(0.0, (peak_net_worth - net_worth) / (peak_net_worth + 1e-8))

        # Append Daily Snapshot Log
        trade_logs.append({
            "timestamp": timestamp_str,
            "date": current_date,
            "ticker": "PORTFOLIO_SUMMARY",
            "action_type": "SNAPSHOT",
            "raw_action": 0.0,
            "target_weight": 0.0,
            "shares": 0.0,
            "price": 0.0,
            "trade_value": 0.0,
            "fee": 0.0,
            "portfolio_cash": round(cash, 2),
            "portfolio_net_worth": round(net_worth, 2),
            "daily_return": round(daily_ret, 6),
            "drawdown": round(drawdown, 6),
            "market_regime": active_regime_name,
            "execution_mode": execution_mode
        })

        print(f"[{current_date}] Mode: {execution_mode} | Regime: {active_regime_name:<16} | Trades: {step_trades:2d} | Cash: ${cash:10,.2f} | Net Worth: ${net_worth:10,.2f} | Return: {daily_ret:+7.4%} | DD: {drawdown:.4%}")

    # Write logs to local CSV backup
    log_df = pd.DataFrame(trade_logs)
    log_df.to_csv(LOG_FILE_PATH, index=False)

    # Push logs to Supabase Cloud Database
    if supabase_client:
        try:
            print("[INFO] Pushing executed trades to Supabase Cloud...")
            clean_logs = log_df.replace({np.nan: None}).to_dict(orient="records")
            # Batch insert in chunks of 100
            for i in range(0, len(clean_logs), 100):
                supabase_client.table("trade_logs").insert(clean_logs[i:i+100]).execute()
            print(f"[SUCCESS] Pushed {len(clean_logs)} trade records to Supabase Cloud Database.")
        except Exception as e:
            print(f"[ERROR] Failed to push logs to Supabase: {e}")

    print("-" * 70)
    print(f"[SUCCESS] Execution completed over {len(range(start_step, num_dates))} steps.")
    print(f"[SUCCESS] Total trade & snapshot records logged: {len(log_df)}")
    print(f"[SUCCESS] Log file output: {LOG_FILE_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    run_paper_trading()
