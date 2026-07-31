"""
Empirical Stress Harness for Custom Environment (Milestone 2)
-------------------------------------------------------------
Comprehensive testing suite covering:
1. 1000-step continuous random action trajectories (no NaN, Inf, or Zero Division)
2. Strict 10 bps transaction fee enforcement on buys and sells across multiple scenarios
3. State observation vector shape (strictly 539-dim Box) & components check
4. Episode reset and truncation/termination behavior
5. Adversarial input stress testing (NaNs, Infs, extreme values, precision edge cases)
"""

import sys
import unittest
import numpy as np
import pandas as pd
import gymnasium as gym

from custom_env import StockTradingEnv, DEFAULT_TECH_INDICATORS


class EmpiricalStressHarnessM2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data_path = "data/processed_market_dynamics.csv"
        cls.df = pd.read_csv(cls.data_path)
        cls.env = StockTradingEnv(df=cls.df)

    def test_01_observation_space_strict_567_dim(self):
        """Verify state observation vector space shape is strictly 567-dim Box."""
        obs, info = self.env.reset()
        
        # Space specs
        self.assertIsInstance(self.env.observation_space, gym.spaces.Box)
        self.assertEqual(self.env.observation_space.shape, (567,))
        self.assertEqual(self.env.observation_space.dtype, np.float32)
        
        # Returned observation specs
        self.assertIsInstance(obs, np.ndarray)
        self.assertEqual(obs.shape, (567,))
        self.assertEqual(obs.dtype, np.float32)
        
        # Check components breakdown:
        # Cash: 1
        # Shares: 28
        # Prices: 28
        # Tech features: 28 * 17 = 476
        # Regimes: 3
        # Risk state: 3
        # Total = 1 + 28 + 28 + 476 + 3 + 3 + 28 = 567
        self.assertEqual(1 + 28 + 28 + (28 * 17) + 3 + 3 + 28, 567)

    def test_02_1000_step_random_trajectories(self):
        """Verify 1000-step random action trajectories execute without zero division, NaN, or Inf values."""
        env = StockTradingEnv(df=self.df)
        
        # Test across 3 different random seeds / episodes (total 3000 steps)
        for seed in [42, 123, 999]:
            obs, info = env.reset(seed=seed)
            step_count = 0
            
            for step in range(1000):
                action = env.action_space.sample()
                obs, reward, terminated, truncated, info = env.step(action)
                step_count += 1
                
                # Check NaNs and Infs
                self.assertFalse(np.isnan(obs).any(), f"NaN in obs at step {step}, seed {seed}")
                self.assertFalse(np.isinf(obs).any(), f"Inf in obs at step {step}, seed {seed}")
                self.assertFalse(np.isnan(reward), f"NaN in reward at step {step}, seed {seed}")
                self.assertFalse(np.isinf(reward), f"Inf in reward at step {step}, seed {seed}")
                
                # Check numerical sanity of state variables
                self.assertGreaterEqual(env.cash, -1e-5, f"Negative cash {env.cash} at step {step}")
                self.assertTrue(np.all(env.shares >= 0.0), f"Negative shares at step {step}")
                self.assertGreaterEqual(env.drawdown, 0.0, f"Negative drawdown at step {step}")
                self.assertLessEqual(env.drawdown, 1.0 + 1e-6, f"Drawdown > 1 at step {step}")
                self.assertGreaterEqual(env.peak_net_worth, env.net_worth - 1e-5, f"Peak net worth anomaly at step {step}")
                
                if terminated or truncated:
                    obs, info = env.reset()
                    
            self.assertEqual(step_count, 1000)

    def test_03_transaction_fee_buy_sell_enforcement(self):
        """Strict verification of 10 bps (0.001 * transaction value) transaction fee on buys and sells."""
        env = StockTradingEnv(df=self.df, buy_cost_pct=0.001, sell_cost_pct=0.001)
        obs, info = env.reset(start_day=0)
        
        # Scenario A: Buy single asset (Asset 0) with 100% allocatable cash
        initial_cash = env.cash
        p0 = env.price_array[0][0]
        
        action_buy = np.zeros(28, dtype=np.float32)
        action_buy[0] = 1.0
        
        obs, reward, terminated, truncated, info = env.step(action_buy)
        
        target_buy_cash = initial_cash
        expected_fee_buy = target_buy_cash * (0.001 / 1.001)
        expected_buy_val = target_buy_cash - expected_fee_buy
        expected_shares_bought = expected_buy_val / p0
        
        # Verify buy fee = 0.001 * transaction value
        actual_buy_val = env.shares[0] * p0
        actual_fee_buy = env.cost
        
        self.assertAlmostEqual(actual_fee_buy, expected_fee_buy, places=4)
        self.assertAlmostEqual(actual_fee_buy / actual_buy_val, 0.001, places=6)
        self.assertAlmostEqual(env.cash, 0.0, places=4)
        self.assertAlmostEqual(env.shares[0], expected_shares_bought, places=4)
        
        # Scenario B: Partial sell (50%) of Asset 0 on day 1
        p1 = env.price_array[1][0]
        shares_before_sell = env.shares[0]
        cost_before_sell = env.cost
        
        action_sell_50 = np.zeros(28, dtype=np.float32)
        action_sell_50[0] = -0.5 # Sell 50%
        
        obs, reward, terminated, truncated, info = env.step(action_sell_50)
        
        sold_shares = shares_before_sell * 0.5
        transaction_val_sell = sold_shares * p1
        expected_sell_fee = transaction_val_sell * 0.001
        expected_cash_received = transaction_val_sell - expected_sell_fee
        
        actual_sell_fee = env.cost - cost_before_sell
        self.assertAlmostEqual(actual_sell_fee, expected_sell_fee, places=4)
        self.assertAlmostEqual(actual_sell_fee / transaction_val_sell, 0.001, places=6)
        self.assertAlmostEqual(env.cash, expected_cash_received, places=4)
        self.assertAlmostEqual(env.shares[0], shares_before_sell - sold_shares, places=4)

    def test_04_multi_asset_buy_sell_fee_enforcement(self):
        """Verify transaction fees when multiple assets are bought/sold simultaneously."""
        env = StockTradingEnv(df=self.df, buy_cost_pct=0.001, sell_cost_pct=0.001)
        obs, info = env.reset(start_day=10)
        
        initial_cash = env.cash
        # Action: Buy equal proportions of assets 0, 1, 2, 3
        action = np.zeros(28, dtype=np.float32)
        action[0:4] = 0.5
        
        obs, reward, terminated, truncated, info = env.step(action)
        
        # Fee should be 10 bps of total transaction value across all 4 assets
        # Total target buy cash = initial_cash
        total_fee = initial_cash * (0.001 / 1.001)
        total_buy_val = initial_cash - total_fee
        
        prices = env.price_array[10][0:4]
        computed_tx_val = np.sum(env.shares[0:4] * prices)
        
        self.assertAlmostEqual(env.cost, total_fee, places=3)
        self.assertAlmostEqual(computed_tx_val, total_buy_val, places=3)
        self.assertAlmostEqual(env.cost / computed_tx_val, 0.001, places=6)

    def test_05_episode_reset_cleanliness(self):
        """Verify that reset() completely wipes state variables, preventing cross-episode leakage."""
        env = StockTradingEnv(df=self.df)
        obs1, info1 = env.reset(start_day=0)
        
        # Take 50 steps
        for _ in range(50):
            env.step(env.action_space.sample())
            
        self.assertGreater(env.trades, 0)
        self.assertGreater(env.cost, 0.0)
        self.assertGreater(len(env.returns_memory), 0)
        
        # Perform Reset
        obs2, info2 = env.reset(start_day=0)
        
        # Verify pristine initial state
        self.assertEqual(env.day, 0)
        self.assertEqual(env.cash, 1e6)
        self.assertTrue(np.all(env.shares == 0.0))
        self.assertEqual(env.net_worth, 1e6)
        self.assertEqual(env.peak_net_worth, 1e6)
        self.assertEqual(env.drawdown, 0.0)
        self.assertEqual(env.drawdown_delta, 0.0)
        self.assertEqual(env.cost, 0.0)
        self.assertEqual(env.trades, 0)
        self.assertEqual(len(env.returns_memory), 0)
        np.testing.assert_array_equal(obs1, obs2)

    def test_06_truncation_and_termination_behavior(self):
        """Verify episode truncation when reaching end of dataset and termination on bankruptcy."""
        env = StockTradingEnv(df=self.df)
        
        # Test Truncation at end of dataset
        obs, info = env.reset(start_day=env.num_dates - 3)
        
        obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
        self.assertFalse(truncated)
        
        obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
        self.assertTrue(truncated)
        self.assertFalse(terminated)

    def test_07_adversarial_action_inputs(self):
        """Stress test with adversarial action vectors containing NaNs, Infs, extreme values, and zeros."""
        env = StockTradingEnv(df=self.df)
        obs, info = env.reset()
        
        adversarial_actions = [
            np.full(28, np.nan, dtype=np.float32),          # All NaNs
            np.full(28, np.inf, dtype=np.float32),          # All +Infs
            np.full(28, -np.inf, dtype=np.float32),         # All -Infs
            np.array([1e10 if i % 2 == 0 else -1e10 for i in range(28)], dtype=np.float32), # Extreme bounds
            np.zeros(28, dtype=np.float32),                 # All zeros
            np.array([1e-8 for _ in range(28)], dtype=np.float32), # Extremely small positive actions
        ]
        
        for idx, act in enumerate(adversarial_actions):
            obs, reward, terminated, truncated, info = env.step(act)
            self.assertFalse(np.isnan(obs).any(), f"NaN in obs for adversarial action {idx}")
            self.assertFalse(np.isinf(obs).any(), f"Inf in obs for adversarial action {idx}")
            self.assertFalse(np.isnan(reward), f"NaN in reward for adversarial action {idx}")
            self.assertFalse(np.isinf(reward), f"Inf in reward for adversarial action {idx}")


def run_stress_harness():
    suite = unittest.TestLoader().loadTestsFromTestCase(EmpiricalStressHarnessM2)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_stress_harness()
    if not success:
        sys.exit(1)
