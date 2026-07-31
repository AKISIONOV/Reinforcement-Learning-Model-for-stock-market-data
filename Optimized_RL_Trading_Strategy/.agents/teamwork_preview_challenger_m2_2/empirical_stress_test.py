"""
Empirical Stress Testing & Mathematical Verification Suite for custom_env.py
Milestone 2 - Challenger 2
"""

import unittest
import numpy as np
import pandas as pd
import sys
import os

# Add parent directory to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_env import StockTradingEnv


class EmpiricalStressTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data_path = "data/processed_market_dynamics.csv"
        cls.df = pd.read_csv(cls.data_path)

    def test_01_drawdown_math_and_delta(self):
        """Verify Drawdown DD_t = (Peak_t - V_t) / Peak_t and Delta DD_t step-by-step math."""
        env = StockTradingEnv(df=self.df, lambda_dd=1.0, mu_dd=2.0, theta=0.0)
        obs, info = env.reset(start_day=0)

        self.assertEqual(env.peak_net_worth, 1e6)
        self.assertEqual(env.drawdown, 0.0)
        self.assertEqual(env.drawdown_delta, 0.0)

        peak = 1e6
        prev_dd = 0.0

        for step in range(50):
            action = np.ones(28, dtype=np.float32) * (0.2 if step % 2 == 0 else -0.2)
            obs, reward, terminated, truncated, info = env.step(action)

            v_t = env.net_worth
            peak = max(peak, v_t)
            expected_dd = max(0.0, (peak - v_t) / (peak + 1e-8))
            expected_delta_dd = max(0.0, expected_dd - prev_dd)

            self.assertAlmostEqual(env.peak_net_worth, peak, places=4,
                                   msg=f"Peak mismatch at step {step}")
            self.assertAlmostEqual(env.drawdown, expected_dd, places=5,
                                   msg=f"Drawdown mismatch at step {step}")
            self.assertAlmostEqual(env.drawdown_delta, expected_delta_dd, places=5,
                                   msg=f"Delta drawdown mismatch at step {step}")

            # Verify risk state in observation vector
            self.assertAlmostEqual(obs[-3], expected_dd, places=4)
            self.assertAlmostEqual(obs[-2], peak / 1e6, places=4)

            prev_dd = expected_dd

    def test_02_regime_state_2_penalty_firing(self):
        """Verify Bearish High-Vol regime downside volatility penalty fires iff argmax(regime_probs) == 2."""
        theta = 0.5
        env = StockTradingEnv(df=self.df, lambda_dd=0.0, mu_dd=0.0, theta=theta)
        obs, info = env.reset(start_day=0)

        penalties_fired = 0
        penalties_zero = 0

        for step in range(200):
            # Take oscillating action to generate negative returns and non-zero downside vol
            action = np.ones(28, dtype=np.float32) * (0.8 if step % 2 == 0 else -0.8)
            obs, reward, terminated, truncated, info = env.step(action)

            r_p = env.portfolio_return
            recent_ret = np.array(env.returns_memory, dtype=np.float32)
            neg_ret = np.minimum(0.0, recent_ret)
            downside_vol = float(np.sqrt(np.mean(neg_ret ** 2))) if len(neg_ret) > 0 else 0.0

            regime_probs = env.regime_array[env.day]
            is_bearish_high_vol = 1.0 if np.argmax(regime_probs) == 2 else 0.0

            expected_penalty = theta * downside_vol * is_bearish_high_vol
            expected_reward = r_p - expected_penalty

            self.assertAlmostEqual(reward, expected_reward, places=5,
                                   msg=f"Reward mismatch at step {step}")

            if is_bearish_high_vol == 1.0 and downside_vol > 0:
                penalties_fired += 1
                self.assertLess(reward, r_p, msg="Penalty should decrease reward when regime 2 dominates")
            else:
                penalties_zero += 1
                self.assertAlmostEqual(reward, r_p, places=5, msg="Penalty should be 0 when regime != 2 or downside_vol == 0")

        print(f"\n[Regime Test] Penalties fired: {penalties_fired}, Penalties zero: {penalties_zero}")

    def test_03_extreme_action_buy_cash_leak_demonstration(self):
        """Empirically test whether +1.0 all-buy action drives cash negative due to float32 weight sum overflow."""
        env = StockTradingEnv(df=self.df)
        obs, info = env.reset(start_day=0)

        action = np.ones(28, dtype=np.float32) # +1.0 all buy
        obs, reward, terminated, truncated, info = env.step(action)

        print(f"\n[Cash Negative Bug Check] Initial Cash: 1,000,000.0 | Post-Buy Cash: {env.cash}")
        
        # Verify that cash balance went negative
        is_cash_negative = env.cash < 0.0
        if is_cash_negative:
            print(f"[BUG CONFIRMED] Cash balance dropped below 0.0: {env.cash}")
        
        # Document bug mathematically
        self.assertTrue(is_cash_negative, "Expected cash balance to go negative due to float32 allocation weight bug in custom_env.py")

    def test_04_extreme_action_all_sell(self):
        """Extreme action test: -1.0 all sell every step for 500 steps."""
        env = StockTradingEnv(df=self.df)
        obs, info = env.reset(start_day=0)

        # First step buy to get shares
        env.step(np.ones(28, dtype=np.float32) * 0.5)

        for step in range(500):
            action = -np.ones(28, dtype=np.float32) # -1.0 all sell
            obs, reward, terminated, truncated, info = env.step(action)

            # Shares non-negativity check
            self.assertTrue(np.all(env.shares >= 0.0), f"Shares negative at step {step}")
            self.assertGreaterEqual(env.cash, 0.0, f"Cash negative ({env.cash}) at step {step}")

            # Observation safety check
            self.assertFalse(np.isnan(obs).any(), f"NaN in obs at step {step}")
            self.assertFalse(np.isinf(obs).any(), f"Inf in obs at step {step}")
            self.assertFalse(np.isnan(reward), f"NaN in reward at step {step}")

            if terminated or truncated:
                break

    def test_05_extreme_action_oscillating(self):
        """Extreme action test: Alternating +1.0 (all buy) and -1.0 (all sell) for 500 steps."""
        env = StockTradingEnv(df=self.df)
        obs, info = env.reset(start_day=0)

        nan_or_inf_found = False

        for step in range(500):
            action = np.ones(28, dtype=np.float32) if step % 2 == 0 else -np.ones(28, dtype=np.float32)
            obs, reward, terminated, truncated, info = env.step(action)

            if np.isnan(obs).any() or np.isinf(obs).any() or np.isnan(reward) or np.isinf(reward):
                nan_or_inf_found = True

            if terminated or truncated:
                break

        self.assertFalse(nan_or_inf_found, "Oscillating extreme actions produced NaN or Inf")

    def test_06_invalid_and_out_of_bounds_actions(self):
        """Stress test with NaN, Inf, -Inf, huge positive/negative actions."""
        env = StockTradingEnv(df=self.df)
        obs, info = env.reset(start_day=0)

        invalid_actions = [
            np.full(28, np.nan, dtype=np.float32),
            np.full(28, np.inf, dtype=np.float32),
            np.full(28, -np.inf, dtype=np.float32),
            np.full(28, 1e12, dtype=np.float32),
            np.full(28, -1e12, dtype=np.float32),
            np.array([np.nan if i % 2 == 0 else np.inf for i in range(28)], dtype=np.float32)
        ]

        for idx, act in enumerate(invalid_actions):
            obs, reward, terminated, truncated, info = env.step(act)

            self.assertFalse(np.isnan(obs).any(), f"NaN in obs for invalid action index {idx}")
            self.assertFalse(np.isinf(obs).any(), f"Inf in obs for invalid action index {idx}")
            self.assertFalse(np.isnan(reward), f"NaN in reward for invalid action index {idx}")
            self.assertFalse(np.isinf(reward), f"Inf in reward for invalid action index {idx}")

    def test_07_downside_volatility_calculation_accuracy(self):
        """Verify rolling 21-day downside volatility calculation logic."""
        env = StockTradingEnv(df=self.df)
        obs, info = env.reset(start_day=0)

        # Run 30 steps
        for step in range(30):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)

        memory = env.returns_memory
        self.assertLessEqual(len(memory), 21)

        recent_ret = np.array(memory, dtype=np.float32)
        neg_ret = np.minimum(0.0, recent_ret)
        expected_vol = float(np.sqrt(np.mean(neg_ret ** 2))) if len(neg_ret) > 0 else 0.0

        obs_downside_vol = obs[-1]
        self.assertAlmostEqual(obs_downside_vol, expected_vol, places=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
