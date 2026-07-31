"""
Optimized CPU Model Training & Model Saving Pipeline (Milestone 3)
------------------------------------------------------------------
Trains an optimized PPO Reinforcement Learning agent on the custom Gymnasium
stock trading environment (StockTradingEnv) using engineered market dynamics features.

Configurations & Requirements:
- CPU-only execution explicitly forced via Stable-Baselines3 `device='cpu'`.
- Chronological train/validation data split:
    * Training Set: 2009-01-01 to 2015-12-31
    * Validation/Testing Set: 2016-01-01 to 2020-05-08
- Hyperparameters: learning_rate=3e-4, n_steps=2048, batch_size=64, n_epochs=10,
                   gamma=0.99, ent_coef=0.005, clip_range=0.2.
- Artifact Saving:
    * Workspace root: optimal_trading_model.zip
    * trained_models/: best_model.zip & ppo_stock_trading_final.zip
"""

import os
import sys
import shutil
import time
import logging
import numpy as np
import pandas as pd
import gymnasium as gym

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import EvalCallback

from custom_env import StockTradingEnv
import data_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TrainOptimized")


def load_or_generate_dataset(data_path: str) -> pd.DataFrame:
    """
    Loads processed_market_dynamics.csv. If missing, runs data_pipeline to generate it.
    """
    if not os.path.exists(data_path):
        logger.info(f"Dataset not found at {data_path}. Running data pipeline...")
        source_dir = r"f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading"
        data_pipeline.run_pipeline(source_dir, data_path)
    
    logger.info(f"Loading dataset from: {data_path}")
    df = pd.read_csv(data_path)
    df['date'] = df['date'].astype(str)
    return df


def split_data_chronologically(df: pd.DataFrame):
    """
    Splits dataset into chronological train and validation sets:
    - Train: 2009-01-01 to 2015-12-31
    - Val:   2016-01-01 to 2020-05-08
    """
    train_df = df[(df['date'] >= '2009-01-01') & (df['date'] <= '2015-12-31')].reset_index(drop=True)
    val_df = df[(df['date'] >= '2016-01-01') & (df['date'] <= '2020-05-08')].reset_index(drop=True)

    logger.info("--- Data Split Summary ---")
    logger.info(f"Training Set:   {train_df['date'].min()} to {train_df['date'].max()} | {train_df['date'].nunique()} dates | {len(train_df)} rows")
    logger.info(f"Validation Set: {val_df['date'].min()} to {val_df['date'].max()} | {val_df['date'].nunique()} dates | {len(val_df)} rows")
    logger.info("--------------------------")

    return train_df, val_df


def evaluate_agent_on_env(model, df_eval: pd.DataFrame, eval_name: str = "Validation"):
    """
    Evaluates trained policy deterministically on a specific dataset split and prints summary statistics.
    """
    eval_env = StockTradingEnv(df=df_eval)
    obs, info = eval_env.reset(seed=42)
    done = False
    
    start_time = time.time()
    step_count = 0
    
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = eval_env.step(action)
        step_count += 1
        done = terminated or truncated

    elapsed = time.time() - start_time
    init_worth = eval_env.initial_amount
    final_worth = info.get('net_worth', eval_env.net_worth)
    cum_return = ((final_worth - init_worth) / init_worth) * 100.0
    max_dd = info.get('drawdown', eval_env.drawdown) * 100.0
    trades = info.get('trades', eval_env.trades)

    logger.info(f"=== Performance Evaluation ({eval_name}) ===")
    logger.info(f"Evaluation Steps:      {step_count}")
    logger.info(f"Initial Portfolio:     ${init_worth:,.2f}")
    logger.info(f"Final Portfolio Value: ${final_worth:,.2f}")
    logger.info(f"Cumulative Return:     {cum_return:.2f}%")
    logger.info(f"Max Drawdown:          {max_dd:.2f}%")
    logger.info(f"Total Trades Executed: {trades}")
    logger.info(f"Evaluation Duration:   {elapsed:.2f}s")
    logger.info("=========================================")

    return {
        "final_worth": final_worth,
        "cum_return": cum_return,
        "max_dd": max_dd,
        "trades": trades
    }


def main():
    start_train_time = time.time()
    logger.info("Initializing CPU PPO Model Training Pipeline (Milestone 3)...")

    # 1. Paths and Directories
    data_path = os.path.join("data", "processed_market_dynamics.csv")
    trained_models_dir = "trained_models"
    os.makedirs(trained_models_dir, exist_ok=True)
    
    best_model_path_in_dir = os.path.join(trained_models_dir, "best_model.zip")
    final_model_path_in_dir = os.path.join(trained_models_dir, "ppo_stock_trading_final.zip")
    root_optimal_model_path = "optimal_trading_model.zip"

    # 2. Data Integration
    full_df = load_or_generate_dataset(data_path)
    train_df, val_df = split_data_chronologically(full_df)

    # 3. Vectorized Environment Creation
    logger.info("Creating vectorized Gymnasium trading environments...")
    train_env = DummyVecEnv([lambda: StockTradingEnv(df=train_df)])
    val_env = DummyVecEnv([lambda: StockTradingEnv(df=val_df)])

    # 4. SB3 PPO CPU Model Configuration
    # Explicitly force CPU training execution (`device='cpu'`)
    hyperparams = {
        "policy": "MlpPolicy",
        "learning_rate": 3e-4,
        "n_steps": 2048,
        "batch_size": 64,
        "n_epochs": 10,
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "ent_coef": 0.005,
        "clip_range": 0.2,
        "max_grad_norm": 0.5,
        "verbose": 1,
        "device": "cpu",
        "seed": 42
    }
    
    logger.info(f"Configuring PPO Agent with hyperparameters:\n{hyperparams}")
    model = PPO(env=train_env, **hyperparams)

    # 5. Model Checkpointing & Callback Setup
    eval_callback = EvalCallback(
        val_env,
        best_model_save_path=trained_models_dir,
        log_path=os.path.join(trained_models_dir, "logs"),
        eval_freq=2048,
        deterministic=True,
        render=False,
        verbose=1
    )

    # 6. Model Training Execution
    TOTAL_TIMESTEPS = 50_000
    logger.info(f"Starting CPU training execution for {TOTAL_TIMESTEPS:,} timesteps on device '{model.device}'...")
    
    model.learn(total_timesteps=TOTAL_TIMESTEPS, callback=eval_callback)
    
    total_duration = time.time() - start_train_time
    logger.info(f"Training completed successfully in {total_duration:.2f} seconds ({total_duration/60.0:.2f} minutes).")

    # 7. Save Final Model Artifacts
    logger.info(f"Saving final model to: {final_model_path_in_dir}")
    model.save(final_model_path_in_dir)

    # Ensure best_model.zip exists in trained_models/
    if not os.path.exists(best_model_path_in_dir):
        logger.info(f"Best model artifact not generated by callback; saving current model to {best_model_path_in_dir}")
        model.save(best_model_path_in_dir[:-4]) # SB3 appends .zip

    # Save artifact optimal_trading_model.zip in workspace root
    if os.path.exists(best_model_path_in_dir):
        logger.info(f"Copying best model from {best_model_path_in_dir} to workspace root: {root_optimal_model_path}")
        shutil.copyfile(best_model_path_in_dir, root_optimal_model_path)
    else:
        logger.info(f"Saving optimal model directly to workspace root: {root_optimal_model_path}")
        model.save("optimal_trading_model")

    # 8. Artifact Verification
    assert os.path.exists(root_optimal_model_path), f"Failed to create {root_optimal_model_path}"
    assert os.path.exists(best_model_path_in_dir), f"Failed to create {best_model_path_in_dir}"
    
    root_size = os.path.getsize(root_optimal_model_path)
    best_size = os.path.getsize(best_model_path_in_dir)
    logger.info(f"Verified artifact root: {root_optimal_model_path} ({root_size / 1024:.1f} KB)")
    logger.info(f"Verified artifact path: {best_model_path_in_dir} ({best_size / 1024:.1f} KB)")

    # 9. Verify Saved Model Reloading & Validation Evaluation
    logger.info("Verifying saved model by reloading from root artifact optimal_trading_model.zip...")
    reloaded_model = PPO.load(root_optimal_model_path, device="cpu")
    val_results = evaluate_agent_on_env(reloaded_model, val_df, eval_name="Out-of-Sample Validation (2016-2020)")

    logger.info("Pipeline execution completed with exit code 0.")
    sys.exit(0)


if __name__ == "__main__":
    main()
