# Utilities Reference

This document provides a comprehensive guide to the `utils/` directory, which contains the system's core infrastructure, data schemas, and helper functions.

> **⚠️ Developer Notice**
>
> Before writing new modules or modifying existing code, ensure you:
>
> 1. **Numeric calculations** → Use `clean_numeric()` / `safe_divide()` from `numeric_utils.py`. Never use raw Python division.
> 2. **HTTP requests** → Use `make_request()` from `http_utils.py`. Never use `requests.get()` directly (built-in retry & error handling).
> 3. **Logging** → Use `setup_logger()` from `logger.py`. Avoid using `print()` for debugging.
> 4. **New data fields** → Must update both `unified_schema.py` AND `field_registry.py`.
> 5. **Display formatting** → Use `safe_format()` and `format_large_number()` to safely handle None/NaN values.
>
> Quick Reference: See `utils/__init__.py` for a complete tool lookup table.

## 1. Core Data Infrastructure

### `unified_schema.py`

- **Purpose**: Defines the "System Constitution" using Pydantic models.
- **Key Models**:
  - `StockData`: The master object containing all data for a single stock.
  - `IncomeStatement`, `BalanceSheet`, `CashFlow`: Standardized financial statements.
  - `CompanyProfile`: Metadata like sector, industry, and description.
  - `ForecastData`: **[NEW]** Forward-looking analyst data model containing:
    - Forward EPS/PE (`std_forward_eps`, `std_forward_pe`)
    - Growth estimates (`std_earnings_growth_current_year`, `std_revenue_growth_next_year`)
    - Analyst price targets (`std_price_target_low/high/consensus`)
    - Earnings Surprise History (`std_earnings_surprise_history`) - Latest 4 quarters
  - `FieldWithSource`: Tracking value provenance (e.g., source: 'yahoo').
- **Usage**: All data fetching modules must conform to these schemas.

### `field_registry.py`

- **Purpose**: Central registry for mapping raw API fields to unified schema names.
- **Key Features**:
  - **Multi-Source Mapping**: Maps `std_revenue` to:
    - Yahoo: `Total Revenue`
    - EDGAR: `Revenues`, `SalesRevenueNet`
    - FMP: `revenue`
    - Alpha Vantage: `totalRevenue`
  - **Priority Logic**: Defines which source wins during data merging (Default: Yahoo > FMP > EDGAR > AV).
- **Customization**: Add new XBRL tags or API field names here to improve data fetching success rates.

### `schema_mapper.py`

- **Purpose**: Logic for converting raw JSON inputs into `unified_schema` objects using `field_registry` definitions.

### `currency_normalizer.py`

- **Purpose**: **Automatic currency conversion and ADR share normalization** for international stocks.
- **Key Features**:
  - **Global Currency Conversion**: Detects and converts foreign currency (e.g., TWD, HKD) financial data to USD using real-time FX rates.
  - **ADR Share Normalization**: Calculates implied ADR share count from market cap and adjusts EPS accordingly.
  - **Multi-Layer Protection**:  
    - Converts 255+ monetary fields across all data sources (Yahoo, FMP, EDGAR, Alpha Vantage).
    - Recalculates EPS using: `EPS_USD = Net_Income_USD / ADR_Shares`.
    - Prevents re-conversion of already processed data (source='manual').
- **Supported Stocks**: Primarily ADRs (TSM, BABA, JD) but applicable to any stock reporting in non-USD currencies.
- **Technical Note**: Triggered automatically when `FinancialCurrency != ListingCurrency` in company profile.

---

## 2. Metrics & Definitions

### `metric_registry.py`

- **Purpose**: The "Dictionary" of all financial and technical indicators.
- **Content**:
  - Defines metric keys (e.g., `roic`, `rsi`).
  - Stores display names in English and Chinese.
  - Sets formatting rules (Percentage, Currency, Decimal).
- **Usage**: Used by report generators to render consistent labels and formats.

### `macro_translations.py`

- **Purpose**: Translation dictionary for the Macro Analysis module.
- **Content**: Maps macro keys (e.g., `gdp`, `cpi`) and UI elements to English and Chinese for bilingual reporting.

---

## 3. Helper Libraries

### `numeric_utils.py`

- **Purpose**: Safe mathematical operations.
- **Functions**:
  - `safe_float()`: Robust string-to-float conversion (handles "N/A", "--").
  - `calculate_cagr()`: Compound Annual Growth Rate calculation.
  - `calculate_growth_rate()`: Period-over-period growth.
  - `safe_divide()`: Division with zero-division protection.

### `http_utils.py`

- **Purpose**: Network request handling.
- **Features**:
  - `fetch_url()`: Wrapper with headers (User-Agent rotation) and error handling.
  - `RateLimiter`: Validates and throttles API requests (especially for Alpha Vantage/FMP).

### `helpers.py`

- **Purpose**: General purpose utilities.
- **Functions**:
  - Date parsing and formatting.
  - File I/O helpers.
  - String manipulation tools.

---

## 4. Logging & Output

### `logger.py`

- **Purpose**: Central logging configuration.
- **Features**:
  - Multi-level logging (INFO, DEBUG, ERROR).
  - File rotation logic.
  - Console output formatting.

### `console_utils.py`

- **Purpose**: Utilities for rich console output (colors, tables).
- **Features**:
  - Progress bars.
  - Colored status messages (Success, Warning, Error).

---

## 5. Reporting

### `report_utils.py`

- **Purpose**: Utilities for generating text and markdown reports.
- **Features**:
  - Helper functions to format data tables in Markdown.
  - Template rendering helpers.

---

## Quick Map

| File | Purpose |
| :--- | :--- |
| `unified_schema.py` | **Data Models** (The "What") |
| `field_registry.py` | **Data Mapping** (The "Where") |
| `currency_normalizer.py` | **Currency Conversion & ADR Normalization** |
| `metric_registry.py` | **Metric Definitions** (The "Definition") |
| `numeric_utils.py` | **Math** (CAGR, Growth, Safe Float) |
| `http_utils.py` | **Network** (Fetch, Rate Limit) |
| `logger.py` | **Logging** |
