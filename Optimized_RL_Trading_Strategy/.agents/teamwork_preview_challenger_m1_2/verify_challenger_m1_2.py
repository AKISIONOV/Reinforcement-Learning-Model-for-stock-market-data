import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import adfuller, kpss

# Import data_pipeline functions
from data_pipeline import (
    engineer_asset_features,
    fit_and_assign_market_regimes,
    compute_corwin_schultz_spread,
    compute_garch_volatility,
    fallback_garch11
)

CSV_PATH = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/data/processed_market_dynamics.csv"
OUTPUT_DIR = r"f:/SURE Trust/Capstone Project/Optimized_RL_Trading_Strategy/.agents/teamwork_preview_challenger_m1_2"

def run_empirical_distribution_checks(df):
    print("=== 1. EMPIRICAL DISTRIBUTION CHECKS ===")
    print(f"Total Rows: {len(df)}")
    print(f"Total Columns: {len(df.columns)}")
    print(f"Tickers present ({df['tic'].nunique()}): {sorted(df['tic'].unique())}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    # Check rows per ticker
    rows_per_tic = df.groupby('tic').size()
    print(f"Rows per ticker min: {rows_per_tic.min()}, max: {rows_per_tic.max()}, median: {rows_per_tic.median()}")
    
    feature_cols = [c for c in df.columns if c not in ['date', 'tic', 'open', 'high', 'low', 'close', 'adj_close', 'volume']]
    print(f"Engineered feature columns ({len(feature_cols)}): {feature_cols}")
    
    stats_list = []
    for col in feature_cols:
        series = df[col]
        nans = series.isna().sum()
        infs = np.isinf(series).sum()
        zeros = (series == 0).sum()
        
        mean_val = series.mean()
        std_val = series.std()
        min_val = series.min()
        q25 = series.quantile(0.25)
        median_val = series.median()
        q75 = series.quantile(0.75)
        max_val = series.max()
        skew_val = series.skew()
        kurt_val = series.kurtosis()
        
        stats_list.append({
            'feature': col,
            'nans': nans,
            'infs': infs,
            'zeros': zeros,
            'mean': mean_val,
            'std': std_val,
            'min': min_val,
            'q25': q25,
            'median': median_val,
            'q75': q75,
            'max': max_val,
            'skewness': skew_val,
            'kurtosis': kurt_val
        })
        
    stats_df = pd.DataFrame(stats_list)
    print("\n--- Summary Statistics ---")
    print(stats_df.to_string())
    return stats_df


def run_stationarity_tests(df):
    print("\n=== 2. STATIONARITY TESTS (ADF & KPSS) ===")
    continuous_features = [
        'return', 'log_return', 'ewma_vol', 'volatility_ratio_5_21',
        'garman_klass_vol', 'garch_vol', 'shadow_upper', 'shadow_lower',
        'shadow_ratio', 'vwap_distance', 'order_flow_imbalance',
        'corwin_schultz_spread', 'return_shock_zscore', 'volume_spike_index',
        'joint_vol_vol_shock'
    ]
    
    results = []
    
    # We will run tests on pooled features and per-ticker average p-values
    for col in continuous_features:
        # Pooled sample (sample first 5000 rows to speed up if large, or full)
        series = df[col].dropna()
        
        # ADF Test
        try:
            adf_res = adfuller(series, maxlag=20, autolag='AIC')
            adf_stat, adf_p = adf_res[0], adf_res[1]
        except Exception as e:
            adf_stat, adf_p = np.nan, np.nan
            
        # KPSS Test
        try:
            kpss_res = kpss(series, regression='c', nlags='auto')
            kpss_stat, kpss_p = kpss_res[0], kpss_res[1]
        except Exception as e:
            kpss_stat, kpss_p = np.nan, np.nan
            
        # Per-ticker ADF rejection rate (at alpha = 0.05)
        adf_rej_count = 0
        kpss_rej_count = 0
        tic_count = 0
        
        for tic, group in df.groupby('tic'):
            g_series = group[col].dropna()
            if len(g_series) > 30:
                tic_count += 1
                try:
                    res_a = adfuller(g_series, autolag='AIC')
                    if res_a[1] < 0.05:
                        adf_rej_count += 1
                except:
                    pass
                try:
                    res_k = kpss(g_series, regression='c', nlags='auto')
                    if res_k[1] < 0.05:
                        kpss_rej_count += 1
                except:
                    pass
                    
        adf_stationarity_pct = (adf_rej_count / tic_count * 100.0) if tic_count > 0 else 0
        kpss_nonstationarity_pct = (kpss_rej_count / tic_count * 100.0) if tic_count > 0 else 0
        
        # Classification
        # Stationary: ADF rejects H0 (p < 0.05) AND KPSS fails to reject H0 (p >= 0.05)
        if adf_p < 0.05 and kpss_p >= 0.05:
            verdict = "Strictly Stationary"
        elif adf_p < 0.05 and kpss_p < 0.05:
            verdict = "Difference Stationary / Heavy Tails"
        elif adf_p >= 0.05 and kpss_p < 0.05:
            verdict = "Non-Stationary (Unit Root)"
        else:
            verdict = "Inconclusive"
            
        results.append({
            'feature': col,
            'adf_stat': adf_stat,
            'adf_p': adf_p,
            'kpss_stat': kpss_stat,
            'kpss_p': kpss_p,
            'ticker_adf_rej_pct': adf_stationarity_pct,
            'ticker_kpss_rej_pct': kpss_nonstationarity_pct,
            'verdict': verdict
        })
        
    res_df = pd.DataFrame(results)
    print(res_df.to_string())
    return res_df


def run_regime_verification(df):
    print("\n=== 3. REGIME PROBABILITY BOUNDS & CONSISTENCY VERIFICATION ===")
    p0 = df['regime_state_0']
    p1 = df['regime_state_1']
    p2 = df['regime_state_2']
    labels = df['regime_label']
    
    # 1. Bounds check
    min_val = min(p0.min(), p1.min(), p2.min())
    max_val = max(p0.max(), p1.max(), p2.max())
    out_of_bounds = ((p0 < 0) | (p0 > 1) | (p1 < 0) | (p1 > 1) | (p2 < 0) | (p2 > 1)).sum()
    
    print(f"Min probability across states: {min_val}")
    print(f"Max probability across states: {max_val}")
    print(f"Out of bounds count [0, 1]: {out_of_bounds}")
    
    # 2. Sum check
    prob_sum = p0 + p1 + p2
    sum_err = np.abs(prob_sum - 1.0)
    max_sum_err = sum_err.max()
    sum_violations = (sum_err > 1e-5).sum()
    print(f"Max sum absolute deviation from 1.0: {max_sum_err}")
    print(f"Sum violations (> 1e-5): {sum_violations}")
    
    # 3. Label argmax consistency check
    expected_labels = np.argmax(df[['regime_state_0', 'regime_state_1', 'regime_state_2']].values, axis=1)
    label_mismatches = (labels != expected_labels).sum()
    print(f"Regime label vs argmax mismatches: {label_mismatches}")
    
    # 4. State distribution
    label_counts = df['regime_label'].value_counts().sort_index()
    print(f"Regime label distribution:\n{label_counts}")
    print(f"Regime label percentages:\n{label_counts / len(df) * 100.0}")
    
    # 5. State characterization (mean return & mean vol per state)
    print("\n--- Mean Return & Volatility per Regime State ---")
    for s in [0, 1, 2]:
        sub = df[df['regime_label'] == s]
        ret_m = sub['return'].mean()
        vol_m = sub['ewma_vol'].mean()
        garch_m = sub['garch_vol'].mean()
        print(f"State {s}: Count={len(sub)} ({len(sub)/len(df)*100:.1f}%), Return Mean={ret_m:.6f}, EWMA Vol Mean={vol_m:.6f}, GARCH Vol Mean={garch_m:.6f}")
        
    # 6. Regime Persistence (average run length of states)
    runs = (df['regime_label'] != df['regime_label'].shift(1)).cumsum()
    run_lengths = df.groupby(runs)['regime_label'].agg(['first', 'count'])
    avg_durations = run_lengths.groupby('first')['count'].mean()
    print("\n--- Average Regime Persistence (days) ---")
    print(avg_durations)
    
    return {
        'min_prob': min_val,
        'max_prob': max_val,
        'out_of_bounds': out_of_bounds,
        'max_sum_err': max_sum_err,
        'sum_violations': sum_violations,
        'label_mismatches': label_mismatches,
        'label_counts': label_counts.to_dict(),
        'avg_durations': avg_durations.to_dict()
    }


def run_adversarial_stress_tests():
    print("\n=== 4. ADVERSARIAL STRESS TESTS ON CODEBASE ===")
    test_results = []
    
    # Helper to generate dummy asset dataframe
    def make_dummy_df(n=50, open_p=100.0, high_p=105.0, low_p=95.0, close_p=100.0, volume=1000000):
        dates = pd.date_range('2020-01-01', periods=n, freq='D')
        return pd.DataFrame({
            'date': dates,
            'tic': 'TEST',
            'open': [open_p] * n,
            'high': [high_p] * n,
            'low': [low_p] * n,
            'close': [close_p] * n,
            'adj_close': [close_p] * n,
            'volume': [volume] * n
        })

    # Test 1: Flatline (Zero Volatility)
    print("\n--- Test 1: Flatline / Zero Volatility ---")
    df_flat = make_dummy_df(n=50, open_p=100.0, high_p=100.0, low_p=100.0, close_p=100.0, volume=1000000)
    try:
        res_flat = engineer_asset_features(df_flat)
        nans = res_flat.isna().sum().sum()
        infs = np.isinf(res_flat.select_dtypes(include=np.number)).sum().sum()
        print(f"Flatline execution: SUCCESS. Output rows={len(res_flat)}, NaNs={nans}, Infs={infs}")
        if nans > 0 or infs > 0:
            print("NaN/Inf breakdown in flatline:")
            print(res_flat.isna().sum()[res_flat.isna().sum() > 0])
            print(np.isinf(res_flat.select_dtypes(include=np.number)).sum()[np.isinf(res_flat.select_dtypes(include=np.number)).sum() > 0])
        test_results.append(('Flatline / Zero Volatility', 'PASS' if nans == 0 and infs == 0 else 'FAIL/WARNING', f"NaNs: {nans}, Infs: {infs}"))
    except Exception as e:
        print(f"Flatline execution FAILED with error: {e}")
        test_results.append(('Flatline / Zero Volatility', 'CRASH', str(e)))

    # Test 2: Extreme Volatility / 1000% Spike
    print("\n--- Test 2: Extreme Volatility Spike ---")
    df_spike = make_dummy_df(n=50)
    df_spike.loc[25, 'high'] = 10000.0
    df_spike.loc[25, 'close'] = 9000.0
    df_spike.loc[25, 'adj_close'] = 9000.0
    try:
        res_spike = engineer_asset_features(df_spike)
        nans = res_spike.isna().sum().sum()
        infs = np.isinf(res_spike.select_dtypes(include=np.number)).sum().sum()
        print(f"Spike execution: SUCCESS. Output rows={len(res_spike)}, NaNs={nans}, Infs={infs}")
        test_results.append(('Extreme Volatility Spike', 'PASS' if nans == 0 and infs == 0 else 'FAIL/WARNING', f"NaNs: {nans}, Infs: {infs}"))
    except Exception as e:
        print(f"Spike execution FAILED: {e}")
        test_results.append(('Extreme Volatility Spike', 'CRASH', str(e)))

    # Test 3: Zero Volume Bar Run
    print("\n--- Test 3: Zero Volume Bar Run ---")
    df_zero_vol = make_dummy_df(n=50, volume=0)
    try:
        res_zv = engineer_asset_features(df_zero_vol)
        nans = res_zv.isna().sum().sum()
        infs = np.isinf(res_zv.select_dtypes(include=np.number)).sum().sum()
        print(f"Zero volume execution: SUCCESS. Output rows={len(res_zv)}, NaNs={nans}, Infs={infs}")
        if nans > 0 or infs > 0:
            print("Zero volume NaN/Inf details:")
            print(res_zv.isna().sum()[res_zv.isna().sum() > 0])
        test_results.append(('Zero Volume Run', 'PASS' if nans == 0 and infs == 0 else 'FAIL/WARNING', f"NaNs: {nans}, Infs: {infs}"))
    except Exception as e:
        print(f"Zero volume execution FAILED: {e}")
        test_results.append(('Zero Volume Run', 'CRASH', str(e)))

    # Test 4: Zero / Negative Prices
    print("\n--- Test 4: Zero or Negative Prices ---")
    df_neg = make_dummy_df(n=50)
    df_neg.loc[25, 'low'] = 0.0
    df_neg.loc[26, 'low'] = -5.0
    try:
        res_neg = engineer_asset_features(df_neg)
        nans = res_neg.isna().sum().sum()
        infs = np.isinf(res_neg.select_dtypes(include=np.number)).sum().sum()
        print(f"Negative price execution: Output rows={len(res_neg)}, NaNs={nans}, Infs={infs}")
        if nans > 0 or infs > 0:
            print("Negative price NaN/Inf details:")
            print(res_neg.isna().sum()[res_neg.isna().sum() > 0])
            print(np.isinf(res_neg.select_dtypes(include=np.number)).sum()[np.isinf(res_neg.select_dtypes(include=np.number)).sum() > 0])
        test_results.append(('Zero/Negative Prices', 'PASS' if nans == 0 and infs == 0 else 'FAIL/WARNING', f"NaNs: {nans}, Infs: {infs}"))
    except Exception as e:
        print(f"Negative price execution FAILED: {e}")
        test_results.append(('Zero/Negative Prices', 'CRASH', str(e)))

    # Test 5: Corwin-Schultz Spread Alpha Negative Case
    print("\n--- Test 5: Corwin-Schultz Negative Alpha Case ---")
    high_cs = pd.Series([100.0, 100.0, 100.0, 100.0])
    low_cs = pd.Series([100.0, 100.0, 100.0, 100.0])
    try:
        cs_val = compute_corwin_schultz_spread(high_cs, low_cs)
        has_nan = np.isnan(cs_val).any()
        has_inf = np.isinf(cs_val).any()
        min_cs = cs_val.min()
        print(f"Corwin-Schultz Flatline: Has NaN={has_nan}, Has Inf={has_inf}, Min={min_cs}, Max={cs_val.max()}")
        test_results.append(('Corwin-Schultz Flatline', 'PASS' if not (has_nan or has_inf) else 'FAIL/WARNING', f"Values: {cs_val}"))
    except Exception as e:
        test_results.append(('Corwin-Schultz Flatline', 'CRASH', str(e)))

    # Test 6: Short Dataset (< 21 rows)
    print("\n--- Test 6: Short Dataframe (< 21 rows) ---")
    df_short = make_dummy_df(n=15)
    try:
        res_short = engineer_asset_features(df_short)
        print(f"Short dataframe output rows: {len(res_short)}")
        if len(res_short) == 0:
            print("WARNING: Short dataframe resulted in 0 rows due to dropna() after 21-day rolling window!")
        test_results.append(('Short Dataframe (<21 rows)', 'EMPTY_OUTPUT' if len(res_short)==0 else 'PASS', f"Returned {len(res_short)} rows"))
    except Exception as e:
        print(f"Short dataframe execution FAILED: {e}")
        test_results.append(('Short Dataframe (<21 rows)', 'CRASH', str(e)))

    # Test 7: Regime Model Fallbacks (GMM and KMeans)
    print("\n--- Test 7: Regime Model Fallbacks ---")
    df_dummy1 = make_dummy_df(n=50)
    df_dummy1['tic'] = 'A'
    df_dummy1_feat = engineer_asset_features(df_dummy1)
    
    df_dummy2 = make_dummy_df(n=50)
    df_dummy2['tic'] = 'B'
    df_dummy2_feat = engineer_asset_features(df_dummy2)
    
    combined_test = pd.concat([df_dummy1_feat, df_dummy2_feat], ignore_index=True)
    lengths_test = [len(df_dummy1_feat), len(df_dummy2_feat)]
    
    try:
        res_reg = fit_and_assign_market_regimes(combined_test, lengths=lengths_test)
        sum_p = res_reg['regime_state_0'] + res_reg['regime_state_1'] + res_reg['regime_state_2']
        max_err = np.abs(sum_p - 1.0).max()
        print(f"Regime fitting test: SUCCESS. Max sum error: {max_err}")
        test_results.append(('Regime Fitting Normal Case', 'PASS', f"Max sum err: {max_err}"))
    except Exception as e:
        print(f"Regime fitting test FAILED: {e}")
        test_results.append(('Regime Fitting Normal Case', 'CRASH', str(e)))

    test_summary_df = pd.DataFrame(test_results, columns=['Test Scenario', 'Status', 'Details'])
    print("\n--- Stress Test Summary Table ---")
    print(test_summary_df.to_string())
    return test_summary_df


if __name__ == '__main__':
    df = pd.read_csv(CSV_PATH)
    stats_df = run_empirical_distribution_checks(df)
    stat_df = run_stationarity_tests(df)
    reg_dict = run_regime_verification(df)
    stress_df = run_adversarial_stress_tests()
    
    # Save outputs to files for auditability
    stats_df.to_csv(os.path.join(OUTPUT_DIR, "empirical_stats.csv"), index=False)
    stat_df.to_csv(os.path.join(OUTPUT_DIR, "stationarity_results.csv"), index=False)
    stress_df.to_csv(os.path.join(OUTPUT_DIR, "stress_test_results.csv"), index=False)
    print("\nAll verification tests completed and exported to output directory.")
