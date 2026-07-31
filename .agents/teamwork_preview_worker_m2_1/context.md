# Worker 1 Scope — Milestone 2 Dependency & Code Fixes
Working Directory: f:\SURE Trust\Capstone Project\.agents\teamwork_preview_worker_m2_1
Target Repo: f:\SURE Trust\Capstone Project\RL_Paper_Trading_Deployment

Tasks:
1. Update `RL_Paper_Trading_Deployment/requirements-heavy.txt`:
   - Change `numpy==2.4.0` -> `numpy>=1.26.4,<2.0.0`
   - Change `pandas==2.3.3` -> `pandas>=2.2.0,<2.3.0`
   - Add `requests>=2.31.0`
2. Update `RL_Paper_Trading_Deployment/requirements.txt`:
   - Consolidate required dependencies (`numpy`, `pandas`, `yfinance`, `arch`, `hmmlearn`, `scikit-learn`, `stable-baselines3`, `supabase`, `python-dotenv`, `requests`, `streamlit`, `plotly`).
3. Update `RL_Paper_Trading_Deployment/trade_executor.py`:
   - Remove lines 20-27 (`sys.modules['numpy._core'] = numpy.core`).
4. Ensure artifact paths:
   - Copy `optimal_trading_model.zip` into `RL_Paper_Trading_Deployment/optimal_trading_model.zip`.
   - Ensure `data/processed_market_dynamics.csv` exists in `RL_Paper_Trading_Deployment/data/processed_market_dynamics.csv`.
5. Update `.github/workflows/daily_trading.yml`:
   - Add `cache-dependency-path: 'RL_Paper_Trading_Deployment/requirements-heavy.txt'` under `actions/setup-python@v5`.
   - Add artifact upload step for `RL_Paper_Trading_Deployment/logs/paper_trade_log.csv`.
6. Verify and commit:
   - Run tests or import check locally.
   - Commit and push changes to `main` branch.
