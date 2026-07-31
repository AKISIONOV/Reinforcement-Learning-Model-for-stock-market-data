"""
Automated Stress Test Suite for RL Paper Trading Dashboard (dashboard.py)
-----------------------------------------------------------------------
Empirically stress-tests dashboard.py data loader functions, metric calculation
logic for edge cases (missing file, empty file, corrupted file, single-row logs,
multi-row logs), and verifies headless Streamlit execution.
"""

import os
import sys
import tempfile
import time
import subprocess
import pytest
import pandas as pd
import numpy as np

# Import functions from dashboard.py
from dashboard import load_trade_log, INITIAL_CAPITAL


class TestDashboardDataLoading:
    """Stress tests for load_trade_log() under invalid file scenarios."""

    def test_load_trade_log_non_existent_file(self):
        """Test 1: Assert load_trade_log() handles non-existent file path gracefully."""
        non_existent_path = "os_non_existent_log_file_path_12345.csv"
        df, error_msg = load_trade_log(non_existent_path)
        
        assert df is None, f"Expected df to be None, got {type(df)}"
        assert error_msg is not None, "Expected non-None error message"
        assert "File not found" in error_msg, f"Unexpected error message: {error_msg}"
        assert non_existent_path in error_msg

    def test_load_trade_log_empty_csv(self):
        """Test 2a: Assert load_trade_log() handles 0-byte or header-only empty CSV gracefully."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            # Test completely empty 0-byte file
            df, error_msg = load_trade_log(tmp_path)
            assert df is None, f"Expected None for 0-byte file, got {df}"
            assert error_msg is not None
            assert ("no records" in error_msg.lower() or "failed to parse" in error_msg.lower())
            
            # Test CSV with header but no data rows
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("timestamp,date,ticker,action_type,portfolio_net_worth\n")
                
            df, error_msg = load_trade_log(tmp_path)
            assert df is None, f"Expected None for empty dataframe, got {df}"
            assert error_msg is not None
            assert "no records" in error_msg.lower()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_load_trade_log_corrupted_csv(self):
        """Test 2b: Assert load_trade_log() handles corrupted/unparseable CSV file gracefully."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            # Write binary garbage or invalid CSV syntax
            with open(tmp_path, "wb") as f:
                f.write(b"\x00\xff\xfe\xfd\x00\x01\x02\x03\x04\x05 corrupt binary stream data\n")
                
            df, error_msg = load_trade_log(tmp_path)
            assert df is None, f"Expected df to be None for corrupted CSV, got {df}"
            assert error_msg is not None, "Expected error message for corrupted CSV"
            assert "Failed to parse CSV log file" in error_msg or "Error" in error_msg
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestDashboardMetricCalculations:
    """Stress tests metric calculation logic on single-row and multi-row trade logs."""

    def calculate_dashboard_metrics(self, df: pd.DataFrame):
        """
        Helper reproducing the exact metric calculation logic of dashboard.py
        to test calculation accuracy on given trade log DataFrames.
        """
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        df_snapshots = df[df['action_type'] == 'SNAPSHOT'].copy()
        if df_snapshots.empty:
            df_snapshots = df.drop_duplicates(subset=['date'], keep='last').copy()

        sort_cols = ['date']
        if 'timestamp' in df_snapshots.columns:
            sort_cols.append('timestamp')
        df_snapshots = df_snapshots.sort_values(by=sort_cols).reset_index(drop=True)

        latest_snap = df_snapshots.iloc[-1]
        latest_net_worth = float(latest_snap['portfolio_net_worth'])
        prev_net_worth = float(df_snapshots.iloc[-2]['portfolio_net_worth']) if len(df_snapshots) > 1 else INITIAL_CAPITAL

        dollar_change = latest_net_worth - INITIAL_CAPITAL
        total_return_pct = (dollar_change / INITIAL_CAPITAL) * 100.0

        raw_daily_ret = float(latest_snap.get('daily_return', 0.0))
        daily_return_pct = raw_daily_ret * 100.0 if abs(raw_daily_ret) <= 1.0 else raw_daily_ret

        if len(df_snapshots) > 1:
            prev_raw_daily = float(df_snapshots.iloc[-2].get('daily_return', 0.0))
            prev_daily_pct = prev_raw_daily * 100.0 if abs(prev_raw_daily) <= 1.0 else prev_raw_daily
            daily_ret_delta = daily_return_pct - prev_daily_pct
        else:
            daily_ret_delta = daily_return_pct

        curr_regime = str(latest_snap.get('market_regime', 'Neutral'))
        regime_counts = df_snapshots['market_regime'].value_counts().to_dict()

        return {
            'latest_net_worth': latest_net_worth,
            'prev_net_worth': prev_net_worth,
            'dollar_change': dollar_change,
            'total_return_pct': total_return_pct,
            'daily_return_pct': daily_return_pct,
            'daily_ret_delta': daily_ret_delta,
            'curr_regime': curr_regime,
            'regime_counts': regime_counts,
            'snapshot_count': len(df_snapshots)
        }

    def test_single_row_trade_log(self):
        """Test 3a: Verify metric calculations for single-row trade log."""
        single_row_df = pd.DataFrame([{
            'timestamp': '2026-07-31T10:00:00Z',
            'date': '2026-07-31',
            'ticker': 'PORTFOLIO_SUMMARY',
            'action_type': 'SNAPSHOT',
            'raw_action': 0.0,
            'target_weight': 0.0,
            'shares': 0.0,
            'price': 0.0,
            'trade_value': 0.0,
            'fee': 0.0,
            'portfolio_cash': 500000.0,
            'portfolio_net_worth': 1050000.0,
            'daily_return': 0.05,
            'drawdown': 0.0,
            'market_regime': 'Bullish Low-Vol',
            'execution_mode': 'MOCK'
        }])

        metrics = self.calculate_dashboard_metrics(single_row_df)

        assert metrics['latest_net_worth'] == 1050000.0
        assert metrics['dollar_change'] == 50000.0
        assert metrics['total_return_pct'] == 5.0
        assert metrics['daily_return_pct'] == 5.0
        assert metrics['daily_ret_delta'] == 5.0
        assert metrics['curr_regime'] == 'Bullish Low-Vol'
        assert metrics['regime_counts'] == {'Bullish Low-Vol': 1}
        assert metrics['snapshot_count'] == 1

    def test_multi_row_trade_log(self):
        """Test 3b: Verify metric calculations for multi-row trade log across multiple dates/regimes."""
        rows = [
            # Day 1
            {'timestamp': '2026-07-01T10:00:00Z', 'date': '2026-07-01', 'ticker': 'AAPL', 'action_type': 'BUY', 'portfolio_net_worth': 1000000.0, 'daily_return': 0.0, 'market_regime': 'Neutral'},
            {'timestamp': '2026-07-01T10:00:00Z', 'date': '2026-07-01', 'ticker': 'PORTFOLIO_SUMMARY', 'action_type': 'SNAPSHOT', 'portfolio_net_worth': 1000000.0, 'daily_return': 0.0, 'market_regime': 'Neutral'},
            # Day 2
            {'timestamp': '2026-07-02T10:00:00Z', 'date': '2026-07-02', 'ticker': 'PORTFOLIO_SUMMARY', 'action_type': 'SNAPSHOT', 'portfolio_net_worth': 1020000.0, 'daily_return': 0.02, 'market_regime': 'Bullish Low-Vol'},
            # Day 3
            {'timestamp': '2026-07-03T10:00:00Z', 'date': '2026-07-03', 'ticker': 'PORTFOLIO_SUMMARY', 'action_type': 'SNAPSHOT', 'portfolio_net_worth': 990000.0, 'daily_return': -0.0294, 'market_regime': 'Bearish High-Vol'},
            # Day 4
            {'timestamp': '2026-07-04T10:00:00Z', 'date': '2026-07-04', 'ticker': 'PORTFOLIO_SUMMARY', 'action_type': 'SNAPSHOT', 'portfolio_net_worth': 1080000.0, 'daily_return': 0.0909, 'market_regime': 'Bullish Low-Vol'}
        ]
        multi_row_df = pd.DataFrame(rows)

        metrics = self.calculate_dashboard_metrics(multi_row_df)

        assert metrics['latest_net_worth'] == 1080000.0
        assert metrics['prev_net_worth'] == 990000.0
        assert metrics['dollar_change'] == 80000.0
        assert metrics['total_return_pct'] == 8.0
        assert pytest.approx(metrics['daily_return_pct'], 0.01) == 9.09
        assert pytest.approx(metrics['daily_ret_delta'], 0.01) == (9.09 - (-2.94))
        assert metrics['curr_regime'] == 'Bullish Low-Vol'
        assert metrics['regime_counts'] == {
            'Bullish Low-Vol': 2,
            'Neutral': 1,
            'Bearish High-Vol': 1
        }
        assert metrics['snapshot_count'] == 4


class TestHeadlessStreamlitRendering:
    """Stress test for headless rendering stability of dashboard.py."""

    def test_headless_streamlit_rendering(self):
        """Test 4: Launch streamlit run dashboard.py --server.headless=true and check startup stability."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dashboard_script = os.path.join(script_dir, "dashboard.py")
        assert os.path.exists(dashboard_script), f"dashboard.py not found at {dashboard_script}"

        cmd = [
            sys.executable, "-m", "streamlit", "run", dashboard_script,
            "--server.headless=true",
            "--server.port=8509"
        ]

        env = os.environ.copy()
        # Launch subprocess
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=script_dir,
            env=env
        )

        try:
            # Allow Streamlit process 5 seconds to initialize and start server
            time.sleep(5)
            
            # Check if process terminated prematurely (indicates crash during import / rendering)
            poll_res = proc.poll()
            if poll_res is not None:
                stdout, stderr = proc.communicate()
                pytest.fail(f"Streamlit headless process exited prematurely with exit code {poll_res}.\nSTDOUT: {stdout}\nSTDERR: {stderr}")

            # Process is still running smoothly as expected for a web server
            assert proc.poll() is None, "Streamlit headless process stopped unexpectedly"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
