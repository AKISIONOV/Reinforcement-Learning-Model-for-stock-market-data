"""
Custom Gymnasium Stock Trading Environment (Milestone 3 Optimization)
---------------------------------------------------------
Adaptation of Gymnasium Env for multi-asset DJIA stock trading with
engineered market dynamics, global market regimes, transaction fees,
action smoothing, hard risk constraints, and drawdown/Sortino-penalized rewards.
"""

import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces

DEFAULT_TECH_INDICATORS = [
    'return', 'log_return', 'ewma_vol', 'volatility_ratio_5_21',
    'garman_klass_vol', 'garch_vol', 'shadow_upper', 'shadow_lower',
    'shadow_ratio', 'vwap', 'vwap_distance', 'order_flow_imbalance',
    'corwin_schultz_spread', 'return_shock_zscore', 'return_jump_indicator',
    'volume_spike_index', 'joint_vol_vol_shock'
]


class StockTradingEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        df: pd.DataFrame | str,
        stock_dim: int = 28,
        initial_amount: float = 1e6,
        buy_cost_pct: float = 0.001,
        sell_cost_pct: float = 0.001,
        reward_scaling: float = 1.0,
        lambda_dd: float = 0.5,
        mu_dd: float = 2.0,
        kappa: float = 10.0, # Downside variance multiplier
        gamma_turnover: float = 0.01, # Action smoothing multiplier
        tech_indicator_list: list = None,
        initial: bool = True,
        previous_state: list = None,
        start_day: int = 0
    ):
        super().__init__()

        if isinstance(df, str):
            df = pd.read_csv(df)

        self.df = df.copy()
        self.stock_dim = stock_dim
        self.initial_amount = float(initial_amount)
        self.buy_cost_pct = float(buy_cost_pct)
        self.sell_cost_pct = float(sell_cost_pct)
        self.reward_scaling = float(reward_scaling)
        self.lambda_dd = float(lambda_dd)
        self.mu_dd = float(mu_dd)
        self.kappa = float(kappa)
        self.gamma_turnover = float(gamma_turnover)
        self.start_day = int(start_day)
        self.initial = initial
        self.previous_state = previous_state

        if tech_indicator_list is None:
            self.tech_indicator_list = DEFAULT_TECH_INDICATORS.copy()
        else:
            self.tech_indicator_list = list(tech_indicator_list)

        self.num_features = len(self.tech_indicator_list)

        self.df['date'] = self.df['date'].astype(str)
        self.df = self.df.sort_values(['date', 'tic']).reset_index(drop=True)

        self.tickers = sorted(self.df['tic'].unique())
        if len(self.tickers) != self.stock_dim:
            self.stock_dim = len(self.tickers)

        self.dates = sorted(self.df['date'].unique())
        self.num_dates = len(self.dates)

        self._prepare_matrices()

        self.action_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(self.stock_dim,),
            dtype=np.float32
        )

        # Cash (1) + Shares (dim) + Prices (dim) + Features (dim * num_features) + Regimes (3) + Risk State (3) + Prev Actions (dim)
        obs_dim = 1 + self.stock_dim + self.stock_dim + (self.stock_dim * self.num_features) + 3 + 3 + self.stock_dim
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_dim,),
            dtype=np.float32
        )

        self.day = 0
        self.cash = self.initial_amount
        self.shares = np.zeros(self.stock_dim, dtype=np.float32)
        self.net_worth = self.initial_amount
        self.peak_net_worth = self.initial_amount
        self.drawdown = 0.0
        self.drawdown_delta = 0.0
        self.portfolio_return = 0.0
        self.returns_memory = []
        self.trades = 0
        self.cost = 0.0
        self.prev_actions = np.zeros(self.stock_dim, dtype=np.float32)
        self.consecutive_loss_days = 0

        self.reset(start_day=self.start_day)

    def _prepare_matrices(self):
        price_pivot = self.df.pivot(index='date', columns='tic', values='adj_close')
        price_pivot = price_pivot.ffill().bfill().fillna(1.0)
        self.price_array = price_pivot.values.astype(np.float32)

        tech_list = []
        for feat in self.tech_indicator_list:
            if feat in self.df.columns:
                p = self.df.pivot(index='date', columns='tic', values=feat).ffill().bfill().fillna(0.0)
            else:
                p = pd.DataFrame(0.0, index=self.dates, columns=self.tickers)
            tech_list.append(p.values)
        
        tech_stacked = np.stack(tech_list, axis=0)
        self.tech_array = np.transpose(tech_stacked, (1, 2, 0)).astype(np.float32)

        regime_cols = ['regime_state_0', 'regime_state_1', 'regime_state_2']
        for col in regime_cols:
            if col not in self.df.columns:
                self.df[col] = 1.0 / 3.0

        regime_df = self.df.groupby('date')[regime_cols].first().reindex(self.dates).ffill().bfill().fillna(1.0 / 3.0)
        self.regime_array = regime_df.values.astype(np.float32)

    def _get_observation(self, day: int) -> np.ndarray:
        day = min(day, self.num_dates - 1)
        cash_norm = np.array([self.cash / self.initial_amount], dtype=np.float32)
        shares_scaled = (self.shares * 1e-4).astype(np.float32)
        current_prices = self.price_array[day].astype(np.float32)
        tech_feats = self.tech_array[day].flatten().astype(np.float32)
        regime_probs = self.regime_array[day].astype(np.float32)

        if len(self.returns_memory) > 0:
            recent_ret = np.array(self.returns_memory, dtype=np.float32)
            neg_ret = np.minimum(0.0, recent_ret)
            downside_vol = float(np.sqrt(np.mean(neg_ret ** 2)))
        else:
            downside_vol = 0.0

        risk_state = np.array(
            [self.drawdown, self.peak_net_worth / self.initial_amount, downside_vol],
            dtype=np.float32
        )

        obs = np.hstack([
            cash_norm,
            shares_scaled,
            current_prices,
            tech_feats,
            regime_probs,
            risk_state,
            self.prev_actions
        ], dtype=np.float32)

        obs = np.nan_to_num(obs, nan=0.0, posinf=1e6, neginf=-1e6).astype(np.float32)
        return obs

    def reset(self, seed=None, options=None, start_day=None):
        super().reset(seed=seed)

        if options is not None:
            if 'initial_step' in options:
                start_day = options['initial_step']
            elif 'start_day' in options:
                start_day = options['start_day']

        if start_day is None:
            start_day = self.start_day

        self.day = max(0, min(int(start_day), self.num_dates - 1))
        self.cash = float(self.initial_amount)
        self.shares = np.zeros(self.stock_dim, dtype=np.float32)
        self.net_worth = float(self.initial_amount)
        self.peak_net_worth = float(self.initial_amount)
        self.drawdown = 0.0
        self.drawdown_delta = 0.0
        self.portfolio_return = 0.0
        self.returns_memory = []
        self.trades = 0
        self.cost = 0.0
        self.prev_actions = np.zeros(self.stock_dim, dtype=np.float32)
        self.consecutive_loss_days = 0

        obs = self._get_observation(self.day)
        info = {
            'net_worth': self.net_worth,
            'portfolio_return': 0.0,
            'drawdown': 0.0,
            'trades': 0
        }
        return obs, info

    def step(self, action):
        action = np.nan_to_num(action, nan=0.0, posinf=1.0, neginf=-1.0)
        action = np.clip(action, -1.0, 1.0).astype(np.float32)

        regime_probs = self.regime_array[self.day]
        is_bearish_high_vol = 1.0 if np.argmax(regime_probs) == 2 else 0.0

        # Hard Risk Constraints
        if self.portfolio_return < -0.05:
            action = -np.ones(self.stock_dim, dtype=np.float32) # Circuit breaker: Liquidate everything
        elif is_bearish_high_vol > 0:
            action = np.clip(action, -0.5, 0.5) # Force position limits during high vol

        action_turnover = np.sum(np.abs(action - self.prev_actions))
        self.prev_actions = action.copy()

        if self.day >= self.num_dates - 1:
            obs = self._get_observation(self.day)
            return obs, 0.0, True, False, {'net_worth': self.net_worth, 'portfolio_return': self.portfolio_return, 'drawdown': self.drawdown, 'trades': self.trades}

        current_prices = self.price_array[self.day]
        prev_net_worth = self.net_worth

        n_step_trades = 0
        step_cost = 0.0

        for i in range(self.stock_dim):
            if action[i] < 0 and self.shares[i] > 0:
                sell_ratio = min(1.0, abs(float(action[i])))
                sell_shares = self.shares[i] * sell_ratio
                if sell_shares > 1e-6:
                    sell_val = sell_shares * current_prices[i]
                    fee = sell_val * self.sell_cost_pct
                    self.cash += (sell_val - fee)
                    self.shares[i] -= sell_shares
                    self.cost += fee
                    step_cost += fee
                    n_step_trades += 1

        pos_mask = action > 0
        pos_sum = float(np.sum(action[pos_mask], dtype=np.float64))
        if pos_sum > 0 and self.cash > 0:
            allocatable_cash = float(self.cash)
            for i in range(self.stock_dim):
                if action[i] > 0 and self.cash > 0:
                    w = float(action[i]) / pos_sum
                    target_buy_cash = min(allocatable_cash * w, float(self.cash))
                    fee = target_buy_cash * (self.buy_cost_pct / (1.0 + self.buy_cost_pct))
                    buy_val = target_buy_cash - fee
                    buy_shares = buy_val / current_prices[i]
                    if buy_shares > 1e-6:
                        self.shares[i] += buy_shares
                        self.cash -= target_buy_cash
                        self.cost += fee
                        step_cost += fee
                        n_step_trades += 1

            self.cash = max(0.0, self.cash)

        self.trades += n_step_trades
        self.day += 1
        next_prices = self.price_array[self.day]

        self.net_worth = float(self.cash + np.sum(self.shares * next_prices))
        r_p = (self.net_worth - prev_net_worth) / (prev_net_worth + 1e-8)
        self.portfolio_return = r_p
        self.returns_memory.append(r_p)
        if len(self.returns_memory) > 21:
            self.returns_memory.pop(0)

        # Consecutive Losses
        if r_p < 0:
            self.consecutive_loss_days += 1
        else:
            self.consecutive_loss_days = 0

        prev_dd = self.drawdown
        self.peak_net_worth = max(self.peak_net_worth, self.net_worth)
        self.drawdown = max(0.0, (self.peak_net_worth - self.net_worth) / (self.peak_net_worth + 1e-8))
        delta_dd = max(0.0, self.drawdown - prev_dd)
        self.drawdown_delta = delta_dd

        downside_variance = min(0.0, r_p) ** 2

        # Drawdown/Sortino Penalized Reward Function with Action Smoothing and Fee penalties
        reward = (
            r_p
            - self.lambda_dd * self.drawdown
            - self.mu_dd * delta_dd
            - self.kappa * downside_variance
            - self.gamma_turnover * action_turnover
            - (step_cost / self.initial_amount) * 10.0
        ) * self.reward_scaling

        if self.consecutive_loss_days >= 3:
            reward -= 0.1 * self.consecutive_loss_days

        terminated = bool(self.net_worth <= 0 or np.isnan(self.net_worth))
        truncated = bool(self.day >= self.num_dates - 1)

        obs = self._get_observation(self.day)
        info = {
            'net_worth': self.net_worth,
            'portfolio_return': r_p,
            'drawdown': self.drawdown,
            'trades': n_step_trades
        }

        return obs, float(reward), terminated, truncated, info

    def render(self, mode="human"):
        print(f"Day: {self.day} | Date: {self.dates[self.day]} | Net Worth: ${self.net_worth:,.2f} | Drawdown: {self.drawdown:.4f}")
