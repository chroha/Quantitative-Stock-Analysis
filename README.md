# Quantitative Stock Analysis System V3.0

[中文版文档](README_CN.md)

## Introduction

This is a quantitative stock analysis and screening tool built for personal use. It is designed to help me quickly and comprehensively evaluate US stocks across fundamentals, technicals, and valuation. It automatically acquires data, calculates complex financial metrics, performs multi-dimensional scoring based on designed quantitative logic, and generates investment reports to assist in decision-making.

## Core Features

### 1. Deep Stock Analysis (`run_analysis.py`)

Performs a full-pipeline analysis for a single stock:

- **Data Acquisition**: Uses a 4-tier cascading data strategy:
  - **T1 Yahoo Finance**: Primary source for real-time quotes and historical financials.
  - **T2 SEC EDGAR**: Official XBRL data directly from the U.S. Securities and Exchange Commission.
  - **T3 FMP**: Supplements analyst estimates and structured financial data.
  - **T4 Alpha Vantage**: Final fallback for obscure stocks with data gaps.
  - **Completeness Scorecard**: Visualizes data health, history depth (Year-by-Year matrix), and missing fields in real-time.
- **Financial Scoring**: Scores the company (0-100) based on 20+ weighted metrics including ROIC, ROE, margins, growth rates, benchmarked against industry standards.
- **Technical Scoring**: Evaluates current trend and momentum using RSI, MACD, and Moving Averages (SMA/EMA).
- **Valuation Models**:
  - Discounted Cash Flow (DCF)
  - Dividend Discount Model (DDM)
  - Relative Valuation (PE/PB/PS/EV-EBITDA Multiples)
  - Value Investing (Graham Number, Peter Lynch, PEG Ratio)
  - Analyst Consensus Targets
- **AI Investment Commentary**: Uses Google Gemini to generate an interpretative report based on all the above data.

### 3. Macro Strategy Analysis (`run_macro_report.py`)

A completely new macroeconomic analysis module for top-down market strategy:

- **Multi-dimensional Data Integration**: Automatically fetches key macro indicators from FRED (Treasury Yields, CPI, Unemployment) and Yahoo Finance (S&P 500, VIX, Exchange Rates).
- **Economic Cycle Positioning**: Quantitatively assesses the current economic cycle phase (e.g., Recovery, Overheating, Stagflation) based on yield spreads, inflation, and employment data.
- **Risk Environment Assessment**: Evaluates market risk appetite (Risk On/Off) by synthesizing signals from VIX volatility, Dollar Index (DXY), and Carry Trade (USD/JPY).
- **Asset Allocation Advice**: Generates asset allocation (Equity/Bond) and geographic bias (US/Emerging) recommendations based on Equity Risk Premium (ERP) and valuation levels.
- **Bilingual Reports**: Automatically generates bilingual (English/Chinese) Markdown reports including raw data tables.

### 2. Batch Stock Scanner (`run_scanner.py`)

- **Batch Processing**: Scans a user-defined list of stocks in one go.
- **Rapid Scoring**: Skips time-consuming valuation and AI steps to focus on rapid financial and technical scoring.
- **Auto-Ranking**: Automatically ranks results by Financial Score.
- **Graceful Degradation**: Intelligently detects and flags stocks with insufficient data (e.g., < 5 years history) in the final report with "reduced reliability" notes.
- **Output**: Prints a summary to the console and generates a detailed text report file.

## Directory Structure

```
.
├── data_acquisition/       # Data Fetching Modules (Yahoo, EDGAR, FMP, Alpha Vantage)
│   ├── benchmark_data/     # Industry Benchmark Data
│   ├── stock_data/         # Stock Financial Data
│   └── macro_data/         # [NEW] Macro Economic Data
├── fundamentals/           # Core Analysis Logic
│   ├── financial_data/     # Metric Calculation (Growth, Profitability, Capital)
│   ├── financial_scorers/  # Financial Scoring Engine (Config & Weights)
│   ├── technical_scorers/  # Technical Indicator Scoring
│   ├── valuation/          # Valuation Models
│   ├── ai_commentary/      # AI Report Generation
│   └── macro_indicator/    # [NEW] Macro Strategy Logic
├── generated_data/         # Intermediate Data (JSON)
├── generated_reports/      # Final Reports (AI Analysis, Scan Summaries)
├── report_example/         # Report Examples
├── config/                 # Configuration (Thresholds & Settings)
├── user_config/            # User Config & Temp Industry Data
├── utils/                  # Utilities (Logger, Masking, Schema)
├── run_analysis.py         # Single Stock Analysis Entry
├── run_scanner.py          # Batch Scanner Entry
├── run_getform.py          # Form Generation Tool
└── run_macro_report.py     # [NEW] Macro Strategy Report Entry
```

## Data Storage & Artifacts

### 1. User Config & Raw Data (`user_config/`)

- **`.env`**: Private file storing your API Keys.
- **`.csv` (xls)**: Raw industry data files downloaded from Damodaran (e.g., `wacc.csv`, `betas.csv`).
- **`sector_benchmarks.json`**: Static industry benchmark data (Generated from Damodaran's raw CSVs, serving as the system default).

### 2. Generated Data (`generated_data/`)

Intermediate processing data is stored here:

- **Raw Stock Data**: `initial_data_{SYMBOL}_{DATE}.json`
- **Benchmarks**: `benchmark_data_{DATE}.json`
- **Metrics**: `financial_data_{SYMBOL}_{DATE}.json`
- **Scores**: `financial_score_{SYMBOL}_{DATE}.json`

### 3. Analysis Reports (`generated_reports/`)

Final human-readable reports are stored here:

- **Scanner Report**: `stock_scan_{DATE}.txt` (Summary of batch scan)
- **AI Report**: `ai_analysis_{SYMBOL}_{DATE}.md` (Deep dive analysis by AI)
- **Data Table**: `collated_scores_{DATE}.csv` (Aggregated CSV report from run_getform.py)

### 4. Report Examples

To see what the generated AI analysis reports look like, check out this example:

- **[Sample AI Depth Analysis Report](report_example/ai_analysis_AAPL_2026-01-22.md)**

## Installation & Configuration

### 1. Requirements

Ensure Python 3.8+ is installed, then install dependencies directly:

```bash
pip install yfinance requests pydantic python-dotenv pandas numpy python-dateutil fredapi scipy pytz
```

### 2. API Key Configuration

This system relies on external APIs to ensure data integrity. Create a `.env` file in the root directory and add your keys:

**File: `.env`**

```env
# [Required] Alpha Vantage: Fills gaps for missing/obscure financial data
ALPHAVANTAGE_API_KEY=your_key_here

# [Required] Financial Modeling Prep (FMP): For analyst targets, WACC, and supplementary financials
FMP_API_KEY=your_key_here

# [Required] Google Gemini: For generating AI analysis reports
GEMINI_API_KEY=your_key_here
```

### 3. Get API Keys

- **Alpha Vantage**: [Get Key (Free)](https://www.alphavantage.co/support/#api-key) - Free tier has some endpoint limitations.
- **FMP**: [Sign Up (Free Tier)](https://site.financialmodelingprep.com/) - Free tier has limitations (max 250 requests/day).
- **Google Gemini**: [AI Studio](https://aistudio.google.com/app/apikey) - Free to use.

## Usage

### Run Single Stock Analysis (Deep Mode)

```bash
python run_analysis.py AAPL
# Or run without arguments to enter interactive mode
python run_analysis.py
```

### Run Batch Scanner (Screening Mode)

```bash
python run_scanner.py AAPL MSFT NVDA TSLA
# Or run without arguments to verify/input list
python run_scanner.py
```

### Run Data Aggregation (Report Mode)

```bash
python run_getform.py AAPL MSFT
# Aggregates scores and valuations into a single CSV file
```

### Run Macro Strategy Report (Macro Mode)

```bash
python run_macro_report.py
# Starts interactive menu to generate report or refresh data
```

## Core Algorithms & Logic

The system is not just a data dashboard, but a sophisticated quantitative evaluation engine.

### 1. Synthetic Benchmarking Algorithm

Since detailed industry distributions (e.g., specific P90/P10 breakpoints) are not directly available, the system uses a core algorithm to reconstruct them:

- **Input**: Industry Mean ($\mu$) from Damodaran and Coefficient of Variation (CV) derived from volatility.
- **Calculation**:
  - Applies a **Damping Factor** (0.8~0.95) to correct for real-world "fat tails".
  - Reconstructs percentiles using a Synthetic Z-Score formula: $P_{xx} = \mu \pm Z \times (\mu \times CV \times Damping)$.
- **Significance**: Achieves **"Relative Fairness"**. In stable sectors (Utilities), slightly above average is excellent; in volatile sectors (Biotech), significant outperformance is required for high scores.

### 2. Dynamic Sector Scoring

Instead of a "one-size-fits-all" approach, the system uses tailored weights for GICS 11 sectors (`scoring_config.py`):

- **Technology**: High weight on **Growth** (Revenue/Net Income CAGR) and R&D.
- **Financials/REITs**: Focus on **Capital Allocation** (Dividends/Buybacks) and **PB Ratio**.
- **Energy/Utilities**: Prioritizes **Cash Flow** (FCF) and Debt Health.
- *Adaptive Mechanism*: If a metric is missing, its weight is automatically redistributed to other metrics in the same category, ensuring a valid 0-100 score.

#### Scoring Weights Visualization

![scoring_weights_overview](scoring_weights_overview.png)
*Scoring Weights Overview*

![scoring_weights_detailed](scoring_weights_detailed.png)
*Detailed Valuation Weights*

### 3. Valuation Blender

To avoid single-model bias, the system aggregates **10 Major Valuation Models** with sector-specific weighting (`valuation_config.py`):

- **Absolute Valuation**:
    1. **DCF (Discounted Cash Flow)**: For mature firms with predictable cash flows.
    2. **DDM (Dividend Discount Model)**: For high-yield sectors (Banks, Utilities).
- **Relative Valuation**:
    3.  **PE (Price-to-Earnings)**: For profitable, stable firms.
    4.  **PS (Price-to-Sales)**: Critical for high-growth, unprofitable firms (SaaS/Biotech).
    5.  **PB (Price-to-Book)**: Floor logic for asset-heavy or financial firms.
    6.  **EV/EBITDA**: Capital-neutral metric for manufacturing/heavy industry.
- **Value Investing Models**:
    7.  **Graham Number**: Conservative intrinsic value based on EPS and Book Value.
    8.  **Peter Lynch Fair Value**: Growth-adjusted valuation using Net Income CAGR.
    9.  **PEG Ratio**: Price/Earnings-to-Growth for growth stock evaluation.
- **Market Consensus**:
    10. **Analyst Targets**: Incorporates Wall Street sentiment as a reference.

#### Valuation Logic Visualization

![Valuation Weights Detailed](valuation_weights_detailed_en.png)
*Detailed Valuation Weights & Logic*

![Valuation Weights Final](valuation_weights_final_en.png)
*Final Valuation Synthesis*

---

## Feedback & Issues

This system involves complex data fetching (from Yahoo/EDGAR/FMP/Alpha Vantage) and financial calculations.

If you encounter **bugs**, **calculation errors**, **data fetching failures**, or **incorrect field mappings**, please report them by opening an issue. Your feedback is crucial for improving the accuracy and robustness of the system. Thank you!

## Risk Warning & Disclaimer

Investing in financial markets involves risks. The views, analyses, and scores presented in this report are logical deductions based on specific model parameters and do not constitute recommendations to buy, hold, or sell any financial products. Investors should make independent decisions based on their own risk tolerance. The author assumes no legal liability for any direct or indirect losses resulting from the use of this report.

---
Generated by Antigravity Agent
