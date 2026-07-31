# Detailed Data Audit Report: Dow Jones 30 Financial Datasets (Milestone 0)

**Author:** Explorer 2  
**Target Repository:** `Deep-Reinforcement-Learning-with-Stock-Trading`  
**Date:** July 31, 2026  

---

## 1. Executive Summary

This report provides a comprehensive data audit of the financial datasets contained in `f:/SURE Trust/Capstone Project/Deep-Reinforcement-Learning-with-Stock-Trading`. 

A total of **60 CSV files** were identified and audited:
- **30 primary CSV files** located in the root repository directory.
- **30 duplicate/notebook CSV files** located in the `notebooks/` directory.

These datasets represent historical price and volume data for the **30 constituent stocks of the Dow Jones Industrial Average (DJIA)**. The data spans from **January 2, 2009 to May 7, 2020** (2,857 trading days for standard assets) at a **daily sampling frequency**.

### Key Findings & Data Health Summary
1. **Schema Consistency:** All files share a standard 7-column OHLCV schema: `Date`, `Open`, `High`, `Low`, `Close`, `Adj Close`, `Volume`. There is no explicit `tic` column in the CSV files; ticker identity is derived from the filename.
2. **Sampling Frequency:** Data is strictly **daily aggregated bars** (1 record per trading day). No intraday timestamps, order book depth (L2/L3), or tick-level trades exist in these datasets.
3. **Data Completeness & Anomalies:**
   - **28 Tickers (93.3%):** 100% complete across 2,857 trading days (2009-01-02 to 2020-05-07) with zero missing values (NaNs).
   - **DOW (Dow Inc.):** Truncated history containing only 288 trading days (2019-03-20 to 2020-05-07) due to its corporate spin-off from DowDuPont on March 20, 2019. Missing ~10 years of training history.
   - **UTX (United Technologies Corp):** Completely empty dataset (0 records, 42 bytes containing only the header row). Occurred due to corporate merger with Raytheon (RTX) in April 2020, breaking automated Yahoo Finance downloads.
4. **Feature Engineering Feasibility:**
   - **Volatility Clustering (EWMA, Rolling Vol Ratio, GARCH):** **FEASIBLE & HIGHLY SUITED**. Standard daily frequency is optimal for GARCH(1,1), EWMA, Parkinson, and Garman-Klass volatility metrics.
   - **Spoofing Proxies:** **LIMITED / NOT DIRECTLY FEASIBLE AT MICROSTRUCTURE LEVEL**. True order-book spoofing requires sub-second L2/L3 order book data. Coarse daily volume-price imbalance proxies must be used instead.
   - **News Shocks:** **MODERATELY FEASIBLE (STATISTICAL SHOCK PROXIES ONLY)**. No textual news feed exists. Statistical jump indicators (Z-score return shocks, overnight gaps, volume spikes) can effectively proxy major news releases.
   - **Market Regimes:** **DAILY REGIMES HIGHLY FEASIBLE / INTRADAY NOT FEASIBLE**. Daily Gaussian HMMs and GMM trend/volatility clustering can be constructed, but intraday regime transitions cannot be modeled.

---

## 2. Dataset Schema & Asset Inventory

### 2.1 File Schema Definition

Each non-empty CSV file adheres to the following layout:

| Column Name | Data Type | Description | Adjustment Status |
| :--- | :--- | :--- | :--- |
| `Date` | `YYYY-MM-DD` | Date of trading session (ISO-8601 string) | N/A |
| `Open` | `float64` | Opening price during standard market hours | Unadjusted |
| `High` | `float64` | Highest price recorded during session | Unadjusted |
| `Low` | `float64` | Lowest price recorded during session | Unadjusted |
| `Close` | `float64` | Unadjusted closing price | Unadjusted |
| `Adj Close` | `float64` | Closing price adjusted for stock splits & dividends | Adjusted |
| `Volume` | `int64` | Total volume of shares traded during session | Unadjusted |

*Note:* When combining these datasets into a unified panel for Reinforcement Learning (RL), a `tic` (ticker symbol) column must be added explicitly during ingestion.

---

### 2.2 Detailed Asset Breakdown

Below is the complete audit inventory of the 30 asset CSV files found in the root directory (mirrored in `notebooks/`):

| Ticker | Asset Name | File Size (Bytes) | Total Lines | Data Rows | Start Date | End Date | Missing Values (NaN) | Data Quality Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AAPL** | Apple Inc. | 316,594 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **AXP** | American Express Co. | 306,098 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **BA** | Boeing Co. | 303,681 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **CAT** | Caterpillar Inc. | 303,796 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **CSCO** | Cisco Systems, Inc. | 314,229 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **CVX** | Chevron Corporation | 308,119 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **DIS** | The Walt Disney Co. | 308,123 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **DOW** | Dow Inc. | 30,723 | 289 | 288 | 2019-03-20 | 2020-05-07 | 0 | **Truncated History** (Post-spin-off) |
| **GS** | Goldman Sachs Group | 307,191 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **HD** | Home Depot, Inc. | 309,168 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **IBM** | IBM Corporation | 318,839 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **INTC** | Intel Corporation | 312,864 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **JNJ** | Johnson & Johnson | 307,428 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **JPM** | JPMorgan Chase & Co. | 310,291 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **KO** | The Coca-Cola Co. | 311,246 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **MCD** | McDonald's Corp. | 304,617 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **MMM** | 3M Company | 315,158 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **MRK** | Merck & Co., Inc. | 316,179 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **MSFT** | Microsoft Corp. | 311,996 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **NKE** | NIKE, Inc. | 307,578 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **PFE** | Pfizer Inc. | 321,148 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **PG** | Procter & Gamble Co. | 303,809 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **TRV** | The Travelers Companies | 309,318 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **UNH** | UnitedHealth Group | 307,486 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **UTX** | United Technologies | 42 | 2 | **0** | N/A | N/A | N/A | **Empty File** (Merger anomaly) |
| **V** | Visa Inc. | 307,181 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **VZ** | Verizon Communications | 312,021 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **WBA** | Walgreens Boots Alliance | 305,476 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **WMT** | Walmart Inc. | 319,614 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |
| **XOM** | Exxon Mobil Corp. | 304,258 | 2,858 | 2,857 | 2009-01-02 | 2020-05-07 | 0 | Clean / Complete |

---

## 3. Data Quality, Anomalies & Preprocessing Recommendations

### 3.1 Detailed Anomaly Analysis

1. **UTX (United Technologies) Empty File Anomaly:**
   - `UTX.csv` has a file size of 42 bytes and contains zero data rows (only header: `Date,Open,High,Low,Close,Adj Close,Volume`).
   - *Root Cause:* United Technologies Corp (UTX) completed a merger with Raytheon in April 2020, changing ticker representation. Automated API calls to Yahoo Finance using `UTX` returned an empty dataset.
   - *Impact on RL:* Including UTX will cause errors during feature calculation or matrix operations (zero rows).
   - *Recommendation:* Remove `UTX` from the active ticker universe for backtesting and RL environment instantiation, reducing the universe from 30 to 28 assets (or 29 if DOW is handled).

2. **DOW (Dow Inc.) Late Start Anomaly:**
   - `DOW.csv` contains only 288 trading days starting on `2019-03-20`.
   - *Root Cause:* Dow Inc. was spun off from DowDuPont on March 20, 2019. Historical data prior to this date does not exist under ticker `DOW`.
   - *Impact on RL:* If the training period is set to `2009-01-01` to `2015-12-31`, `DOW` has 0 training samples. For validation (`2016`), `DOW` has 0 samples.
   - *Recommendation:* Exclude `DOW` from 2009–2020 multi-asset portfolio training models, or forward-fill/impute missing history if required. The clean benchmark universe for 2009–2020 consists of **28 core assets**.

3. **Adjusted vs. Raw Price Discrepancies (Split & Dividend Handling):**
   - Columns `Open`, `High`, `Low`, and `Close` are raw prices. Column `Adj Close` accounts for splits and cash dividends.
   - *Example:* AAPL underwent a 7-for-1 stock split on June 9, 2014. Using raw `Close` for return calculations creates a false -85% price jump on split day.
   - *Recommendation:* Compute price returns using `Adj Close` ($r_t = \frac{\text{Adj Close}_t}{\text{Adj Close}_{t-1}} - 1$). Alternatively, adjust Open, High, Low, Close proportionally using the adjustment factor $\gamma_t = \frac{\text{Adj Close}_t}{\text{Close}_t}$.

---

## 4. Feature Engineering Assessment

The core task requires evaluating the dataset for engineering four specific feature domains:

```
+-----------------------------------------------------------------------------------+
|                            FEATURE ENGINEERING DOMAINS                            |
+---------------------------+-----------------------------------+-------------------+
| Domain                    | Data Requirement                  | Feasibility Status|
+---------------------------+-----------------------------------+-------------------+
| 1. Volatility Clustering  | Daily Returns, OHLC Prices        | HIGHLY FEASIBLE   |
| 2. Spoofing Proxies       | Order Book L2/L3, Depth, Quotes   | COARSE PROXIES    |
| 3. News Shocks            | Daily Returns, Volume, Gap        | STATISTICAL ONLY  |
| 4. Market Regimes         | Daily OHLCV, Multi-year History   | DAILY FEASIBLE    |
+---------------------------+-----------------------------------+-------------------+
```

---

### 4.1 Volatility Clustering (EWMA, Rolling Vol Ratio, GARCH)

**Assessment: Highly Feasible & High Quality**

Daily OHLCV data is ideal for volatility modeling and capturing financial time series tail risk / volatility clustering.

#### Implementable Formulations:
1. **Exponentially Weighted Moving Variance (EWMA):**
   $$\sigma_{EWMA, t}^2 = \lambda \sigma_{EWMA, t-1}^2 + (1 - \lambda) r_t^2$$
   where $\lambda = 0.94$ (standard RiskMetrics decay factor) and $r_t = \ln(\text{Adj Close}_t / \text{Adj Close}_{t-1})$.

2. **Rolling Volatility Ratio:**
   $$\text{VolRatio}_t = \frac{\sigma_{\text{short}, t}}{\sigma_{\text{long}, t}} = \frac{\text{Std}(r_{t-4:t})}{\text{Std}(r_{t-20:t})}$$
   A ratio > 1.5 signals sudden volatility expansion / cluster initiation.

3. **GARCH(1,1) Conditional Volatility:**
   $$\sigma_t^2 = \omega + \alpha \epsilon_{t-1}^2 + \beta \sigma_{t-1}^2$$
   Estimated per asset over rolling 252-day windows using `arch.arch_model(r_t, vol='Garch', p=1, q=1)`.

4. **Range-Based High-Frequency Proxies (Parkinson & Garman-Klass):**
   - **Parkinson Volatility (High/Low):**
     $$\sigma_{P, t}^2 = \frac{(\ln(High_t / Low_t))^2}{4 \ln 2}$$
   - **Garman-Klass Volatility (Open/High/Low/Close):**
     $$\sigma_{GK, t}^2 = 0.5 \left(\ln\frac{High_t}{Low_t}\right)^2 - (2\ln 2 - 1)\left(\ln\frac{Close_t}{Open_t}\right)^2$$
     *Advantage:* Provides significantly more accurate daily volatility estimates than close-to-close returns alone.

---

### 4.2 Spoofing Proxies (Volume Imbalance, Order Flow Imbalance, Order Patterns)

**Assessment: Not Directly Feasible at Microstructure Level / Requires Coarse Daily Proxies**

Spoofing is a high-frequency manipulation technique involving sub-second order placements and cancellations on bid-ask order books (Level 2/3 depth data). Because these datasets are **daily aggregated OHLCV**, sub-second order flow, bid-ask spreads, and quote cancellations **do not exist**.

#### Proposed Coarse Daily Workaround Proxies:
While true spoofing cannot be observed, coarse daily order-imbalance and pressure proxies can be calculated:
1. **Volume Imbalance Proxy (Upper/Lower Shadow Ratio):**
   $$\text{UpperShadow}_t = High_t - \max(Open_t, Close_t)$$
   $$\text{LowerShadow}_t = \min(Open_t, Close_t) - Low_t$$
   $$\text{ShadowRatio}_t = \frac{\text{UpperShadow}_t - \text{LowerShadow}_t}{High_t - Low_t + \epsilon}$$
   Measures intrabar buying vs. selling rejection.

2. **Volume-Weighted Price Pressure (VWAP Distance):**
   $$\text{VWAP}_{\text{proxy}, t} = \frac{High_t + Low_t + Close_t}{3}$$
   $$\text{VolumePressure}_t = \frac{Close_t - \text{VWAP}_{\text{proxy}, t}}{\text{ATR}_t} \times \frac{Volume_t}{\text{MA}_{20}(Volume_t)}$$

3. **Intraday Liquidity / Kyle's Lambda Proxy:**
   $$\lambda_{\text{proxy}, t} = \frac{|r_t|}{\text{Volume}_t / 10^6}$$
   Measures price impact per unit of volume traded.

---

### 4.3 News Shocks (Return Shock Jump Indicators, Jump Spike Proxies)

**Assessment: Moderately Feasible (Statistical Shock Proxies Only)**

No external textual news feeds or sentiment scores are provided in the CSV files. However, major earnings announcements, FDA approvals, and macroeconomic news manifest directly as **statistical price and volume jumps**.

#### Implementable Jump Proxies:
1. **Z-Score Return Shock Jump Indicator:**
   $$Z_{r, t} = \frac{r_t - \mu_{r, 21}}{\sigma_{r, 21}}$$
   $$\text{ShockFlag}_t = \mathbb{I}(|Z_{r, t}| > 2.5)$$

2. **Overnight Gap Shock:**
   $$r_{\text{gap}, t} = \ln\left(\frac{Open_t}{Close_{t-1}}\right)$$
   Overnight gaps directly capture news released outside regular trading hours (earnings reports released after close or before open).

3. **Abnormal Volume Spike Indicator:**
   $$Z_{V, t} = \frac{Volume_t - \text{Mean}_{21}(Volume)}{\text{Std}_{21}(Volume)}$$
   $$\text{NewsSpike}_t = Z_{r, t} \times Z_{V, t}$$
   High price shock accompanied by abnormal volume spike is a classic signal of institutional news digestion.

4. **Bipower Variation Jump Test (Bar-Based Jump Proxy):**
   Compare squared daily return $r_t^2$ to realized bipower variation $BV_t = \frac{\pi}{2} |r_t| |r_{t-1}|$ over rolling windows to isolate jump discontinuities from continuous diffusions.

---

### 4.4 Intraday Market Regimes (HMM, Trend/Volatility Regime Clustering)

**Assessment: Daily Regimes Highly Feasible / Intraday Regimes Not Feasible**

Because records are daily, **intraday regime transitions** (e.g. morning open volatility vs. mid-day lunch low-volatility vs. market close ramp) cannot be resolved. However, **multi-day/daily market regime modeling** across the 11-year timeline (2009–2020) is **highly feasible**.

#### Implementable Daily Regime Models:
1. **Gaussian Hidden Markov Model (HMM):**
   - **Feature Inputs:** Daily return $r_t$ and rolling Parkinson volatility $\sigma_{P, t}$.
   - **Model Setup:** 3-State Gaussian HMM (`hmmlearn.hmm.GaussianHMM(n_components=3)`):
     - *State 0:* Bullish / Low Volatility (Trend)
     - *State 1:* Sideways / Medium Volatility (Consolidation)
     - *State 2:* Bearish / High Volatility (Crisis / Panic)
   - **RL Output:** Pass posterior state probabilities $[P(S_t=0), P(S_t=1), P(S_t=2)]$ to the RL state representation.

2. **Unsupervised Regime Clustering (GMM / k-Means):**
   - Combine Average Directional Index (ADX-14), Normalized ATR, EWMA Volatility Ratio, and 21-day Return Momentum.
   - Fit Gaussian Mixture Model to classify daily regime into distinct market states.

---

## 5. Summary & Actionable Recommendations for Milestone 1

1. **Ticker Universe Definition:**
   - Exclude `UTX` completely (empty file anomaly).
   - Exclude `DOW` for standard 2009–2020 training splits (insufficient history).
   - Use the **28 verified clean assets** as the standard multi-asset portfolio universe.

2. **Data Alignment Protocol:**
   - Align all 28 assets on `Date` using an outer join, then verify 2,857 rows per asset.
   - Assign explicit ticker index `tic` to create the standard FinRL / RL state tensor shape `(T, N, F)` where $T=2857$, $N=28$, $F=\text{feature dimension}$.

3. **Feature Matrix Recommendations:**
   - **Volatility:** Include EWMA Volatility ($\lambda=0.94$), Garman-Klass Volatility, and Rolling Volatility Ratio ($5\text{d}/21\text{d}$).
   - **Shocks:** Include Return Z-score, Overnight Gap Return, and Volume Spike Index.
   - **Regimes:** Train a 3-State Gaussian HMM on market benchmark/aggregate returns and append state posterior probabilities to state space.
   - **Microstructure:** Replace impossible L2 spoofing features with Daily Shadow Ratio and VWAP Price Pressure.

---
*Report completed by Explorer 2.*
