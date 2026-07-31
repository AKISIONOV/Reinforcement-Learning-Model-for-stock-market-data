"""
RL Paper Trading Web Dashboard (dashboard.py)
---------------------------------------------
Streamlit web application for real-time visual tracking, performance analytics,
asset allocation, market regime breakdown, and execution trade logs of the
Reinforcement Learning Paper Trading System.
"""

import os
import io
import datetime
import numpy as np
import pandas as pd
import streamlit as st

# Optional Plotly imports with fallback flag
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Optional Supabase import
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

# -----------------------------------------------------------------------------
# 1. Page Configuration & Custom CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="RL Paper Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
INITIAL_CAPITAL = 1000000.0  # $1,000,000.00 baseline
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LOG_PATH = os.path.join(SCRIPT_DIR, "logs", "paper_trade_log.csv")

# Custom CSS for polished layout & card aesthetics
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 8px;
        padding: 12px 16px;
        border: 1px solid #E2E8F0;
    }
    .stMetric label {
        font-weight: 600 !important;
        color: #334155 !important;
    }
    div[data-testid="stSidebarUserContent"] {
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. Data Loader Function
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_trade_log(file_path: str):
    """
    Loads paper trading execution log from Supabase Cloud (if configured)
    with a graceful fallback to the local CSV file.
    Returns (DataFrame or None, error_message or None, source_str).
    """
    # 1. Try Supabase Cloud Database first
    if HAS_SUPABASE:
        try:
            # Check Streamlit Cloud Secrets or local .env
            sb_url = None
            sb_key = None
            
            # Use st.secrets if available (Streamlit Cloud)
            if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
                sb_url = st.secrets["SUPABASE_URL"]
                sb_key = st.secrets["SUPABASE_KEY"]
            else:
                # Fallback to local .env
                from dotenv import load_dotenv
                load_dotenv()
                sb_url = os.getenv("SUPABASE_URL")
                sb_key = os.getenv("SUPABASE_KEY")
                
            if sb_url and sb_key and not sb_url.startswith("YOUR_"):
                supabase: Client = create_client(sb_url, sb_key)
                response = supabase.table("trade_logs").select("*").execute()
                
                # If connected but table is empty
                if isinstance(response.data, list) and len(response.data) == 0:
                    return None, "Connected to Supabase Cloud, but the database is empty! Please run `trade_executor.py` locally to push the first trades.", "SUPABASE_CLOUD"
                
                # If connected and has data
                if response.data:
                    df = pd.DataFrame(response.data)
                    return df, None, "SUPABASE_CLOUD"
            else:
                print("Supabase URLs missing or are placeholder.")
        except Exception as e:
            print(f"Supabase connection warning: {e}")

    # 2. Fallback to Local CSV
    if not os.path.exists(file_path):
        return None, f"File not found at path: {file_path}", "LOCAL_CSV"
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return None, "Log file exists but contains no records.", "LOCAL_CSV"
        return df, None, "LOCAL_CSV"
    except Exception as e:
        return None, f"Failed to parse CSV log file: {str(e)}", "LOCAL_CSV"


# -----------------------------------------------------------------------------
# 3. Sidebar Setup
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ Dashboard Controls")

# File Path Configuration
log_path_input = st.sidebar.text_input(
    "CSV Log Path",
    value=DEFAULT_LOG_PATH,
    help="Absolute or relative path to logs/paper_trade_log.csv"
)

# Manual Data Refresh Button
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.rerun()

# Load Data
df, load_error, data_source = load_trade_log(log_path_input)

# Sidebar Status & Summary
if df is not None:
    source_icon = "☁️" if data_source == "SUPABASE_CLOUD" else "📁"
    st.sidebar.success(f"{source_icon} {data_source} ({len(df)} records)")
    
    # Execution Mode Indicator
    exec_mode = df['execution_mode'].iloc[-1] if 'execution_mode' in df.columns else "UNKNOWN"
    if "LIVE" in str(exec_mode).upper() or "ALPACA" in str(exec_mode).upper():
        st.sidebar.success(f"⚡ Execution Mode: **{exec_mode}**")
    else:
        st.sidebar.info(f"🧪 Execution Mode: **{exec_mode}**")
        
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Strategy Summary")
    st.sidebar.markdown("""
    - **RL Model**: Continuous PPO (SB3)
    - **Target Universe**: 28 DJIA Equities + Cash
    - **Observation State**: 567 Dimensions
    - **Regime Model**: 3-State Gaussian HMM
    - **Transaction Fee**: 10 bps (0.10%)
    - **Initial Capital**: $1,000,000.00
    """)
else:
    st.sidebar.error("❌ Log File Missing / Unreadable")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Strategy Summary")
    st.sidebar.markdown("""
    - **RL Model**: Continuous PPO (SB3)
    - **Target Universe**: 28 DJIA Equities + Cash
    - **Initial Capital**: $1,000,000.00
    """)

# -----------------------------------------------------------------------------
# 4. Missing File Graceful Fallback
# -----------------------------------------------------------------------------
if df is None:
    st.title("📈 RL Paper Trading Dashboard")
    st.error(f"⚠️ {load_error}")
    st.warning("""
    **Instructions to generate execution log data:**
    1. If using GitHub Actions, go to the Actions tab and manually run the **Daily Paper Trading Execution** workflow to push fresh data to Supabase.
    2. Alternatively, run the engine locally:
       ```bash
       python trade_executor.py
       ```
    """)
    st.info(f"Target file path being read: `{log_path_input}`")
    st.stop()


# -----------------------------------------------------------------------------
# 5. Data Preprocessing & Metric Calculations
# -----------------------------------------------------------------------------
# Standardize Date Column
if 'date' in df.columns:
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

# Filter snapshot rows for portfolio trajectory metrics
df_snapshots = df[df['action_type'] == 'SNAPSHOT'].copy()
if df_snapshots.empty:
    df_snapshots = df.drop_duplicates(subset=['date'], keep='last').copy()

# Sort snapshots chronologically
sort_cols = ['date']
if 'timestamp' in df_snapshots.columns:
    sort_cols.append('timestamp')
df_snapshots = df_snapshots.sort_values(by=sort_cols).reset_index(drop=True)

# Calculate Metric Card Values
latest_snap = df_snapshots.iloc[-1]
latest_net_worth = float(latest_snap['portfolio_net_worth'])
prev_net_worth = float(df_snapshots.iloc[-2]['portfolio_net_worth']) if len(df_snapshots) > 1 else INITIAL_CAPITAL

dollar_change = latest_net_worth - INITIAL_CAPITAL
total_return_pct = (dollar_change / INITIAL_CAPITAL) * 100.0

# Daily return conversion (handle ratio vs percentage gracefully)
raw_daily_ret = float(latest_snap.get('daily_return', 0.0))
daily_return_pct = raw_daily_ret * 100.0 if abs(raw_daily_ret) <= 1.0 else raw_daily_ret

if len(df_snapshots) > 1:
    prev_raw_daily = float(df_snapshots.iloc[-2].get('daily_return', 0.0))
    prev_daily_pct = prev_raw_daily * 100.0 if abs(prev_raw_daily) <= 1.0 else prev_raw_daily
    daily_ret_delta = daily_return_pct - prev_daily_pct
else:
    daily_ret_delta = daily_return_pct

curr_regime = str(latest_snap.get('market_regime', 'Neutral'))
curr_exec_mode = str(latest_snap.get('execution_mode', 'MOCK'))

# -----------------------------------------------------------------------------
# 6. Title & Header Metric Cards
# -----------------------------------------------------------------------------
st.title("📈 RL Paper Trading Dashboard")
st.markdown("Real-time visual performance tracking, asset allocation, market regime analytics, and trade execution logs.")

m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.metric(
        label="Portfolio Net Worth",
        value=f"${latest_net_worth:,.2f}",
        delta=f"{'+' if dollar_change >= 0 else ''}${dollar_change:,.2f}"
    )

with m2:
    st.metric(
        label="Total Return",
        value=f"{total_return_pct:+.2f}%",
        delta=f"{total_return_pct:+.2f}% vs Baseline"
    )

with m3:
    st.metric(
        label="Daily Return",
        value=f"{daily_return_pct:+.2f}%",
        delta=f"{daily_ret_delta:+.2f}% DoD" if len(df_snapshots) > 1 else None
    )

with m4:
    st.metric(
        label="Market Regime",
        value=curr_regime,
        delta="3-State HMM"
    )

with m5:
    st.metric(
        label="Execution Mode",
        value=curr_exec_mode,
        delta="Alpaca / Mock"
    )

st.markdown("---")

# -----------------------------------------------------------------------------
# 7. Interactive Tabs Layout
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Portfolio Performance",
    "📊 Current Asset Allocations",
    "🌐 Market Regimes & Analytics",
    "📜 Execution Logs & Exports"
])

# =============================================================================
# TAB 1: PORTFOLIO PERFORMANCE
# =============================================================================
with tab1:
    st.subheader("Portfolio Net Worth Trajectory vs Initial Capital Baseline")
    
    dates = df_snapshots['date']
    net_worths = df_snapshots['portfolio_net_worth']
    
    if HAS_PLOTLY:
        fig_nw = go.Figure()
        fig_nw.add_trace(go.Scatter(
            x=dates,
            y=net_worths,
            mode='lines+markers',
            name='Portfolio Net Worth ($)',
            line=dict(color='#1E88E5', width=3),
            marker=dict(size=6),
            hovertemplate='Date: %{x}<br>Net Worth: $%{y:,.2f}<extra></extra>'
        ))
        fig_nw.add_trace(go.Scatter(
            x=dates,
            y=[INITIAL_CAPITAL] * len(dates),
            mode='lines',
            name='Initial Capital Baseline ($1,000,000)',
            line=dict(color='#E53935', width=2, dash='dash'),
            hovertemplate='Baseline: $1,000,000.00<extra></extra>'
        ))
        fig_nw.update_layout(
            title="Portfolio Net Worth Trajectory ($1,000,000 Baseline)",
            xaxis_title="Date",
            yaxis_title="Net Worth ($)",
            yaxis=dict(tickprefix="$", tickformat=",.0f"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=60, b=40),
            hovermode="x unified",
            template="plotly_white"
        )
        st.plotly_chart(fig_nw, use_container_width=True)
    else:
        df_nw = pd.DataFrame({
            'Date': dates,
            'Net Worth ($)': net_worths,
            'Initial Baseline ($1M)': [INITIAL_CAPITAL] * len(dates)
        }).set_index('Date')
        st.line_chart(df_nw)

    col_ret, col_dd = st.columns(2)
    
    with col_ret:
        st.subheader("Daily Returns (%)")
        daily_rets_pct = df_snapshots['daily_return'].apply(lambda r: r * 100.0 if abs(r) <= 1.0 else r)
        
        if HAS_PLOTLY:
            colors = ['#2ECC71' if r >= 0 else '#E74C3C' for r in daily_rets_pct]
            fig_ret = go.Figure(data=[
                go.Bar(
                    x=dates,
                    y=daily_rets_pct,
                    marker_color=colors,
                    name='Daily Return (%)',
                    hovertemplate='Date: %{x}<br>Return: %{y:+.2f}%<extra></extra>'
                )
            ])
            fig_ret.update_layout(
                title="Daily Returns (%) - Green: Profit, Red: Loss",
                xaxis_title="Date",
                yaxis_title="Daily Return (%)",
                yaxis=dict(ticksuffix="%"),
                margin=dict(l=40, r=40, t=50, b=40),
                template="plotly_white"
            )
            st.plotly_chart(fig_ret, use_container_width=True)
        else:
            df_ret = pd.DataFrame({'Date': dates, 'Daily Return (%)': daily_rets_pct}).set_index('Date')
            st.bar_chart(df_ret)
            
    with col_dd:
        st.subheader("Drawdown Trajectory Curve (%)")
        drawdowns_pct = df_snapshots['drawdown'].apply(lambda d: d * 100.0 if abs(d) <= 1.0 else d)
        
        if HAS_PLOTLY:
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(
                x=dates,
                y=drawdowns_pct,
                mode='lines',
                fill='tozeroy',
                name='Drawdown (%)',
                line=dict(color='#E74C3C', width=2),
                fillcolor='rgba(231, 76, 60, 0.2)',
                hovertemplate='Date: %{x}<br>Drawdown: %{y:.2f}%<extra></extra>'
            ))
            fig_dd.update_layout(
                title="Portfolio Drawdown Curve over Time",
                xaxis_title="Date",
                yaxis_title="Drawdown (%)",
                yaxis=dict(ticksuffix="%"),
                margin=dict(l=40, r=40, t=50, b=40),
                template="plotly_white"
            )
            st.plotly_chart(fig_dd, use_container_width=True)
        else:
            df_dd = pd.DataFrame({'Date': dates, 'Drawdown (%)': drawdowns_pct}).set_index('Date')
            st.line_chart(df_dd)


# =============================================================================
# TAB 2: CURRENT ASSET ALLOCATIONS
# =============================================================================
with tab2:
    st.subheader("Current Asset Allocations & Holdings Breakdown")
    
    # Calculate cumulative net position per ticker from log
    net_shares_map = {}
    last_price_map = {}
    last_action_map = {}
    
    for _, row in df.iterrows():
        t = str(row['ticker'])
        act = str(row['action_type']).upper()
        if act in ['BUY', 'SELL']:
            s = float(row['shares']) if act == 'BUY' else -float(row['shares'])
            net_shares_map[t] = net_shares_map.get(t, 0.0) + s
            last_price_map[t] = float(row['price'])
            last_action_map[t] = act
            
    holdings_list = []
    total_equities_val = 0.0
    
    for ticker, shares in net_shares_map.items():
        if round(shares, 4) > 0:
            price = last_price_map.get(ticker, 0.0)
            trade_val = shares * price
            total_equities_val += trade_val
            holdings_list.append({
                'Ticker': ticker,
                'Action': last_action_map.get(ticker, 'BUY'),
                'Shares': round(shares, 4),
                'Price ($)': round(price, 2),
                'Trade Value ($)': round(trade_val, 2),
            })
            
    latest_cash = float(latest_snap.get('portfolio_cash', 0.0))
    if latest_cash <= 0 and latest_net_worth > total_equities_val:
        latest_cash = max(0.0, latest_net_worth - total_equities_val)
        
    portfolio_total = total_equities_val + latest_cash
    if portfolio_total <= 0:
        portfolio_total = latest_net_worth
        
    for h in holdings_list:
        h['Weight (%)'] = round((h['Trade Value ($)'] / portfolio_total) * 100.0, 2)
        
    holdings_df = pd.DataFrame(holdings_list)
    if not holdings_df.empty:
        holdings_df = holdings_df.sort_values(by='Weight (%)', ascending=False).reset_index(drop=True)
        
    alloc_data = []
    for h in holdings_list:
        alloc_data.append({'Asset': h['Ticker'], 'Value ($)': h['Trade Value ($)'], 'Weight (%)': h['Weight (%)']})
        
    cash_weight = round((latest_cash / portfolio_total) * 100.0, 2)
    if cash_weight > 0.001 or len(alloc_data) == 0:
        alloc_data.append({'Asset': 'CASH', 'Value ($)': round(latest_cash, 2), 'Weight (%)': cash_weight})
        
    alloc_df = pd.DataFrame(alloc_data)

    c_chart1, c_chart2 = st.columns([1, 1])
    
    with c_chart1:
        st.markdown("#### Donut Chart: Portfolio Allocation")
        if HAS_PLOTLY and not alloc_df.empty:
            fig_donut = px.pie(
                alloc_df,
                names='Asset',
                values='Weight (%)',
                hole=0.4,
                title="Asset Allocation Weights across DJIA Tickers & Cash",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_donut.update_traces(textposition='inside', textinfo='percent+label')
            fig_donut.update_layout(margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_donut, use_container_width=True)
        elif not alloc_df.empty:
            st.bar_chart(alloc_df.set_index('Asset')['Weight (%)'])
            
    with c_chart2:
        st.markdown("#### Bar Chart: Asset Weights Comparison")
        if HAS_PLOTLY and not alloc_df.empty:
            fig_bar = px.bar(
                alloc_df,
                x='Asset',
                y='Weight (%)',
                color='Weight (%)',
                color_continuous_scale='Viridis',
                title="Asset Weight Breakdown (% of Portfolio)",
                text='Weight (%)'
            )
            fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig_bar.update_layout(xaxis_tickangle=-45, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_bar, use_container_width=True)
            
    st.markdown("#### Current Portfolio Holdings Table")
    if not holdings_df.empty:
        display_holdings = holdings_df.copy()
        cash_row = pd.DataFrame([{
            'Ticker': 'CASH',
            'Action': 'HOLD',
            'Shares': 1.0,
            'Price ($)': round(latest_cash, 2),
            'Trade Value ($)': round(latest_cash, 2),
            'Weight (%)': cash_weight
        }])
        display_holdings = pd.concat([display_holdings, cash_row], ignore_index=True)
        
        st.dataframe(
            display_holdings.style.format({
                'Shares': '{:,.4f}',
                'Price ($)': '${:,.2f}',
                'Trade Value ($)': '${:,.2f}',
                'Weight (%)': '{:.2f}%'
            }),
            use_container_width=True
        )
    else:
        st.info("No active equity holdings recorded.")


# =============================================================================
# TAB 3: MARKET REGIMES & ANALYTICS
# =============================================================================
with tab3:
    st.subheader("Market Regime Analytics & Distribution")
    
    regime_counts = df_snapshots['market_regime'].value_counts().reset_index()
    regime_counts.columns = ['Market Regime', 'Count']
    
    col_reg1, col_reg2 = st.columns([1, 1])
    
    with col_reg1:
        st.markdown("#### Market Regime Time Distribution")
        if HAS_PLOTLY and not regime_counts.empty:
            color_map = {
                'Bullish Low-Vol': '#2ECC71',
                'Bullish': '#2ECC71',
                'Neutral': '#3498DB',
                'Bearish High-Vol': '#E74C3C',
                'Bearish': '#E74C3C'
            }
            fig_reg_pie = px.pie(
                regime_counts,
                names='Market Regime',
                values='Count',
                title="Time Spent in Each Market Regime (HMM States)",
                color='Market Regime',
                color_discrete_map=color_map,
                hole=0.35
            )
            fig_reg_pie.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_reg_pie, use_container_width=True)
        elif not regime_counts.empty:
            st.bar_chart(regime_counts.set_index('Market Regime'))

    with col_reg2:
        st.markdown("#### Regime Frequency Breakdown Table")
        regime_counts['Percentage (%)'] = round((regime_counts['Count'] / regime_counts['Count'].sum()) * 100.0, 2)
        st.dataframe(
            regime_counts.style.format({'Percentage (%)': '{:.2f}%'}),
            use_container_width=True
        )
        
    st.markdown("#### Regime-Highlighted Portfolio Trajectory Chart")
    if HAS_PLOTLY:
        fig_reg_traj = px.line(
            df_snapshots,
            x='date',
            y='portfolio_net_worth',
            title="Portfolio Net Worth Trajectory with Active Market Regime Overlay",
            labels={'portfolio_net_worth': 'Net Worth ($)', 'date': 'Date'}
        )
        fig_reg_traj.update_traces(line=dict(color='#7F8C8D', width=2))
        
        # Overlay scatter points per market regime
        for regime_name, group in df_snapshots.groupby('market_regime'):
            color = '#2ECC71' if 'Bullish' in str(regime_name) else ('#E74C3C' if 'Bearish' in str(regime_name) else '#3498DB')
            fig_reg_traj.add_trace(go.Scatter(
                x=group['date'],
                y=group['portfolio_net_worth'],
                mode='markers',
                name=f"Regime: {regime_name}",
                marker=dict(size=10, color=color),
                hovertemplate='Date: %{x}<br>Net Worth: $%{y:,.2f}<br>Regime: ' + str(regime_name) + '<extra></extra>'
            ))
            
        fig_reg_traj.update_layout(
            xaxis_title="Date",
            yaxis_title="Net Worth ($)",
            yaxis=dict(tickprefix="$", tickformat=",.0f"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=50, b=40),
            template="plotly_white"
        )
        st.plotly_chart(fig_reg_traj, use_container_width=True)
    else:
        st.line_chart(df_snapshots.set_index('date')['portfolio_net_worth'])


# =============================================================================
# TAB 4: EXECUTION LOGS & EXPORTS
# =============================================================================
with tab4:
    st.subheader("Interactive Execution Logs & Offline Export")
    
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    
    with col_f1:
        action_options = ["ALL"] + sorted(list(df['action_type'].unique())) if 'action_type' in df.columns else ["ALL"]
        action_filter = st.selectbox(
            "Filter by Action Type",
            options=action_options
        )
        
    with col_f2:
        all_tickers = sorted(list(df['ticker'].unique())) if 'ticker' in df.columns else []
        ticker_filter = st.selectbox(
            "Filter by Ticker",
            options=["ALL"] + all_tickers
        )
        
    with col_f3:
        search_query = st.text_input("Search Logs", value="", placeholder="Search ticker, date, regime...")
        
    # Apply Filters
    filtered_df = df.copy()
    
    if action_filter != "ALL":
        filtered_df = filtered_df[filtered_df['action_type'] == action_filter]
        
    if ticker_filter != "ALL":
        filtered_df = filtered_df[filtered_df['ticker'] == ticker_filter]
        
    if search_query:
        query_str = search_query.lower()
        mask = filtered_df.apply(lambda row: row.astype(str).str.lower().str.contains(query_str).any(), axis=1)
        filtered_df = filtered_df[mask]
        
    st.markdown(f"Displaying **{len(filtered_df)}** of **{len(df)}** total trade log records:")
    
    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=420
    )
    
    st.markdown("---")
    
    # Download CSV Export Button
    csv_buffer = io.StringIO()
    filtered_df.to_csv(csv_buffer, index=False)
    csv_data = csv_buffer.getvalue()
    
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="📥 Download Executed Trade Logs (CSV)",
        data=csv_data,
        file_name=f"paper_trade_log_export_{timestamp_str}.csv",
        mime="text/csv",
        use_container_width=False
    )
