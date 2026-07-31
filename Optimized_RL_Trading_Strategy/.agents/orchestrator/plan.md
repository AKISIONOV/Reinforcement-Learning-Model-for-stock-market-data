# Orchestrator Plan

## Architectural Overview & Execution Strategy

We decompose the project into 4 core milestones + E2E packaging, following the **Project Orchestration Pattern**:

1. **Milestone 0: Codebase & Data Exploration [COMPLETE]**
   - Audited parent repository `Deep-Reinforcement-Learning-with-Stock-Trading`.
   - Identified 28 clean DJIA assets (excluding `UTX` empty file and `DOW` truncated file).
   - Identified parent code defects (cumulative profit non-stationary reward, 0 transaction fee, backtest env leak).

2. **Milestone 1: Data Engineering for Market Dynamics (R1) [COMPLETE & AUDITED CLEAN]**
   - Delivered `data_pipeline.py` and `data/processed_market_dynamics.csv` (79,380 rows x 29 columns).
   - Implemented volatility clustering (EWMA, Garman-Klass, GARCH, vol ratio), spoofing proxies (shadow ratios, VWAP distance, OFI, Corwin-Schultz spread), news shocks (return Z-score, jump indicator, volume spike index, joint shock), and 3-state HMM market regimes.
   - Verified CLEAN by Forensic Auditor (`a9f85dfb-614c-4287-8d7b-8f34e1b64356`).

3. **Milestone 2: Custom Gymnasium RL Environment Adaptation (R2) [COMPLETE & AUDITED CLEAN]**
   - Delivered `custom_env.py` and `test_custom_env.py`.
   - Gymnasium compliance: 539-dim observation space, 28-dim continuous action space, 10 bps fee enforcement, drawdown-penalized risk reward ($R_t = r_{p,t} - \lambda_{dd} DD_t - \mu_{dd} \Delta DD_t - \theta \cdot DownsideVol_t \cdot \mathbb{I}(\text{Regime}==2)$).
   - Hardened against float32 negative cash drift, all unit tests pass, verified CLEAN by Forensic Auditor (`b9469856-158a-4b68-b5b6-f2e00c964763`).

4. **Milestone 3: CPU Model Training & Saving (R3) [IN_PROGRESS / NEXT TO EXECUTE]**
   - Module: `train_optimized.py`.
   - Goal: Train PPO agent strictly on CPU (`device='cpu'`) using `custom_env.py` and `data/processed_market_dynamics.csv`.
   - Train on training slice (`2009-01-01` to `2015-12-31`), evaluate on validation/test slice, and save the best performing model to `optimal_trading_model.zip` (and `trained_models/`).
   - Standalone reproducible script execution without errors.

5. **Milestone 4: Packaging, Notebooks & Documentation (R3/Packaging) [TO EXECUTE AFTER M3]**
   - `evaluate.py`: Backtesting and evaluation utilities for calculating total return, Sharpe ratio, Sortino ratio, max drawdown, win rate.
   - `main.ipynb`: End-to-end reproducible Jupyter Notebook demonstrating dataset loading, feature engineering, environment creation, model evaluation/backtesting, and performance charts.
   - `summary_of_files.md`: Concise breakdown of all files created, modified, and used in the project.
   - `README.md`: Comprehensive documentation covering technical architecture, feature engineering rationale (volatility clustering, spoofing proxies, news shocks, HMM regimes), drawdown reward penalty formulation, installation, usage guide, and benchmark results.

## Verification & Gating Loop per Milestone
- **Worker**: Implements modules, runs builds/tests/scripts, documents commands & outputs.
- **Reviewer**: Inspects code quality, correctness, interface adherence.
- **Challenger**: Runs stress testing / empirical validation.
- **Auditor**: Performs static analysis, runtime verification, integrity audit.
