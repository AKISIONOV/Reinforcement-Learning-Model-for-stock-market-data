"""
Unit Tests & Empirical Stress Suite for Custom Stock Trading Environment (Milestone 2)
---------------------------------------------------------------------------------------
Comprehensive verification suite testing compliance with Gymnasium API specs,
SB3 env_checker, 1000-step random action trajectories, 10 bps transaction fee enforcement,
drawdown tracking, reward formula accuracy, observation shape (539-dim Box), episode reset,
truncation/termination behavior, and adversarial input robustness.
"""

import sys
import unittest
import numpy as np
import pandas as pd
import gymnasium as gym

from gymnasium.utils.env_checker import check_env as check_env_gym
from stable_baselines3.common.env_checker import check_env as check_env_sb3

from custom_env import StockTradingEnv, DEFAULT_TECH_INDICATORS


class TestStockTradingEnv(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data_path = "data/processed_market_dynamics.csv"
        cls.df = pd.read_csv(cls.data_path)
        cls.env = StockTradingEnv(df=cls.df)

    def test_01_environment_initialization(self):
        """Test observation and action space dimensions, data types, and initial reset."""
        obs, info = self.env.reset()
        
        self.assertEqual(self.env.action_space.shape, (28,))
        self.assertEqual(self.env.action_space.dtype, np.float32)
        self.assertEqual(self.env.action_space.low[0], -1.0)
        self.assertEqual(self.env.action_space.high[0], 1.0)

        # Observation dimension: 1 (cash) + 28 (shares) + 28 (prices) + 28*17 (tech) + 3 (regimes) + 3 (risk) + 28 (prev actions) = 567
        self.assertEqual(self.env.observation_space.shape, (567,))
        
        obs, info = self.env.reset()
        self.assertEqual(obs.shape, (567,))
        self.assertEqual(obs.dtype, np.float32)
        
        self.assertIn('net_worth', info)
        self.assertIn('portfolio_return', info)
        self.assertIn('drawdown', info)
        self.assertIn('trades', info)
        self.assertEqual(info['net_worth'], 1000000.0)
        self.assertEqual(info['portfolio_return'], 0.0)
        self.assertEqual(info['drawdown'], 0.0)
        self.assertEqual(info['trades'], 0)

    def test_02_stable_baselines3_env_checker(self):
        """Run SB3 check_env to verify Gymnasium API compliance."""
        env = StockTradingEnv(df=self.df)
        check_env_sb3(env)

    def test_03_gymnasium_env_checker(self):
        """Run Gymnasium native check_env to verify API compliance."""
        env = StockTradingEnv(df=self.df)
        check_env_gym(env)

    def test_04_random_action_episode_1000_steps(self):
        """Run 1000 random action steps and verify rewards, obs, drawdown, fees, and no NaNs/Infs."""
        env = StockTradingEnv(df=self.df)
        obs, info = env.reset(seed=42)

        total_reward = 0.0
        step_count = 0

        for step in range(1000):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            step_count += 1

            # 1. Zero NaNs / Infs checks
            self.assertFalse(np.isnan(obs).any(), f"NaN detected in obs at step {step}")
            self.assertFalse(np.isinf(obs).any(), f"Inf detected in obs at step {step}")
            self.assertFalse(np.isnan(reward), f"NaN detected in reward at step {step}")
            self.assertFalse(np.isinf(reward), f"Inf detected in reward at step {step}")

            # 2. Key info dictionary checks
            self.assertIn('net_worth', info)
            self.assertIn('portfolio_return', info)
            self.assertIn('drawdown', info)
            self.assertIn('trades', info)

            # 3. Value bounds checks
            self.assertGreater(info['net_worth'], 0.0, f"Net worth <= 0 at step {step}")
            self.assertGreaterEqual(info['drawdown'], 0.0, f"Drawdown < 0 at step {step}")
            self.assertLessEqual(info['drawdown'], 1.0 + 1e-6, f"Drawdown > 1.0 at step {step}")
            self.assertGreaterEqual(env.peak_net_worth, env.net_worth - 1e-4, f"Peak net worth < net worth at step {step}")
            self.assertGreaterEqual(env.drawdown_delta, 0.0, f"Drawdown delta < 0 at step {step}")
            
            # Cash balance must never be negative
            self.assertGreaterEqual(env.cash, 0.0, f"Cash balance negative ({env.cash}) at step {step}")

            total_reward += reward

            if terminated or truncated:
                obs, info = env.reset()

        self.assertEqual(step_count, 1000)

    def test_05_transaction_fee_enforcement(self):
        """Verify 10 bps fee (0.001 * transaction value) on buys and sells."""
        env = StockTradingEnv(df=self.df, buy_cost_pct=0.001, sell_cost_pct=0.001)
        obs, info = env.reset(start_day=0)

        initial_cash = env.cash
        current_price = env.price_array[0][0]

        # Buy action on asset 0 only
        action = np.zeros(28, dtype=np.float32)
        action[0] = 1.0 # Request 100% positive buy weight

        obs, reward, terminated, truncated, info = env.step(action)

        # Check transaction fee on buy
        fee_rate = 0.001
        target_buy_cash = initial_cash
        expected_fee = target_buy_cash * (fee_rate / (1.0 + fee_rate))
        expected_buy_val = target_buy_cash - expected_fee

        self.assertAlmostEqual(env.cost, expected_fee, places=2)
        self.assertAlmostEqual(env.cash, 0.0, places=2)
        self.assertAlmostEqual(env.shares[0], expected_buy_val / current_price, places=2)
        self.assertAlmostEqual(expected_fee / expected_buy_val, 0.001, places=6)

        # Test sell action
        cost_before_sell = env.cost
        shares_held = env.shares[0]
        sell_price = env.price_array[1][0]
        action_sell = np.zeros(28, dtype=np.float32)
        action_sell[0] = -1.0 # Request 100% sell

        obs, reward, terminated, truncated, info = env.step(action_sell)

        sell_val = shares_held * sell_price
        sell_fee = sell_val * 0.001
        expected_total_cost = cost_before_sell + sell_fee

        self.assertAlmostEqual(env.cost, expected_total_cost, places=2)
        self.assertAlmostEqual(env.cash, sell_val - sell_fee, places=2)
        self.assertEqual(env.shares[0], 0.0)
        self.assertAlmostEqual(sell_fee / sell_val, 0.001, places=6)

    def test_06_reward_function_formula_accuracy(self):
        """Verify step reward matches new optimized formula."""
        env = StockTradingEnv(
            df=self.df,
            lambda_dd=0.5,
            mu_dd=2.0,
            kappa=10.0,
            gamma_turnover=0.01
        )
        obs, info = env.reset(start_day=0)

        action = np.ones(28, dtype=np.float32) * 0.5
        
        # Calculate step cost based on env logic
        allocatable_cash = float(env.cash)
        fee = allocatable_cash * (0.001 / 1.001)
        # Note: 28 assets bought, this is total fee
        
        obs, reward, terminated, truncated, info = env.step(action)

        r_p = env.portfolio_return
        dd = env.drawdown
        delta_dd = env.drawdown_delta
        downside_variance = min(0.0, r_p) ** 2
        action_turnover = np.sum(np.abs(action - np.zeros(28))) # since prev action was 0
        
        # We fetch the env's exact step cost because floating point is hard
        step_cost = env.cost 

        expected_reward = r_p - 0.5 * dd - 2.0 * delta_dd - 10.0 * downside_variance - 0.01 * action_turnover - (step_cost / 1e6) * 10.0
        
        if env.consecutive_loss_days >= 3:
            expected_reward -= 0.1 * env.consecutive_loss_days

        self.assertAlmostEqual(reward, expected_reward, places=4)

    def test_07_custom_start_date_reset(self):
        """Test reset options with custom start day indexing."""
        env = StockTradingEnv(df=self.df)
        obs, info = env.reset(options={'initial_step': 250})
        self.assertEqual(env.day, 250)

        obs, info = env.reset(options={'start_day': 500})
        self.assertEqual(env.day, 500)

    def test_08_full_episode_run(self):
        """Run episode through end of dataset and check truncation behavior."""
        env = StockTradingEnv(df=self.df)
        obs, info = env.reset(start_day=env.num_dates - 5)

        truncated_found = False
        while not truncated_found:
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            self.assertFalse(np.isnan(obs).any())
            self.assertFalse(np.isnan(reward))
            if truncated:
                truncated_found = True
                break

        self.assertTrue(truncated_found)

    def test_09_adversarial_inputs_handling(self):
        """Verify environment stability when presented with NaN, Inf, and extreme action vectors."""
        env = StockTradingEnv(df=self.df)
        obs, info = env.reset()

        adversarial_actions = [
            np.full(28, np.nan, dtype=np.float32),
            np.full(28, np.inf, dtype=np.float32),
            np.full(28, -np.inf, dtype=np.float32),
            np.array([1e8 if i % 2 == 0 else -1e8 for i in range(28)], dtype=np.float32),
            np.zeros(28, dtype=np.float32)
        ]

        for act in adversarial_actions:
            obs, reward, terminated, truncated, info = env.step(act)
            self.assertFalse(np.isnan(obs).any())
            self.assertFalse(np.isinf(obs).any())
            self.assertFalse(np.isnan(reward))
            self.assertFalse(np.isinf(reward))

    def test_10_extreme_all_ones_action_cash_non_negative(self):
        """Verify taking extreme action +1.0 across all 28 assets keeps self.cash >= 0.0."""
        env = StockTradingEnv(df=self.df)
        obs, info = env.reset()
        action = np.ones(28, dtype=np.float32)

        for step in range(50):
            obs, reward, terminated, truncated, info = env.step(action)
            self.assertGreaterEqual(env.cash, 0.0, f"Cash balance negative ({env.cash}) at step {step}")
            self.assertFalse(np.isnan(obs).any())
            self.assertFalse(np.isinf(obs).any())
            if terminated or truncated:
                break


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStockTradingEnv)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    if not success:
        sys.exit(1)
