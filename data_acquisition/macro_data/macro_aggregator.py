"""
Macro Data Aggregator - 宏观数据聚合器

Orchestrates fetching from FRED and Yahoo Finance, combines data,
and saves to JSON (snapshot). Historical CSV logging is currently suspended due to schema changes.

协调FRED和Yahoo数据获取，合并数据，并保存为JSON格式
"""

import json
import pandas as pd
import json
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from utils.logger import setup_logger
import pytz

from .fred_fetcher import FREDFetcher
from .yahoo_macro_fetcher import YahooMacroFetcher

logger = setup_logger('macro_aggregator')


class MacroAggregator:
    """Aggregates macro data from multiple sources."""
    
    
    def __init__(self, fred_api_key: Optional[str] = None, config: Optional[Dict] = None, 
                 interactive_input_func: Optional[Any] = None):
        """
        Initialize macro aggregator.
        
        Args:
            fred_api_key: FRED API key (or use FRED_API_KEY env var)
            config: Configuration dict
            interactive_input_func: Function to call for user input if data missing (e.g. Forward PE)
        """
        self.config = config or self._load_default_config()
        self.interactive_input_func = interactive_input_func
        
        # Initialize fetchers
        try:
            self.fred_fetcher = FREDFetcher(api_key=fred_api_key, config=self.config)
            self.fred_available = True
        except Exception as e:
            logger.error(f"Failed to initialize FRED fetcher: {e}")
            self.fred_fetcher = None
            self.fred_available = False
        
        self.yahoo_fetcher = YahooMacroFetcher(config=self.config)
        
        # Setup data directory
        self.data_dir = Path(__file__).parent / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.json_path = self.data_dir / 'macro_latest.json'

    def _load_default_config(self) -> Dict:
        """Load default configuration."""
        config_path = Path(__file__).parent / 'macro_config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}

    def fetch_all_data(self) -> Dict[str, Any]:
        """
        Fetch all macro data from FRED and Yahoo Finance.
        
        Returns:
            Combined macro data snapshot suitable for Dashboard
        """
        logger.info("=" * 60)
        logger.info("MACRO DATA AGGREGATOR - Starting data fetch")
        logger.info("=" * 60)

        # Get current time with local timezone (system)
        local_tz = datetime.now().astimezone().tzinfo
        now = datetime.now(local_tz)
        
        snapshot = {
            'snapshot_date': now.isoformat(),
            'data_quality': {
                'fred_status': 'unavailable',
                'yahoo_status': 'unknown',
                'warnings': []
            },
            'dashboard_data': {
                'assets': {},
                'economic': {},
                'internals': {},
                'sectors': {}
            }
        }
        
        # 1. Fetch FRED data
        fred_data = {}
        if self.fred_available:
            try:
                fred_data = self.fred_fetcher.fetch_all()
                snapshot['data_quality']['fred_status'] = fred_data.get('status', 'unknown')
                snapshot['data_quality']['warnings'].extend(fred_data.get('warnings', []))
            except Exception as e:
                logger.error(f"FRED fetch failed: {e}")
                snapshot['data_quality']['fred_status'] = 'error'
                snapshot['data_quality']['warnings'].append(f"FRED error: {str(e)}")
        else:
            snapshot['data_quality']['warnings'].append("FRED API not available")
        
        # 2. Fetch Yahoo Finance data
        yahoo_data = {}
        try:
            yahoo_data = self.yahoo_fetcher.fetch_all()
            snapshot['data_quality']['yahoo_status'] = yahoo_data.get('status', 'unknown')
            snapshot['data_quality']['warnings'].extend(yahoo_data.get('warnings', []))
        except Exception as e:
            logger.error(f"Yahoo Finance fetch failed: {e}")
            snapshot['data_quality']['yahoo_status'] = 'error'
            snapshot['data_quality']['warnings'].append(f"Yahoo error: {str(e)}")

        # ---------------------------------------------------------
        # Assemble Dashboard Data Structure
        # ---------------------------------------------------------
        
        # A. Asset Performance (from Yahoo)
        # Groups: Indices, Commodities, Crypto, Currencies
        y_data = yahoo_data.get('data', {})
        
        snapshot['dashboard_data']['assets'] = {
            'Indices': {
                'S&P 500': y_data.get('SP500_ETF'),
                'Russell 2000': y_data.get('Russell2000_ETF'),
            },
            'Commodities': {
                'Crude Oil': y_data.get('Crude_Oil'),
                'Gold': y_data.get('Gold'),
                'Copper': y_data.get('Copper'),
            },
            'Crypto': {
                'Bitcoin': y_data.get('Bitcoin'),
            },
            'Currencies': {
                'DXY (USD)': y_data.get('DXY'),
                'USD/JPY': y_data.get('USDJPY'),
                'AUD/USD': y_data.get('AUDUSD'),
                'AUD/CNY': y_data.get('AUDCNY')
            }
        }
        
        # B. Economic Indicators (from FRED)
        f_emp = fred_data.get('employment', {})
        f_inf = fred_data.get('inflation', {})
        f_trs = fred_data.get('treasury_yields', {})
        f_rsk = fred_data.get('risk_sentiment', {})
        
        def get_trend(curr, prev):
            if curr is None or prev is None: return "stable"
            return "up" if curr > prev else "down" if curr < prev else "stable"

        snapshot['dashboard_data']['economic'] = {
            'Growth & Labor': {
                'Unemployment Rate': f_emp.get('UNRATE'),
                'Initial Claims': f_emp.get('ICSA'),
            },
            'Inflation': {
                'CPI (YoY)': {
                    'value': f_inf.get('CPI_YOY'),
                    'date': f_inf.get('CPI_date'),
                    'prev_value': f_inf.get('CPI_YOY_prev'),
                    'trend': get_trend(f_inf.get('CPI_YOY'), f_inf.get('CPI_YOY_prev'))
                }, 
                'CPI Index': {
                    'value': f_inf.get('CPI_latest'),
                    'date': f_inf.get('CPI_date'),
                    'prev_value': f_inf.get('CPI_prev'),
                    'trend': get_trend(f_inf.get('CPI_latest'), f_inf.get('CPI_prev'))
                },
                'CPI Context': f_inf # Full object for details
            },
            'Rates & liquidity': {
                '10Y Treasury': {
                    'value': f_trs.get('GS10_current'),
                    'date': f_trs.get('yield_date'),
                    'prev_value': f_trs.get('GS10_prev'),
                    'trend': get_trend(f_trs.get('GS10_current'), f_trs.get('GS10_prev'))
                },
                '10Y-2Y Spread': {
                    'value': f_trs.get('yield_curve_10y_2y'),
                    'date': f_trs.get('yield_date'),
                    'prev_value': f_trs.get('yield_curve_10y_2y_prev'),
                    'trend': get_trend(f_trs.get('yield_curve_10y_2y'), f_trs.get('yield_curve_10y_2y_prev'))
                },
                'HY Spread': f_rsk.get('HY_SPREAD'),
                'Fin Stress Idx': f_rsk.get('STLFSI3')
            },
            'Sentiment': {
                'Consumer Sent': f_rsk.get('UMCSENT') # Contains date inside
            }
        }
        
        # C. Market Internals (from Yahoo)
        vix_struct = y_data.get('VIX_Structure', {})
        snapshot['dashboard_data']['internals'] = {
            'Style_Ratio': y_data.get('Style_Ratio'),
            'Size_Ratio': y_data.get('Size_Ratio'),
            'VIX_Structure': {
                "ratio": vix_struct.get('ratio'),
                "signal": vix_struct.get('signal'),
                "sma20": vix_struct.get('sma20')
            },
            'VIX_Level': y_data.get('VIX')
        }

        # D. Sectors (from Yahoo)
        # Using tickers as keys since they are unique and standard
        sector_tickers = ['XLK', 'XLC', 'XLY', 'XLE', 'XLF', 'XLI', 'XLB', 'XLRE', 'XLP', 'XLV', 'XLU']
        for sec in sector_tickers:
             snapshot['dashboard_data']['sectors'][sec] = y_data.get(sec) # Fetcher keys are tickers for sectors

        # ---------------------------------------------------------
        # Backwards Compatibility & Valuation Logic
        # ---------------------------------------------------------
        
        # 1. Initialize 'equity_market' in snapshot
        # Using SPY as proxy for SPX level if available
        spx_price = y_data.get('SP500_ETF', {}).get('price')
        
        snapshot['equity_market'] = {
            'SPX_current': spx_price,
            'SPX_forward_pe': None,
            'equity_risk_premium': None 
        }
        
        # 2. Interactive Prompt for Forward PE
        # This is critical for the Valuation Module
        em = snapshot['equity_market']
        
        if self.interactive_input_func:
            # We don't have PE in batch data, so we always ask if not provided
            # (Or we could fetch trailing PE as a crude proxy, but better to ask)
            
            # Check if we have a cached value from a previous run? 
            # (Not implemented complexity, just ask user)
            
            print("\n" + "!" * 60)
            print("Action Required: S&P 500 Forward PE Ratio")
            print("The Valuation Model requires this metric to calculate ERP.")
            print("Please check: https://en.macromicro.me/series/20052/sp500-forward-pe-ratio")
            print("Typical range: 15.0 - 25.0")
            print("!" * 60 + "\n")
            
            try:
                user_val = self.interactive_input_func("Enter Forward PE value (e.g. 21.5): ")
                if user_val and user_val.strip():
                    em['SPX_forward_pe'] = float(user_val.strip())
                    em['SPX_forward_pe_source'] = 'user_input'
                    logger.info(f"Using user-provided Forward PE: {em['SPX_forward_pe']}")
            except Exception as e:
                logger.warning(f"Invalid input: {e}")

        # 3. Fallback
        if em['SPX_forward_pe'] is None:
            # Default fallback to ensure model runs even without user input
            fallback_val = 22.5
            em['SPX_forward_pe'] = fallback_val
            em['SPX_forward_pe_source'] = 'fallback_default'
            logger.warning(f"Forward PE missing. Using fallback: {fallback_val}") 
        
        # If still None, the Valuation module will fail or return None.
        
        # ---------------------------------------------------------
        # Derived Metrics (ERP)
        # ---------------------------------------------------------
        # ERP = (1 / PE) - RiskFree (10Y)
        try:
            pe = em.get('SPX_forward_pe')
            # 10Y Yield might look like 4.25 (percent)
            gs10 = f_trs.get('GS10_current')
            
            if pe and gs10:
                yield_decimal = gs10 / 100.0
                earnings_yield = 1.0 / pe
                erp = earnings_yield - yield_decimal
                
                em['equity_risk_premium'] = erp
                logger.info(f"Calculated ERP: {erp:.2%}")
        except Exception as e:
            logger.warning(f"Could not calculate ERP: {e}")

        # Construct Legacy Mappings
        snapshot['treasury_yields'] = f_trs
        snapshot['inflation'] = f_inf
        snapshot['employment'] = f_emp
        # Legacy mapping for CycleAnalyzer
        if f_emp.get('UNRATE'):
            snapshot['employment']['UNRATE_current'] = f_emp['UNRATE'].get('value') if isinstance(f_emp['UNRATE'], dict) else f_emp['UNRATE']
        
        # VIX Trend derivation for legacy RiskAssessor
        vix_data = y_data.get('VIX', {})
        vix_trend = "stable"
        change_1d = vix_data.get('change_1d', 0) 
        if change_1d and change_1d > 0.05:
            vix_trend = "rising"
        elif change_1d and change_1d < -0.05:
            vix_trend = "declining"
            
        snapshot['market_risk'] = {
            'VIX_current': vix_data.get('price'),
            'VIX_trend_direction': vix_trend
        }
        
        snapshot['currencies'] = {
            'DXY_current': y_data.get('DXY', {}).get('price'),
            'USDJPY_current': y_data.get('USDJPY', {}).get('price'),
            'AUDUSD_current': y_data.get('AUDUSD', {}).get('price')
        }

        # Overall Status
        f_ok = snapshot['data_quality']['fred_status'] in ['ok', 'unavailable', 'degraded']
        y_ok = snapshot['data_quality']['yahoo_status'] == 'ok'
        
        if f_ok and y_ok:
            snapshot['data_quality']['overall_status'] = 'ok'
        else:
            snapshot['data_quality']['overall_status'] = 'degraded'
        
        return snapshot
    
    def save_snapshot(self, snapshot: Dict):
        """
        Save snapshot to JSON (overwrite).
        """
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved JSON snapshot: {self.json_path}")
        except Exception as e:
            logger.error(f"Failed to save JSON: {e}")
            
    def run(self) -> Dict[str, Any]:
        """
        Main execution: fetch all data and save.
        """
        snapshot = self.fetch_all_data()
        self.save_snapshot(snapshot)
        return snapshot
    
    def get_summary(self, snapshot: Dict) -> str:
        """
        Generate a human-readable summary of the macro snapshot.
        """
        # Minimal implementation for console feedback
        data = snapshot.get('dashboard_data', {})
        assets = data.get('assets', {})
        
        lines = []
        lines.append("=" * 60)
        lines.append("MACRO DASHBOARD SNAPSHOT")
        lines.append(f"Timestamp: {snapshot.get('snapshot_date')}")
        lines.append("=" * 60)
        
        lines.append("\n[Asset Performance 1D%]")
        for category, items in assets.items():
            line_parts = []
            for name, details in items.items():
                if details and 'change_1d_safe' in details:
                    chg = details['change_1d_safe'] * 100
                    line_parts.append(f"{name}: {chg:+.2f}%")
            if line_parts:
                lines.append(f"{category}: " + " | ".join(line_parts))
                
        return "\n".join(lines)
