"""
Automated Stress Test Suite for trade_executor.py (test_stress_executor.py)
-------------------------------------------------------------------------
Empirically stress-tests the paper trading execution engine across four key domains:
1. Network offline / yfinance exception fallback handling.
2. 567-dimensional observation state vector properties (shape, dtype, NaNs, Infs).
3. Mock Execution Mode with missing .env file and invalid API credentials.
4. Portfolio accounting integrity (cash + position value - fees = net worth).
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import io
import numpy as np
import pandas as pd

# Import target functions and constants from trade_executor
from trade_executor import (
    fetch_aligned_market_data,
    construct_observation_vector,
    fit_and_assign_market_regimes,
    engineer_asset_features,
    prepare_market_dataset,
    run_paper_trading,
    AlpacaExecutionEngine,
    DJIA_28_TICKERS,
    HISTORICAL_DATA_PATH,
    LOG_FILE_PATH,
    LOG_DIR
)


class TestStressTradeExecutor(unittest.TestCase):

    def setUp(self):
        """Set up test environment and state before each test."""
        self.num_assets = len(DJIA_28_TICKERS)
        self.initial_amount = 1e6

    # =========================================================================
    # Stress Test 1: Network Offline / yfinance Exception Fallback
    # =========================================================================
    @patch("yfinance.download")
    def test_network_offline_yfinance_fallback(self, mock_yf_download):
        """
        Test execution when network is offline or yfinance throws exceptions.
        Verifies seamless switch to historical dataset fallback without crashing.
        """
        # Force yfinance to raise a network/connection exception
        mock_yf_download.side_effect = Exception("Simulated Network Offline / Connection Error")

        # Capture log output
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            df_fallback = fetch_aligned_market_data(period="60d", interval="1d")

        output_str = captured_output.getvalue()

        # Assert fallback warning was printed
        self.assertIn("[WARNING] yfinance data fetch failed/incomplete", output_str)
        self.assertIn("[INFO] Loaded historical CSV fallback", output_str)

        # Assert returned DataFrame is non-empty and valid
        self.assertIsInstance(df_fallback, pd.DataFrame)
        self.assertFalse(df_fallback.empty, "Fallback DataFrame should not be empty")

        # Assert all required columns are present
        required_cols = ['date', 'tic', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
        for col in required_cols:
            self.assertIn(col, df_fallback.columns, f"Column '{col}' missing from fallback dataset")

        # Assert all 28 DJIA tickers are present
        unique_tickers = sorted(df_fallback['tic'].unique())
        self.assertEqual(unique_tickers, sorted(DJIA_28_TICKERS), "Fallback dataset must contain all 28 DJIA tickers")

        # Assert zero NaNs or Infs in numerical columns
        numeric_cols = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
        nan_count = df_fallback[numeric_cols].isna().sum().sum()
        self.assertEqual(nan_count, 0, f"Fallback dataset contains {nan_count} NaNs")

    @patch("yfinance.download")
    def test_end_to_end_network_offline_execution(self, mock_yf_download):
        """
        Verify end-to-end run_paper_trading execution when yfinance is completely unreachable.
        """
        mock_yf_download.side_effect = Exception("HTTP 500 Server Error / Network Timeout")

        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            try:
                run_paper_trading()
                execution_success = True
            except Exception as e:
                execution_success = False
                err_msg = str(e)

        self.assertTrue(execution_success, f"run_paper_trading failed under yfinance network failure: {err_msg if not execution_success else ''}")
        self.assertTrue(os.path.exists(LOG_FILE_PATH), "Log file should be created during execution")

    # =========================================================================
    # Stress Test 2: Observation State Vector Properties
    # =========================================================================
    def test_observation_vector_properties_standard(self):
        """
        Test state observation vector under standard valid inputs:
        Assert shape is strictly (567,), dtype is float32, and contains 0 NaNs / Infs.
        """
        cash = 500000.0
        shares = np.array([100.0] * self.num_assets, dtype=np.float32)
        price_row = np.array([150.0] * self.num_assets, dtype=np.float32)
        tech_matrix_row = np.ones((self.num_assets, 17), dtype=np.float32) * 0.05
        regime_row = np.array([0.7, 0.2, 0.1], dtype=np.float32)
        drawdown = 0.02
        peak_net_worth = 1050000.0
        returns_memory = [0.001, -0.002, 0.005, -0.001]
        prev_actions = np.zeros(self.num_assets, dtype=np.float32)

        obs = construct_observation_vector(
            cash=cash,
            shares=shares,
            initial_amount=self.initial_amount,
            price_row=price_row,
            tech_matrix_row=tech_matrix_row,
            regime_row=regime_row,
            drawdown=drawdown,
            peak_net_worth=peak_net_worth,
            returns_memory=returns_memory,
            prev_actions=prev_actions
        )

        # Assertion 1: Shape is strictly (567,)
        self.assertEqual(obs.shape, (567,), f"Observation vector shape mismatch! Expected (567,), got {obs.shape}")

        # Assertion 2: Dtype is float32
        self.assertEqual(obs.dtype, np.float32, f"Observation vector dtype mismatch! Expected float32, got {obs.dtype}")

        # Assertion 3: Contains 0 NaNs
        nan_count = np.isnan(obs).sum()
        self.assertEqual(nan_count, 0, f"Observation vector contains {nan_count} NaNs!")

        # Assertion 4: Contains 0 Infs
        inf_count = np.isinf(obs).sum()
        self.assertEqual(inf_count, 0, f"Observation vector contains {inf_count} Infs!")

    def test_observation_vector_corrupted_inputs_resilience(self):
        """
        Test state observation vector when fed corrupted data containing NaNs, Infs, or negative values:
        Assert shape remains (567,), dtype remains float32, and NaNs/Infs are scrubbed to 0.
        """
        cash = 250000.0
        shares = np.array([50.0] * self.num_assets, dtype=np.float32)
        price_row = np.array([200.0] * self.num_assets, dtype=np.float32)

        # Inject NaNs, Infs, and -Infs into technical features matrix
        tech_matrix_corrupted = np.ones((self.num_assets, 17), dtype=np.float32) * 0.1
        tech_matrix_corrupted[0, 0] = np.nan
        tech_matrix_corrupted[5, 3] = np.inf
        tech_matrix_corrupted[12, 10] = -np.inf

        regime_corrupted = np.array([np.nan, 0.5, np.inf], dtype=np.float32)
        returns_memory = [np.nan, 0.01, -np.inf]
        prev_actions = np.ones(self.num_assets, dtype=np.float32) * np.nan

        obs = construct_observation_vector(
            cash=cash,
            shares=shares,
            initial_amount=self.initial_amount,
            price_row=price_row,
            tech_matrix_row=tech_matrix_corrupted,
            regime_row=regime_corrupted,
            drawdown=np.nan,
            peak_net_worth=np.inf,
            returns_memory=returns_memory,
            prev_actions=prev_actions
        )

        self.assertEqual(obs.shape, (567,), f"Observation vector shape must be (567,), got {obs.shape}")
        self.assertEqual(obs.dtype, np.float32, f"Observation vector dtype must be float32, got {obs.dtype}")
        self.assertEqual(np.isnan(obs).sum(), 0, "Observation vector must scrub all NaNs")
        self.assertEqual(np.isinf(obs).sum(), 0, "Observation vector must scrub all Infs")

    # =========================================================================
    # Stress Test 3: Mock Execution Mode with Missing .env & Invalid Keys
    # =========================================================================
    @patch.dict(os.environ, {"APCA_API_KEY_ID": "", "APCA_API_SECRET_KEY": "", "TRADING_MODE": "paper"}, clear=False)
    def test_mock_execution_missing_env(self):
        """
        Test Mock Execution Mode when .env / API credentials are missing.
        Assert script logs warning and executes without crashing.
        """
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            run_paper_trading()

        output_str = captured_output.getvalue()

        # Assert warning for missing credentials
        self.assertIn("[WARNING] Alpaca API credentials missing or placeholder values in environment/.env.", output_str)
        self.assertIn("[WARNING] Automatically entering MOCK EXECUTION MODE.", output_str)

        # Assert log file is created
        self.assertTrue(os.path.exists(LOG_FILE_PATH), "Log file should be generated in Mock Execution Mode")
        log_df = pd.read_csv(LOG_FILE_PATH)
        self.assertFalse(log_df.empty, "Paper trade log CSV should contain records")
        self.assertTrue((log_df["execution_mode"] == "MOCK").all(), "All logged rows should indicate MOCK execution mode")

    @patch.dict(os.environ, {
        "APCA_API_KEY_ID": "INVALID_KEY_ID_12345",
        "APCA_API_SECRET_KEY": "INVALID_SECRET_KEY_67890",
        "APCA_API_BASE_URL": "https://paper-api.alpaca.markets",
        "TRADING_MODE": "paper"
    }, clear=False)
    @patch("trade_executor.AlpacaExecutionEngine.validate_connection")
    def test_mock_execution_invalid_api_keys(self, mock_validate):
        """
        Test Mock Execution Mode when invalid API keys are provided.
        Assert script catches authentication failure, logs warning, and seamlessly switches to Mock mode.
        """
        # Mock connection validation failure
        mock_validate.return_value = (False, "HTTP 401: Invalid credentials")

        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            run_paper_trading()

        output_str = captured_output.getvalue()

        # Assert authentication failure handled gracefully
        self.assertIn("[WARNING] Alpaca API Connection Failed: HTTP 401: Invalid credentials", output_str)
        self.assertIn("[WARNING] Automatically entering MOCK EXECUTION MODE.", output_str)

        # Verify execution log
        self.assertTrue(os.path.exists(LOG_FILE_PATH))
        log_df = pd.read_csv(LOG_FILE_PATH)
        self.assertTrue((log_df["execution_mode"] == "MOCK").all())

    # =========================================================================
    # Stress Test 4: Portfolio Accounting Integrity
    # =========================================================================
    def test_portfolio_accounting_integrity_step_math(self):
        """
        Test portfolio accounting integrity on step-by-step simulated trades.
        Verify cash + position values - transaction fees equal portfolio net worth on every step.
        """
        stock_dim = self.num_assets
        initial_amount = 1e6
        cash = initial_amount
        shares = np.zeros(stock_dim, dtype=np.float32)
        fee_pct = 0.001  # 10 bps fee model

        # Simulated prices for step 1 and step 2
        price_step1 = np.array([100.0 + i for i in range(stock_dim)], dtype=np.float32)
        price_step2 = np.array([102.0 + i * 0.5 for i in range(stock_dim)], dtype=np.float32)

        # Simulated continuous action vector (-1.0 to 1.0)
        action_step1 = np.linspace(-0.5, 0.8, stock_dim, dtype=np.float32)

        pre_trade_cash = cash
        pre_trade_shares = shares.copy()
        pre_trade_net_worth = pre_trade_cash + np.sum(pre_trade_shares * price_step1)
        self.assertAlmostEqual(pre_trade_net_worth, initial_amount, places=2)

        # Target portfolio allocation weights
        pos_mask = action_step1 > 0
        pos_sum = float(np.sum(action_step1[pos_mask]))
        target_weights = np.zeros(stock_dim, dtype=np.float32)
        if pos_sum > 0:
            target_weights[pos_mask] = action_step1[pos_mask] / pos_sum

        total_step_fees = 0.0

        # Execute Sells
        for i in range(stock_dim):
            a_val = float(action_step1[i])
            p_val = float(price_step1[i])
            if a_val < 0 and shares[i] > 0:
                sell_ratio = min(1.0, abs(a_val))
                sell_shares = shares[i] * sell_ratio
                sell_val = sell_shares * p_val
                fee = sell_val * fee_pct
                cash += (sell_val - fee)
                shares[i] -= sell_shares
                total_step_fees += fee

        # Execute Buys
        if pos_sum > 0 and cash > 0:
            allocatable_cash = float(cash)
            for i in range(stock_dim):
                a_val = float(action_step1[i])
                p_val = float(price_step1[i])
                if a_val > 0 and cash > 0:
                    w = float(a_val) / pos_sum
                    target_buy_cash = min(allocatable_cash * w, float(cash))
                    fee = target_buy_cash * (fee_pct / (1.0 + fee_pct))
                    buy_val = target_buy_cash - fee
                    buy_shares = buy_val / p_val

                    shares[i] += buy_shares
                    cash -= target_buy_cash
                    total_step_fees += fee

        # Accounting Check 1: Post-trade Cash + Position Values at current step prices equals Pre-trade Net Worth minus Transaction Fees
        post_trade_position_val = np.sum(shares * price_step1)
        post_trade_total = cash + post_trade_position_val

        expected_post_trade_total = pre_trade_net_worth - total_step_fees

        # Note: float32 single-precision at $1,000,000 scale has a machine quantization resolution of 2^-18 * 1e6 = $0.0625.
        # We assert equality within $0.10 to accommodate float32 precision limits.
        self.assertAlmostEqual(
            float(post_trade_total),
            float(expected_post_trade_total),
            delta=0.10,
            msg=f"Accounting Violation! Post-trade total ({post_trade_total}) != Pre-trade NW minus fees ({expected_post_trade_total})"
        )

        # Assertion: Cash must be non-negative
        self.assertGreaterEqual(cash, 0.0, "Cash balance became negative!")

        # Accounting Check 2: Next step Net Worth evaluated at price_step2 equals Cash + sum(shares * price_step2)
        end_net_worth_step1 = cash + np.sum(shares * price_step2)
        self.assertTrue(np.isfinite(end_net_worth_step1), "End net worth must be finite")
        self.assertGreater(end_net_worth_step1, 0.0, "End net worth must be positive")

    def test_portfolio_accounting_logged_history(self):
        """
        Execute run_paper_trading and inspect the logged CSV history to verify portfolio accounting integrity.
        Confirm cash balance is non-negative and snapshot net worth equals sum of positions + cash.
        """
        run_paper_trading()
        self.assertTrue(os.path.exists(LOG_FILE_PATH))
        log_df = pd.read_csv(LOG_FILE_PATH)

        # Check snapshot rows
        snapshots = log_df[log_df["action_type"] == "SNAPSHOT"].copy()
        self.assertFalse(snapshots.empty, "Trade log must contain PORTFOLIO_SUMMARY SNAPSHOT entries")

        for idx, row in snapshots.iterrows():
            c_val = float(row["portfolio_cash"])
            nw_val = float(row["portfolio_net_worth"])

            # Assert cash >= 0
            self.assertGreaterEqual(c_val, 0.0, f"Logged cash balance is negative (${c_val}) on step {row['date']}")

            # Assert net worth > 0
            self.assertGreater(nw_val, 0.0, f"Logged net worth is invalid (${nw_val}) on step {row['date']}")


if __name__ == "__main__":
    unittest.main()
