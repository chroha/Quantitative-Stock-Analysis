# Configuration Reference

This document lists all configuration files in the project that users can customize.

## 1. Core Configuration (`config/`)

### `config/settings.py`

- **Purpose**: API keys and environment settings
- **Loads from**: `user_config/.env`
- **Key Variables**:
  - `GOOGLE_AI_KEY`: Gemini API key for AI commentary
  - `FMP_API_KEY`: Financial Modeling Prep API key
  - `FRED_API_KEY`: FRED API key for macro data
  - `ALPHA_VANTAGE_KEY`: Alpha Vantage API key

### `config/constants.py`

- **Purpose**: Path constants and directory structure
- **Key Variables**:
  - `DATA_CACHE_STOCK`: Stock data cache directory
  - `DATA_CACHE_MACRO`: Macro data cache directory
  - `DATA_CACHE_BENCHMARK`: Benchmark data cache directory
  - `DATA_REPORTS`: Generated reports directory

### `config/analysis_config.py`

- **Purpose**: Analysis thresholds and validation parameters
- **Customizable**:
  - `DATA_SUFFICIENCY_CONFIG`: Historical data completeness thresholds
  - `DATA_FETCH_GAP_THRESHOLDS`: Acceptable data gap percentages
  - `VALUATION_THRESHOLDS`: Valuation assessment boundaries
  - `METRIC_BOUNDS`: Ratio validation boundaries

---

## 2. Financial Scoring (`fundamentals/financial_scorers/`)

### `scoring_config.py` (Financial)

- **Purpose**: Financial metric scoring weights and thresholds
- **Customizable**:
  - `CATEGORY_WEIGHTS`: Profitability/Growth/Capital allocation weights
  - `SECTOR_WEIGHT_OVERRIDES`: Sector-specific adjustments
  - `TIER3_THRESHOLDS`: Absolute scoring thresholds for each metric
  - Scoring functions for special metrics (share dilution, SBC, etc.)

---

## 3. Technical Scoring (`fundamentals/technical_scorers/`)

### `scoring_config.py` (Technical)

- **Purpose**: Technical indicator scoring parameters
- **Customizable**:
  - `CATEGORY_WEIGHTS`: Trend/Momentum/Volatility/Structure/Volume weights
  - `MA_CONFIG`: Moving average periods
  - `RSI_CONFIG`: RSI thresholds and scoring
  - `ADX_CONFIG`: Trend strength thresholds
  - `BOLLINGER_CONFIG`: Bollinger Band parameters
  - `ATR_CONFIG`: Volatility scoring
  - `VOLUME_CONFIG`: Volume analysis parameters

---

## 4. Valuation (`fundamentals/valuation/`)

### `valuation_config.py`

- **Purpose**: Sector-specific valuation method weights
- **Customizable**:
  - `SECTOR_WEIGHTS`: 11 GICS sectors with 10 valuation method weights each
  - Methods: PE, PB, PS, EV/EBITDA, DCF, DDM, Graham, Peter Lynch, PEG, Analyst

---

## 5. Macro Analysis (`data_acquisition/macro_data/`)

### `macro_config.py`

- **Purpose**: Macro data fetching and analysis parameters
- **Customizable**:
  - `LOOKBACK_WEEKS`: Historical data lookback period
  - `CACHE_TTL_HOURS`: Cache expiration time
  - `TREND_THRESHOLD`: Trend significance threshold
  - `MA_PERIOD`: Moving average period for trend calculation

---

## 6. User Configuration (`user_config/`)

### `.env`

- **Purpose**: API keys (sensitive data, git-ignored)
- **Required Keys**:

  ```env
  FMP_API_KEY=your_fmp_key
  FRED_API_KEY=your_fred_key
  GOOGLE_AI_KEY=your_gemini_key
  ALPHA_VANTAGE_KEY=your_av_key
  ```

### `.env.example`

- **Purpose**: Template for `.env` file

---

## Quick Reference Table

| Config File | Location | Purpose |
| :--- | :--- | :--- |
| `settings.py` | `config/` | API keys, environment |
| `constants.py` | `config/` | Paths, directories |
| `analysis_config.py` | `config/` | Data quality thresholds |
| `scoring_config.py` | `fundamentals/financial_scorers/` | Financial scoring weights |
| `scoring_config.py` | `fundamentals/technical_scorers/` | Technical scoring params |
| `valuation_config.py` | `fundamentals/valuation/` | Sector valuation weights |
| `macro_config.py` | `data_acquisition/macro_data/` | Macro data settings |
| `.env` | `user_config/` | API keys (create from .env.example) |

---

## Notes

1. **Do not commit `.env`** - It contains sensitive API keys
2. **Sector weights sum to 1.0** - When modifying valuation weights, ensure they sum to 100%
3. **Test after changes** - Run `python run_analysis.py AAPL` to verify configuration changes
