## 2026-07-31T11:44:57Z
<USER_REQUEST>
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You are a Worker subagent (worker_m3).
Working directory: f:/SURE Trust/Capstone Project/RL_Paper_Trading_Deployment/.agents/worker_m3
Project scope doc: f:/SURE Trust/Capstone Project/RL_Paper_Trading_Deployment/.agents/orchestrator/PROJECT.md

Your Task:
Create `f:/SURE Trust/Capstone Project/RL_Paper_Trading_Deployment/dashboard.py` using Streamlit:
- Imports: `streamlit`, `pandas`, `numpy`, `plotly` (or matplotlib/altair fallback if plotly is unavailable).
- Data Loading:
  - Reads `f:/SURE Trust/Capstone Project/RL_Paper_Trading_Deployment/logs/paper_trade_log.csv`.
  - Handles missing CSV gracefully with a clear error/warning message instructing the user to run `trade_executor.py` first.
- Page Layout:
  - Title: "RL Paper Trading Dashboard"
  - Sidebar: Data refresh button, file path status, execution mode indicator (MOCK vs LIVE ALPACA), and strategy summary.
  - Header Metric Cards (`st.metric`):
    - Current Portfolio Net Worth ($) with dollar change
    - Total Return (%) with delta
    - Daily Return (%)
    - Current Market Regime (Bullish Low-Vol / Neutral / Bearish High-Vol)
    - Execution Mode (MOCK vs LIVE)
  - Interactive Tabs:
    1. **Tab 1: Portfolio Performance**:
       - Line chart of Portfolio Net Worth over time compared to Initial Capital ($1,000,000 baseline).
       - Bar chart of Daily Returns (%) with color coding (green for profit, red for loss).
       - Line chart of Drawdown Curve (%) over time.
    2. **Tab 2: Current Asset Allocations**:
       - Donut chart / Bar chart of latest asset weights across DJIA tickers + Cash.
       - Data table listing current holdings (Ticker, Action, Shares, Price, Trade Value, Weight %).
    3. **Tab 3: Market Regimes & Analytics**:
       - Distribution pie chart of time spent in each market regime (Bullish, Neutral, Bearish).
       - Regime-highlighted portfolio net worth trajectory chart.
    4. **Tab 4: Execution Logs & Exports**:
       - Interactive data table of all recorded trades (`BUY`, `SELL`, `SNAPSHOT`).
       - CSV download button for offline analysis.

Verification Requirement:
- Run a verification script (e.g. executing `python -c "import dashboard"` or running streamlit in headless mode `streamlit run dashboard.py --server.headless=true`) to confirm that `dashboard.py` imports, loads log CSV data, and renders without syntax or runtime errors.
- Document verification output in your handoff report.

Write handoff report to `f:/SURE Trust/Capstone Project/RL_Paper_Trading_Deployment/.agents/worker_m3/handoff.md` and notify parent via send_message when complete.
</USER_REQUEST>
