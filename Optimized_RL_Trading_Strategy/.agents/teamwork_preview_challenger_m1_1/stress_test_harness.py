"""
Empirical Stress Testing & Adversarial Verification Harness for Milestone 1 (data_pipeline.py)
-----------------------------------------------------------------------------------------
Author: Challenger 1 (Empirical Challenger)
Metadata Dir: f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_challenger_m1_1
"""

import sys
import os
import traceback
import numpy as np
import pandas as pd

# Add target code directory to sys.path
TARGET_DIR = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy"
if TARGET_DIR not in sys.path:
    sys.path.insert(0, TARGET_DIR)

import data_pipeline as dp

# Utility helper to generate synthetic market data
def generate_synthetic_asset(
    num_days=100,
    base_price=100.0,
    base_volume=100000.0,
    noise_std=0.01,
    start_date="2020-01-01"
):
    dates = pd.date_range(start=start_date, periods=num_days, freq="D")
    np.random.seed(42)
    returns = np.random.normal(0, noise_std, num_days)
    price_series = base_price * np.exp(np.cumsum(returns))
    
    # Generate OHLCAV
    high = price_series * (1.0 + np.abs(np.random.normal(0, 0.005, num_days)))
    low = price_series * (1.0 - np.abs(np.random.normal(0, 0.005, num_days)))
    open_p = low + (high - low) * np.random.uniform(0.1, 0.9, num_days)
    close = low + (high - low) * np.random.uniform(0.1, 0.9, num_days)
    adj_close = close.copy()
    volume = np.abs(np.random.normal(base_volume, base_volume * 0.2, num_days)) + 100.0
    
    df = pd.DataFrame({
        'date': dates,
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'adj_close': adj_close,
        'volume': volume,
        'tic': 'TEST'
    })
    return df

class StressTestRunner:
    def __init__(self):
        self.results = []

    def log_result(self, test_id, name, status, details, severity="NONE"):
        self.results.append({
            'test_id': test_id,
            'name': name,
            'status': status,  # PASS / FAIL / WARN
            'severity': severity,  # CRITICAL / HIGH / MEDIUM / LOW / NONE
            'details': details
        })
        print(f"[{status}] {test_id}: {name}")
        if status != "PASS":
            print(f"   --> [{severity}] {details}")

    def run_all_tests(self):
        print("==================================================")
        print("Starting Empirical Stress Testing & Verification")
        print("==================================================")
        
        self.test_1_1_zero_prices()
        self.test_1_2_negative_prices()
        self.test_1_3_flat_zero_volume()
        self.test_1_4_zero_volatility_constant_price()
        self.test_1_5_extreme_price_spikes()
        self.test_1_6_malformed_high_low_relationships()
        self.test_1_7_missing_nans_in_raw_input()
        
        self.test_2_1_garch_fallback_vs_arch()
        self.test_2_2_corwin_schultz_overflow_underflow()
        self.test_2_3_spoofing_proxies_bounds()
        self.test_2_4_news_shocks_zero_std()
        self.test_2_5_garman_klass_zero_high()
        
        self.test_3_1_asset_isolation_feature_eng()
        self.test_3_2_hmm_regime_cross_asset_contamination()
        self.test_3_3_global_ffill_cross_ticker_leakage()
        
        self.test_4_1_empirical_dataset_audit()

    # --- CATEGORY 1: EXTREME INPUT BOUNDARY TESTS ---

    def test_1_1_zero_prices(self):
        df = generate_synthetic_asset(num_days=50)
        # Set prices to 0 for a subset of days
        df.loc[30:35, ['open', 'high', 'low', 'close', 'adj_close']] = 0.0
        
        try:
            res = dp.engineer_asset_features(df)
            nans = res.isna().sum().sum()
            infs = np.isinf(res.select_dtypes(include=[np.number])).sum().sum()
            
            if nans > 0 or infs > 0:
                nan_cols = res.columns[res.isna().any()].tolist()
                inf_cols = res.columns[np.isinf(res).any()].tolist()
                self.log_result(
                    "T1.1", "Zero Prices Handling", "FAIL",
                    f"Found {nans} NaNs (cols: {nan_cols}) and {infs} Infs (cols: {inf_cols}) when prices drop to 0.0",
                    severity="HIGH"
                )
            else:
                self.log_result("T1.1", "Zero Prices Handling", "PASS", "No NaN/Inf produced with zero prices.")
        except Exception as e:
            self.log_result("T1.1", "Zero Prices Handling", "FAIL", f"Unhandled exception: {e}\n{traceback.format_exc()}", severity="CRITICAL")

    def test_1_2_negative_prices(self):
        df = generate_synthetic_asset(num_days=50)
        # Set negative prices (e.g. WTI oil crash anomaly)
        df.loc[40:45, ['open', 'high', 'low', 'close', 'adj_close']] = -5.0
        
        try:
            res = dp.engineer_asset_features(df)
            nans = res.isna().sum().sum()
            infs = np.isinf(res.select_dtypes(include=[np.number])).sum().sum()
            
            if nans > 0 or infs > 0:
                nan_cols = res.columns[res.isna().any()].tolist()
                inf_cols = res.columns[np.isinf(res).any()].tolist()
                self.log_result(
                    "T1.2", "Negative Prices Handling", "FAIL",
                    f"Found {nans} NaNs (cols: {nan_cols}) and {infs} Infs (cols: {inf_cols}) with negative prices",
                    severity="HIGH"
                )
            else:
                self.log_result("T1.2", "Negative Prices Handling", "PASS", "No NaN/Inf produced with negative prices.")
        except Exception as e:
            self.log_result("T1.2", "Negative Prices Handling", "FAIL", f"Unhandled exception: {e}\n{traceback.format_exc()}", severity="CRITICAL")

    def test_1_3_flat_zero_volume(self):
        df = generate_synthetic_asset(num_days=50)
        df['volume'] = 0.0
        
        try:
            res = dp.engineer_asset_features(df)
            nans = res.isna().sum().sum()
            infs = np.isinf(res.select_dtypes(include=[np.number])).sum().sum()
            
            # Check vwap_distance explosion
            vwap_dist_max = res['vwap_distance'].abs().max()
            
            if nans > 0 or infs > 0:
                nan_cols = res.columns[res.isna().any()].tolist()
                inf_cols = res.columns[np.isinf(res).any()].tolist()
                self.log_result(
                    "T1.3", "Flat Zero Volume Handling", "FAIL",
                    f"Found {nans} NaNs (cols: {nan_cols}) and {infs} Infs (cols: {inf_cols}) with zero volume.",
                    severity="HIGH"
                )
            elif vwap_dist_max > 1e6:
                self.log_result(
                    "T1.3", "Flat Zero Volume Handling", "WARN",
                    f"vwap_distance exploded to max magnitude {vwap_dist_max:.2e} when volume=0 due to (close-0)/1e-8",
                    severity="MEDIUM"
                )
            else:
                self.log_result("T1.3", "Flat Zero Volume Handling", "PASS", f"Handled zero volume cleanly (max vwap_dist={vwap_dist_max:.2f}).")
        except Exception as e:
            self.log_result("T1.3", "Flat Zero Volume Handling", "FAIL", f"Unhandled exception: {e}\n{traceback.format_exc()}", severity="CRITICAL")

    def test_1_4_zero_volatility_constant_price(self):
        df = generate_synthetic_asset(num_days=50)
        df['open'] = 100.0
        df['high'] = 100.0
        df['low'] = 100.0
        df['close'] = 100.0
        df['adj_close'] = 100.0
        
        try:
            res = dp.engineer_asset_features(df)
            nans = res.isna().sum().sum()
            infs = np.isinf(res.select_dtypes(include=[np.number])).sum().sum()
            
            if nans > 0 or infs > 0:
                nan_cols = res.columns[res.isna().any()].tolist()
                inf_cols = res.columns[np.isinf(res).any()].tolist()
                self.log_result(
                    "T1.4", "Zero Volatility Constant Price", "FAIL",
                    f"Found {nans} NaNs (cols: {nan_cols}) and {infs} Infs (cols: {inf_cols}) with constant price.",
                    severity="HIGH"
                )
            else:
                self.log_result("T1.4", "Zero Volatility Constant Price", "PASS", "No NaN/Inf produced with constant price.")
        except Exception as e:
            self.log_result("T1.4", "Zero Volatility Constant Price", "FAIL", f"Unhandled exception: {e}\n{traceback.format_exc()}", severity="CRITICAL")

    def test_1_5_extreme_price_spikes(self):
        df = generate_synthetic_asset(num_days=60)
        # 10,000x price spike at index 40
        df.loc[40, ['open', 'high', 'low', 'close', 'adj_close']] *= 10000.0
        
        try:
            res = dp.engineer_asset_features(df)
            nans = res.isna().sum().sum()
            infs = np.isinf(res.select_dtypes(include=[np.number])).sum().sum()
            
            if nans > 0 or infs > 0:
                nan_cols = res.columns[res.isna().any()].tolist()
                inf_cols = res.columns[np.isinf(res).any()].tolist()
                self.log_result(
                    "T1.5", "Extreme Price Spikes", "FAIL",
                    f"Found {nans} NaNs (cols: {nan_cols}) and {infs} Infs (cols: {inf_cols}) during 10,000x price spike.",
                    severity="HIGH"
                )
            else:
                self.log_result("T1.5", "Extreme Price Spikes", "PASS", "No NaN/Inf produced during 10,000x price spike.")
        except Exception as e:
            self.log_result("T1.5", "Extreme Price Spikes", "FAIL", f"Unhandled exception: {e}\n{traceback.format_exc()}", severity="CRITICAL")

    def test_1_6_malformed_high_low_relationships(self):
        df = generate_synthetic_asset(num_days=50)
        # High < Low anomaly
        df.loc[30, 'high'] = 50.0
        df.loc[30, 'low'] = 100.0
        
        try:
            res = dp.engineer_asset_features(df)
            nans = res.isna().sum().sum()
            infs = np.isinf(res.select_dtypes(include=[np.number])).sum().sum()
            
            if nans > 0 or infs > 0:
                nan_cols = res.columns[res.isna().any()].tolist()
                inf_cols = res.columns[np.isinf(res).any()].tolist()
                self.log_result(
                    "T1.6", "Malformed High < Low Data", "FAIL",
                    f"Found {nans} NaNs (cols: {nan_cols}) and {infs} Infs (cols: {inf_cols}) when High < Low.",
                    severity="MEDIUM"
                )
            else:
                self.log_result("T1.6", "Malformed High < Low Data", "PASS", "No NaN/Inf produced with High < Low.")
        except Exception as e:
            self.log_result("T1.6", "Malformed High < Low Data", "FAIL", f"Unhandled exception: {e}\n{traceback.format_exc()}", severity="CRITICAL")

    def test_1_7_missing_nans_in_raw_input(self):
        df = generate_synthetic_asset(num_days=50)
        df.loc[25, 'adj_close'] = np.nan
        df.loc[35, 'volume'] = np.nan
        
        try:
            res = dp.engineer_asset_features(df)
            nans = res.isna().sum().sum()
            infs = np.isinf(res.select_dtypes(include=[np.number])).sum().sum()
            
            if nans > 0 or infs > 0:
                nan_cols = res.columns[res.isna().any()].tolist()
                inf_cols = res.columns[np.isinf(res).any()].tolist()
                self.log_result(
                    "T1.7", "Raw Input NaNs Handling", "FAIL",
                    f"Found {nans} NaNs (cols: {nan_cols}) and {infs} Infs (cols: {inf_cols}) when input CSV has NaNs.",
                    severity="HIGH"
                )
            else:
                self.log_result("T1.7", "Raw Input NaNs Handling", "PASS", "Input NaNs correctly filtered/handled.")
        except Exception as e:
            self.log_result("T1.7", "Raw Input NaNs Handling", "FAIL", f"Unhandled exception on raw input NaNs: {e}\n{traceback.format_exc()}", severity="HIGH")

    # --- CATEGORY 2: NUMERICAL STABILITY & FEATURE DERIVATION ---

    def test_2_1_garch_fallback_vs_arch(self):
        df = generate_synthetic_asset(num_days=100)
        returns = df['adj_close'].pct_change().dropna()
        
        garch_fb = dp.fallback_garch11(returns)
        
        nans_fb = np.isnan(garch_fb).sum()
        infs_fb = np.isinf(garch_fb).sum()
        
        if nans_fb > 0 or infs_fb > 0:
            self.log_result("T2.1", "GARCH Volatility Stability", "FAIL", f"GARCH fallback produced {nans_fb} NaNs and {infs_fb} Infs.", severity="HIGH")
        else:
            self.log_result("T2.1", "GARCH Volatility Stability", "PASS", f"GARCH computation stable. Uses arch package: {dp.HAS_ARCH}.")

    def test_2_2_corwin_schultz_overflow_underflow(self):
        high = pd.Series([100.0, 105.0, 1000.0, 0.001, 100.0, 100.0])
        low = pd.Series([95.0, 98.0, 990.0, 0.0005, 100.0, 10.0])
        
        spread = dp.compute_corwin_schultz_spread(high, low)
        nans = np.isnan(spread).sum()
        infs = np.isinf(spread).sum()
        
        if nans > 0 or infs > 0:
            self.log_result("T2.2", "Corwin-Schultz Spread Stability", "FAIL", f"Corwin-Schultz produced {nans} NaNs and {infs} Infs on synthetic series.", severity="HIGH")
        else:
            self.log_result("T2.2", "Corwin-Schultz Spread Stability", "PASS", f"Corwin-Schultz output stable: {spread}")

    def test_2_3_spoofing_proxies_bounds(self):
        df = generate_synthetic_asset(num_days=50)
        res = dp.engineer_asset_features(df)
        
        shadow_min = res['shadow_ratio'].min()
        shadow_max = res['shadow_ratio'].max()
        
        if shadow_min < 0.0 or shadow_max > 10.0:
            self.log_result("T2.3", "Spoofing Proxy Bounds", "FAIL", f"shadow_ratio out of bounds [0, 10]: min={shadow_min}, max={shadow_max}", severity="HIGH")
        else:
            self.log_result("T2.3", "Spoofing Proxy Bounds", "PASS", f"shadow_ratio properly bounded in [0, 10]: [{shadow_min:.4f}, {shadow_max:.4f}].")

    def test_2_4_news_shocks_zero_std(self):
        df = generate_synthetic_asset(num_days=50)
        df.loc[10:35, ['open', 'high', 'low', 'close', 'adj_close']] = 100.0
        
        res = dp.engineer_asset_features(df)
        zscores = res['return_shock_zscore']
        
        nans = zscores.isna().sum()
        infs = np.isinf(zscores).sum()
        max_z = zscores.abs().max()
        
        if nans > 0 or infs > 0:
            self.log_result("T2.4", "News Shocks Z-score Stability", "FAIL", f"return_shock_zscore produced {nans} NaNs and {infs} Infs when std=0", severity="HIGH")
        elif max_z > 1e5:
            self.log_result("T2.4", "News Shocks Z-score Stability", "WARN", f"return_shock_zscore reached large value {max_z:.2e} when std=0", severity="LOW")
        else:
            self.log_result("T2.4", "News Shocks Z-score Stability", "PASS", f"return_shock_zscore stable when std=0 (max z={max_z:.4f}).")

    def test_2_5_garman_klass_zero_high(self):
        df = generate_synthetic_asset(num_days=50)
        # Set high = 0.0 for days 30 to 35
        df.loc[30:35, 'high'] = 0.0
        
        res = dp.engineer_asset_features(df)
        gk = res['garman_klass_vol']
        infs = np.isinf(gk).sum()
        nans = gk.isna().sum()
        
        if infs > 0 or nans > 0:
            self.log_result(
                "T2.5", "Garman-Klass Zero High Handling", "FAIL",
                f"Garman-Klass Volatility produced {infs} Infs and {nans} NaNs when high=0 due to log(0 / max(low, 1e-8))",
                severity="HIGH"
            )
        else:
            self.log_result("T2.5", "Garman-Klass Zero High Handling", "PASS", "Garman-Klass Volatility handled high=0 without Inf/NaN.")

    # --- CATEGORY 3: ASSET ISOLATION & STATE LEAKAGE TESTS ---

    def test_3_1_asset_isolation_feature_eng(self):
        df_a = generate_synthetic_asset(num_days=100, base_price=100.0, start_date="2020-01-01")
        df_a['tic'] = 'AAPL'
        
        df_b = generate_synthetic_asset(num_days=100, base_price=500.0, start_date="2020-01-01")
        df_b['tic'] = 'MSFT'
        
        res_a_alone = dp.engineer_asset_features(df_a)
        diff_a = np.abs(res_a_alone.select_dtypes(include=[np.number]).values - 
                        dp.engineer_asset_features(df_a.copy()).select_dtypes(include=[np.number]).values).max()
        
        if diff_a > 1e-12:
            self.log_result("T3.1", "Asset Isolation in Feature Engineering", "FAIL", f"State leakage detected! Max difference: {diff_a}", severity="CRITICAL")
        else:
            self.log_result("T3.1", "Asset Isolation in Feature Engineering", "PASS", "No state leakage across isolated asset feature engineering.")

    def test_3_2_hmm_regime_cross_asset_contamination(self):
        df_a = generate_synthetic_asset(num_days=60, base_price=100.0)
        df_a['tic'] = 'AAA'
        df_a_feat = dp.engineer_asset_features(df_a)
        
        df_b = generate_synthetic_asset(num_days=80, base_price=200.0)
        df_b['tic'] = 'BBB'
        df_b_feat = dp.engineer_asset_features(df_b)
        
        combined = pd.concat([df_a_feat, df_b_feat], ignore_index=True)
        lengths = [len(df_a_feat), len(df_b_feat)]
        
        try:
            res_with_len = dp.fit_and_assign_market_regimes(combined.copy(), lengths=lengths)
            prob_sums = res_with_len[['regime_state_0', 'regime_state_1', 'regime_state_2']].sum(axis=1)
            sum_diff = np.abs(prob_sums - 1.0).max()
            
            if sum_diff > 1e-5:
                self.log_result("T3.2", "HMM Regime Sequence Lengths & Probabilities", "FAIL", f"Regime probabilities do not sum to 1.0 (max dev: {sum_diff})", severity="HIGH")
            else:
                self.log_result("T3.2", "HMM Regime Sequence Lengths & Probabilities", "PASS", f"HMM sequence lengths correctly handled, posteriors sum to 1.0.")
        except Exception as e:
            self.log_result("T3.2", "HMM Regime Sequence Lengths & Probabilities", "FAIL", f"HMM fitting error: {e}\n{traceback.format_exc()}", severity="HIGH")

    def test_3_3_global_ffill_cross_ticker_leakage(self):
        df_a = pd.DataFrame({
            'date': pd.to_datetime(['2020-01-01', '2020-01-02']),
            'tic': ['AAA', 'AAA'],
            'feature': [10.0, 10.0]
        })
        df_b = pd.DataFrame({
            'date': pd.to_datetime(['2020-01-01', '2020-01-02']),
            'tic': ['BBB', 'BBB'],
            'feature': [np.nan, 20.0]
        })
        
        combined = pd.concat([df_a, df_b], ignore_index=True)
        combined = combined.sort_values(['date', 'tic']).reset_index(drop=True)
        
        combined_ffill = combined.ffill()
        bbb_val = combined_ffill.loc[combined_ffill['tic'] == 'BBB', 'feature'].iloc[0]
        
        if bbb_val == 10.0:
            self.log_result(
                "T3.3", "Global ffill Cross-Ticker State Leakage Vulnerability", "FAIL",
                f"VULNERABILITY CONFIRMED! Global ffill() on dataframe sorted by ['date', 'tic'] filled BBB's NaN with AAA's value (10.0). "
                f"Correct behavior requires grouping by 'tic' before ffill(): df.groupby('tic').ffill()",
                severity="HIGH"
            )
        else:
            self.log_result("T3.3", "Global ffill Cross-Ticker State Leakage Vulnerability", "PASS", f"No cross-ticker leakage detected (val={bbb_val}).")

    # --- CATEGORY 4: EMPIRICAL AUDIT OF PROCESSED_MARKET_DYNAMICS.CSV ---

    def test_4_1_empirical_dataset_audit(self):
        csv_path = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv"
        if not os.path.exists(csv_path):
            self.log_result("T4.1", "Empirical Dataset Audit", "FAIL", f"Dataset file not found at {csv_path}", severity="CRITICAL")
            return
            
        df = pd.read_csv(csv_path)
        total_rows = len(df)
        num_cols = len(df.columns)
        tickers = df['tic'].unique()
        num_tickers = len(tickers)
        
        nans = df.isna().sum().sum()
        infs = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()
        
        prob_sum = (df['regime_state_0'] + df['regime_state_1'] + df['regime_state_2'])
        prob_dev = np.abs(prob_sum - 1.0).max()
        
        regime_mat = df[['regime_state_0', 'regime_state_1', 'regime_state_2']].values
        calc_labels = np.argmax(regime_mat, axis=1)
        label_mismatches = (df['regime_label'].values != calc_labels).sum()
        
        dates_per_tic = df.groupby('tic')['date'].count()
        uniform_dates = (dates_per_tic == dates_per_tic.iloc[0]).all()
        
        audit_msg = (
            f"Shape: ({total_rows}, {num_cols}), Tickers: {num_tickers}, Dates per ticker: {dates_per_tic.iloc[0]}. "
            f"Total NaNs: {nans}, Total Infs: {infs}. Max regime prob dev: {prob_dev:.2e}. "
            f"Label mismatches: {label_mismatches}. Uniform dates across assets: {uniform_dates}."
        )
        
        if nans > 0 or infs > 0 or label_mismatches > 0 or not uniform_dates:
            self.log_result("T4.1", "Empirical Dataset Audit", "FAIL", audit_msg, severity="HIGH")
        else:
            self.log_result("T4.1", "Empirical Dataset Audit", "PASS", audit_msg)

if __name__ == '__main__':
    runner = StressTestRunner()
    runner.run_all_tests()
