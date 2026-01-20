# Quantitative Stock Analysis System V3.0

[中文版文档](README_CN.md)
## Introduction
This is an advanced quantitative stock analysis and screening tool designed to automate the comprehensive evaluation of US stocks across fundamentals, technicals, and valuation. It automatically acquires data, calculates complex financial metrics, performs multi-dimensional scoring, and generates investment reports.

## Core Features

### 1. Deep Stock Analysis (`run_analysis.py`)
Performs a full-pipeline analysis for a single stock:
- **Data Acquisition**: Uses a 4-tier cascading data strategy:
    - **T1 Yahoo Finance**: Primary source for real-time quotes and historical financials.
    - **T2 SEC EDGAR**: Official XBRL data directly from the U.S. Securities and Exchange Commission.
    - **T3 FMP**: Supplements analyst estimates and structured financial data.
    - **T4 Alpha Vantage**: Final fallback for obscure stocks with data gaps.
- **Financial Scoring**: Scores the company (0-100) based on 20+ weighted metrics including ROIC, ROE, margins, growth rates, and capital allocation, benchmarked against industry standards (Damodaran data).
- **Technical Scoring**: Evaluates current trend and momentum using RSI, MACD, and Moving Averages (SMA/EMA).
- **Valuation Models**: 
    - Discounted Cash Flow (DCF)
    - Dividend Discount Model (DDM)
    - Mean Reversion (Graham Number, Peter Lynch)
    - Relative Valuation (PE/PS Multiples)
- **AI Investment Commentary**: Generates professional investment insights and risk warnings using Google Gemini, based on all the data above.

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
│   └── stock_data/         # Stock Financial Data
├── fundamentals/           # Core Analysis Logic
│   ├── financial_data/     # Metric Calculation (Growth, Profitability, Capital)
│   ├── financial_scorers/  # Financial Scoring Engine (Config & Weights)
│   ├── technical_scorers/  # Technical Indicator Scoring
│   ├── valuation/          # Valuation Models
│   └── ai_commentary/      # AI Report Generation
├── generated_data/         # Output Directory (JSON Data, PDF/TXT Reports)
├── config/                 # Configuration (Thresholds & Settings)
└── utils/                  # Utilities (Logger, Masking, Schema)
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

## Installation & Configuration

### 1. Requirements
Ensure Python 3.8+ is installed, then install dependencies:
```bash
pip install -r requirements.txt
```
(Key dependencies: `pandas`, `yfinance`, `requests`, `google-generativeai`)

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
- **Alpha Vantage**: [Get Key (Free)](https://www.alphavantage.co/support/#api-key) - 25 calls/day limit.
- **FMP**: [Sign Up (Free Tier)](https://site.financialmodelingprep.com/) - Free tier limits handled automatically.
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

## Core Algorithms & Logic

The system is not just a data dashboard, but a sophisticated quantitative evaluation engine.

### 1. Synthetic Benchmarking Algorithm
Since detailed industry distributions (e.g., specific P90/P10 breakpoints) are not directly available, the system uses a core algorithm to reconstruct them:
*   **Input**: Industry Mean ($\mu$) from Damodaran and Coefficient of Variation (CV) derived from volatility.
*   **Calculation**:
    *   Applies a **Damping Factor** (0.8~0.95) to correct for real-world "fat tails".
    *   Reconstructs percentiles using a Synthetic Z-Score formula: $P_{xx} = \mu \pm Z \times (\mu \times CV \times Damping)$.
*   **Significance**: Achieves **"Relative Fairness"**. In stable sectors (Utilities), slightly above average is excellent; in volatile sectors (Biotech), significant outperformance is required for high scores.

### 2. Dynamic Sector Scoring
Instead of a "one-size-fits-all" approach, the system uses tailored weights for GICS 11 sectors (`scoring_config.py`):
*   **Technology**: High weight on **Growth** (Revenue/Net Income CAGR) and R&D.
*   **Financials/REITs**: Focus on **Capital Allocation** (Dividends/Buybacks) and **PB Ratio**.
*   **Energy/Utilities**: Prioritizes **Cash Flow** (FCF) and Debt Health.
*   *Adaptive Mechanism*: If a metric is missing, its weight is automatically redistributed to other metrics in the same category, ensuring a valid 0-100 score.

### 3. Valuation Blender
to avoid single-model bias, the system aggregates **7 Major Valuation Models** with sector-specific weighting (`valuation_config.py`):
*   **Absolute Valuation**:
    1.  **DCF (Discounted Cash Flow)**: For mature firms with predictable cash flows.
    2.  **DDM (Dividend Discount Model)**: For high-yield sectors (Banks, Utilities).
*   **Relative Valuation**:
    3.  **PE (Price-to-Earnings)**: For profitable, stable firms.
    4.  **PS (Price-to-Sales)**: Critical for high-growth, unprofitable firms (SaaS/Biotech).
    5.  **PB (Price-to-Book)**: Floor logic for asset-heavy or financial firms.
    6.  **EV/EBITDA**: Capital-neutral metric for manufacturing/heavy industry.
*   **Market Consensus**:
    7.  **Analyst Targets**: Incorporates Wall Street sentiment as a reference.

### 4. Data Integrity & Fallback
Uses a cascading fetch strategy: Yahoo (Primary) -> FMP (Secondary) -> Alpha Vantage (Fallback). Ensures analysis completion even if one source fails. (Note: Manual data entry mode has been removed in V3.0 in favor of full automation).

## Future Roadmap

### Integrate SEC EDGAR (Tier 4 Data Source)
Currently, the system uses a 3-tier fallback (Yahoo -> FMP -> Alpha Vantage). To further enhance data authority and reliability, we plan to integrate official SEC EDGAR data as a Tier 4 source.

**Development Guide:**
1.  **Architecture Extension**: 
    - The system has reserved an extension interface. Please refer to `data_acquisition/stock_data/base_fetcher.py`.
    - Create an `EdgarFetcher` class inheriting from `BaseFetcher` and implement the standard interfaces like `fetch_income_statements`.
2.  **Technical Challenges**:
    - **XBRL Parsing**: SEC data is provided in XBRL format, which is complex. It requires mapping hundreds of XBRL tags to the ~70 standardized core fields used in this project (defined in `utils.unified_schema`).
    - **API Interaction**: Requires handling SEC REST API headers (User-Agent must comply with SEC guidelines).
3.  **References**:
    - [SEC EDGAR API Documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
    - [Alpha Vantage Field Documentation](https://documentation.alphavantage.co/FundamentalDataDocs/index.html) (for field mapping reference)

---
Generated by Antigravity Agent
