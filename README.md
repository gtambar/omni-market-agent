# OmniMarket Agent — 24/7 Multi-Modal Quantitative & Deep Research Platform

**OmniMarket Agent** is an institutional-grade, Light-Mode interactive, multi-modal (**Voice + Text**) multi-agent equity analysis, deep company/technical research, and trade execution platform grounded live in **Google Finance** (`https://www.google.com/finance/quote/{TICKER}:{EXCHANGE}`).

---

## 🌟 Key Capabilities

1. **🎙️ Interactive Voice & Text Multi-Modal Assistant (`#interactive-voice-console`)**:
   - **Spoken Greeting First**: Clicking **`🎙️ Talk to OmniMarket`** (or any **`🎤 Voice`** button) greets the user audibly with *"How can I help you today?"* and opens the microphone only after the greeting finishes (`utterance.onend`), eliminating audio feedback loops.
   - **Instant Stock Chart Display**: Detecting any ticker or company name in speech or text immediately loads and scrolls to the **Top Hero Interactive Candlestick + MA(9, 20, 50, 200) + Wilder's RSI(14) & Divergence Chart**.
   - **Comprehensive Multi-Agent Spoken Response**: Runs `TechnicalIndicatorSubAgent`, `AnalystForecastSubAgent`, `SmartMoneyIndexSubAgent`, and `DeepResearchSubAgent` concurrently (`asyncio.gather`) to speak a complete grounded analysis covering live Google Finance price, daily change, Buy/Sell/Hold verdict, 9/20/50/200 SMAs, RSI(14), 10d momentum, Price-RSI divergence, Wall Street consensus/target/upgrades, company economic moat, and Congressional + Tom Lee ownership.
   - **Instant "Stop Response" Control**: Dedicated **`⏹️ Stop Response`** button (and `Esc` shortcut) immediately halts speech synthesis and queued sentences at any moment.

2. **Complete Multi-Index Universe Coverage (614 Tracked Equities Grounded Live in Google Finance)**:
   - Live quotes & 250+ trading days of historical OHLCV bars via Google Finance `FinHubUi/data/batchexecute` RPCs (`eJnF6e` & `wnpaJ`) + direct quote page grounding (`https://www.google.com/finance/quote/{TICKER}:{EXCHANGE}`).
   - **DJIA**: All 30 Dow Jones Industrial Average companies (`DIA`).
   - **Nasdaq 100**: All 101 Nasdaq-100 constituent stocks (`QQQ`).
   - **S&P 500**: All 503 S&P 500 constituent stocks across all 11 GICS sectors (`SPY`).
   - **IWM & Russell 3000**: `IWM`, `IWV`, and broad small/mid/large-cap Russell constituents.
   - **Value Stocks**: Multi-sector low-P/E, high free-cash-flow value compounders (`VTV`).
   - **🏛️ Congressional Leaders Index**: Separate custom index tracking stocks actively owned and traded by US Congressional Leaders via STOCK Act disclosures (`NANC`).
   - **🎯 Tom Lee / Fundstrat Portfolio Index**: Separate custom index tracking stocks held in the Fundstrat Granny Shots ETF (`GRNY`) and Tom Lee's thematic conviction portfolios.

3. **🔬 Separate Multi-Modal Deep Stock Research Studio (`DeepResearchSubAgent`)**:
   - Dedicated **Voice + Text Deep Research Search Area** on the Light-Mode UI (`POST /api/research/deep`).
   - Synthesizes **Company Research** (Business Model, Economic Moat Rating, Fwd P/E, Revenue Growth, Gross/FCF Margins, ROIC, Bull Catalysts & Bear Risks) + **Technical Analysis** (`MA 9, 20, 50, 200`, `RSI(14)`, `10d Momentum ROC`, `MACD`, `Price-RSI Divergence`, `Support & Resistance Levels`, `Entry Zone`, `Stop-Loss Invalidation`) into an explicit **`BUY` / `SELL` / `HOLD`** verdict with spoken audio briefing.

4. **📈 Top Interactive Candlestick + RSI(14)/Divergence Chart & Flashing UI Alerts**:
   - **Moving Averages**: 9, 20, 50, and 200 Simple & Exponential Moving Averages (`SMA` & `EMA`).
   - **Oscillators & Momentum**: Wilder's `RSI(14)`, 10-day `ROC`, and `MACD (12, 26, 9)`.
   - **Divergence Detector & Sub-Chart**: Synchronized lower chart pane rendering Wilder's `RSI(14)` with 70/30 overbought/oversold bands and explicit Bullish/Bearish Price-RSI Divergence status banners.
   - **Wall Street Consensus**: Analyst ratings, Low/Mean/High 12-month price targets, implied upside %, and recent brokerage upgrades/downgrades grounded in Google Finance.
   - **Flashing Indicators & Light-Mode Interactive UI**: High-contrast institutional Light Mode UI with pulsing buy/sell indicator ribbons.

5. **💼 Trade Execution with Human-in-the-Loop (HITL) Safety Gate**:
   - Executes `BUY` and `SELL` instructions via persistent SQLite Paper Trading Ledger + optional Alpaca Broker API adapter.
   - High-stakes trades (`>= $5,000` notional or `>= 100` shares) automatically pause at `HumanInTheLoopApprovalGate` (`hitl_...` confirmation token) until approved via UI click or spoken/typed confirmation.

6. **⏱️ 24/7 Continuous Operation (Every 3 Minutes)**:
   - Background `MarketScannerDaemon24x7` refreshes all indices and flashing indicators every **180 seconds (3 minutes)** locally or via Cloud Scheduler (`*/3 * * * *`) on Google Cloud Run.

---

## 🚀 Quick Start

```bash
# 1. (Optional) Install production dependencies (runs out-of-the-box on Python 3.11+ stdlib too!)
pip install -r requirements.txt

# 2. Launch the 24/7 Light-Mode Web Terminal & 3-Minute Daemon
python3 run.py --host 127.0.0.1 --port 8080
# Open http://127.0.0.1:8080 in Chrome/Edge/Safari

# 3. Run a Deep Stock Research Dossier from CLI
python3 run.py --deep-research NVDA

# 4. Run Unit & Integration Tests
python3 -m unittest discover -s tests -p "test_*.py" -v
```

---

## ☁️ Production Deployment & Cloud Infrastructure

```bash
# Deploy with Google ADK CLI / Cloud Run CLI
adk deploy cloud_run --project=$GCP_PROJECT_ID --region=us-central1 --service_name=omni-market-agent

# Or provision full Infrastructure as Code via Terraform (Cloud Run v2 + Secret Manager + 3-min Cloud Scheduler)
cd infra/terraform
terraform init
terraform apply -var="gcp_project_id=$GCP_PROJECT_ID"
```
