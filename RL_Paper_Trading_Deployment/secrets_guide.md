# Alpaca Paper Trading Credentials & Setup Guide

This guide provides step-by-step instructions for creating a free Alpaca Paper Trading account, generating API credentials, and configuring your local environment for live paper trading execution with the RL Trading Strategy.

---

## 1. Overview of Alpaca Paper Trading

Alpaca provides a commission-free developer API for automated stock trading. Their **Paper Trading** environment allows you to execute simulated trades against real-time US market data without risking actual capital.

- **Paper Trading Base URL**: `https://paper-api.alpaca.markets`
- **Cost**: 100% Free
- **Account Type**: Individual Developer Account

---

## 2. Step-by-Step Account Creation

1. **Sign Up**:
   - Navigate to the [Alpaca Dashboard Sign Up Page](https://app.alpaca.markets/signup).
   - Enter your email address and a strong password, then click **Sign Up**.
   - Verify your email address by clicking the verification link sent to your inbox.

2. **Access the Dashboard**:
   - Log in to your Alpaca account at [https://app.alpaca.markets](https://app.alpaca.markets).
   - Upon logging in, look at the top navigation bar or left sidebar to ensure you are in the **Paper Trading** dashboard (you will see a banner or toggle indicating **"Paper Account"** with a starting virtual cash balance, typically $100,000).

---

## 3. Generating API Key ID & Secret Key

1. **Locate API Keys Panel**:
   - On the right panel of the Paper Trading Dashboard, find the section titled **API Keys** or **Your API Keys**.
   - If generating for the first time, click **Generate New Keys** (or **Regenerate Key**).

2. **Copy Credentials**:
   - **API Key ID**: A alphanumeric string (e.g., `PKXXXXXXXXXXXXXXXXXX`). Copy and save this.
   - **Secret Key**: A longer secret string (e.g., `XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`).
   - ⚠️ **IMPORTANT**: The Secret Key is shown **ONLY ONCE**. Copy it immediately and store it securely. If lost, you will need to generate a new key pair.

3. **Verify API Base URL**:
   - Ensure you use the Paper Trading base URL:
     `https://paper-api.alpaca.markets`
   - *Do NOT use `https://api.alpaca.markets` (which is for live real-money trading).*

---

## 4. Configuring `.env` Environment File

1. **Copy the Template**:
   In the root of the deployment directory (`RL_Paper_Trading_Deployment`), create a `.env` file by copying `.env.example`:
   ```bash
   cp .env.example .env
   # On Windows PowerShell:
   Copy-Item .env.example .env
   ```

2. **Update `.env` with Your Credentials**:
   Open `.env` in a text editor and replace the placeholder values with your actual Alpaca Paper Trading keys:

   ```ini
   # Alpaca Paper Trading API Credentials
   APCA_API_KEY_ID=PK1234567890ABCDEFGH
   APCA_API_SECRET_KEY=AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
   APCA_API_BASE_URL=https://paper-api.alpaca.markets

   # Trading Execution Configuration
   TRADING_MODE=paper
   ```

3. **Security Best Practices**:
   - Never commit your `.env` file to git repositories or share your secret key publicly.
   - The `.env` file is included in `.gitignore` by default.

---

## 5. Dual-Mode Execution Behavior in `trade_executor.py`

The execution engine (`trade_executor.py`) is designed with automatic **Dual-Mode Execution**:

- **Live Alpaca Paper Trading Mode**:
  - Activated automatically when valid `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` are detected in `.env` / environment and connection test to `https://paper-api.alpaca.markets/v2/account` succeeds.
  - Submits paper trading orders directly to Alpaca API.

- **Mock Execution Mode (Fallback)**:
  - Automatically triggered if API keys are missing, empty, invalid, or network connection fails.
  - Logs a clear warning message:
    `[WARNING] Alpaca API keys missing or invalid. Automatically entering Mock Execution Mode.`
  - Simulates trade executions locally using a 10 bps (0.001) fee structure, updates portfolio cash/holdings, and logs trades to `logs/paper_trade_log.csv`.
