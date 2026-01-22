"""
Macro Data Aggregator - 宏观数据聚合器

Orchestrates fetching from FRED and Yahoo Finance, combines data,
and saves to CSV (historical) and JSON (snapshot).

协调FRED和Yahoo数据获取，合并数据，并保存为CSV和JSON格式
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
        # ... (rest of init)
        
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
        
        self.csv_path = self.data_dir / 'macro_history.csv'
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
            Combined macro data snapshot
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
            }
        }
        
        # Fetch FRED data
        if self.fred_available:
            try:
                fred_data = self.fred_fetcher.fetch_all()
                snapshot.update({
                    'treasury_yields': fred_data['treasury_yields'],
                    'inflation': fred_data['inflation'],
                    'employment': fred_data.get('employment', {})
                })
                snapshot['data_quality']['fred_status'] = fred_data['status']
                snapshot['data_quality']['warnings'].extend(fred_data['warnings'])
            except Exception as e:
                logger.error(f"FRED fetch failed: {e}")
                snapshot['data_quality']['fred_status'] = 'error'
                snapshot['data_quality']['warnings'].append(f"FRED error: {str(e)}")
        else:
            snapshot['data_quality']['warnings'].append("FRED API not available (check API key)")
        
        # Fetch Yahoo Finance data
        try:
            yahoo_data = self.yahoo_fetcher.fetch_all()
            
            # --- INTERACTIVE PROMPT FOR FORWARD PE ---
            em = yahoo_data.get('equity_market', {})
            
            # If Forward PE is missing, try interactive prompt then fallback
            if not em.get('SPX_forward_pe') and self.interactive_input_func:
                logger.info("Forward PE missing from Yahoo. Requesting user input...")
                
                print("\n" + "!" * 60)
                print("MISSING DATA: SP&500 Forward PE Ratio")
                print("Please check: https://en.macromicro.me/series/20052/sp500-forward-pe-ratio")
                print("!" * 60 + "\n")
                
                user_val = self.interactive_input_func("Enter Forward PE value (or press Enter to skip): ")
                
                if user_val and user_val.strip():
                    try:
                        em['SPX_forward_pe'] = float(user_val.strip())
                        em['SPX_forward_pe_source'] = 'user_input'
                        logger.info(f"Using user-provided Forward PE: {em['SPX_forward_pe']}")
                        # Remove warning about missing PE if present
                        if "Yahoo Forward PE unavailable" in yahoo_data.get('warnings', []):
                             yahoo_data['warnings'].remove("Yahoo Forward PE unavailable")
                    except ValueError:
                        logger.warning("Invalid input for Forward PE. Proceeding to fallback.")
            
            # Fallback to Trailing PE if still no Forward PE
            if not em.get('SPX_forward_pe'):
                trailing = em.get('SPX_trailing_pe')
                if trailing:
                    em['SPX_forward_pe'] = trailing
                    em['SPX_forward_pe_source'] = "trailing_proxy_yahoo"
                    logger.info(f"Fallback: Using Yahoo Trailing PE ({trailing}) as Forward Proxy")
                    yahoo_data['warnings'].append(f"Using Trailing PE ({trailing}) as proxy for Forward PE")
            
            # Clean up temporary field
            if 'SPX_trailing_pe' in em:
                del em['SPX_trailing_pe']

            snapshot.update({
                'market_risk': yahoo_data['market_risk'],
                'equity_market': em,
                'currencies': yahoo_data['currencies']
            })
            snapshot['data_quality']['yahoo_status'] = yahoo_data['status']
            snapshot['data_quality']['warnings'].extend(yahoo_data['warnings'])
        except Exception as e:
            logger.error(f"Yahoo Finance fetch failed: {e}")
            snapshot['data_quality']['yahoo_status'] = 'error'
            snapshot['data_quality']['warnings'].append(f"Yahoo error: {str(e)}")
            
        # ---------------------------------------------------------
        # Derived Metrics & Cross-Source Calculations
        # ---------------------------------------------------------
        
        # ERP (Equity Risk Premium) = (1 / PE) - RiskFree
        try:
            em = snapshot.get('equity_market', {})
            ty = snapshot.get('treasury_yields', {})
            
            pe = em.get('SPX_forward_pe')
            yield_10y = ty.get('GS10_current')
            
            if pe and yield_10y and pe > 0:
                erp = (1 / pe) - (yield_10y / 100.0)
                em['equity_risk_premium'] = erp
                logger.info(f"Calculated ERP: {erp:.2%}")
                
            # Check PE Source Warning
            pe_source = em.get('SPX_forward_pe_source', '')
            if 'trailing_proxy' in str(pe_source):
                warning = f"Using Trailing PE ({pe:.2f}) as proxy for Forward PE"
                snapshot['data_quality']['warnings'].append(warning)
                logger.warning(warning)
                
        except Exception as e:
            logger.warning(f"Failed to calculate derived metrics: {e}")
        
        # Overall status
        fred_ok = snapshot['data_quality']['fred_status'] in ['ok', 'unavailable']
        yahoo_ok = snapshot['data_quality']['yahoo_status'] == 'ok'
        
        if fred_ok and yahoo_ok:
            overall_status = 'ok'
        elif not fred_ok and not yahoo_ok:
            overall_status = 'critical'
        else:
            overall_status = 'degraded'
        
        snapshot['data_quality']['overall_status'] = overall_status
        
        logger.info("=" * 60)
        logger.info(f"Macro data fetch complete. Overall status: {overall_status}")
        logger.info(f"FRED: {snapshot['data_quality']['fred_status']} | Yahoo: {snapshot['data_quality']['yahoo_status']}")
        if snapshot['data_quality']['warnings']:
            logger.warning(f"Total warnings: {len(snapshot['data_quality']['warnings'])}")
            for warning in snapshot['data_quality']['warnings']:
                logger.warning(f"  - {warning}")
        logger.info("=" * 60)
        
        return snapshot
    
    def _flatten_snapshot_for_csv(self, snapshot: Dict) -> pd.DataFrame:
        """
        Flatten snapshot data for CSV storage.
        
        Args:
            snapshot: Macro data snapshot
            
        Returns:
            DataFrame with timestamp, metric_name, value, source columns
        """
        timestamp = snapshot['snapshot_date']
        rows = []
        
        # Treasury yields
        if 'treasury_yields' in snapshot:
            ty = snapshot['treasury_yields']
            if ty.get('GS10_current'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'GS10_current',
                    'value': ty['GS10_current'],
                    'source': 'FRED'
                })
            if ty.get('GS2_current'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'GS2_current',
                    'value': ty['GS2_current'],
                    'source': 'FRED'
                })
            if ty.get('yield_curve_10y_2y'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'yield_curve_10y_2y',
                    'value': ty['yield_curve_10y_2y'],
                    'source': 'FRED'
                })
        
        # Inflation
        if 'inflation' in snapshot:
            inf = snapshot['inflation']
            if inf.get('CPI_latest'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'CPI_latest',
                    'value': inf['CPI_latest'],
                    'source': 'FRED'
                })
        
        # Market risk
        if 'market_risk' in snapshot:
            mr = snapshot['market_risk']
            if mr.get('VIX_current'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'VIX_current',
                    'value': mr['VIX_current'],
                    'source': 'Yahoo'
                })
            if mr.get('VIX_avg'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'VIX_avg',
                    'value': mr['VIX_avg'],
                    'source': 'Yahoo'
                })
            if mr.get('VIX_trend_slope'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'VIX_trend_slope',
                    'value': mr['VIX_trend_slope'],
                    'source': 'Yahoo'
                })
        
        # Equity market
        if 'equity_market' in snapshot:
            em = snapshot['equity_market']
            if em.get('SPX_current'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'SPX_current',
                    'value': em['SPX_current'],
                    'source': 'Yahoo'
                })
            if em.get('SPX_forward_pe'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'SPX_forward_pe',
                    'value': em['SPX_forward_pe'],
                    'source': em.get('SPX_forward_pe_source', 'Yahoo')
                })
            if em.get('equity_risk_premium'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'equity_risk_premium',
                    'value': em['equity_risk_premium'],
                    'source': 'Derived'
                })
        
        # Currencies
        if 'currencies' in snapshot:
            cur = snapshot['currencies']
            if cur.get('DXY_current'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'DXY_current',
                    'value': cur['DXY_current'],
                    'source': 'Yahoo'
                })
            if cur.get('USDJPY_current'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'USDJPY_current',
                    'value': cur['USDJPY_current'],
                    'source': 'Yahoo'
                })
            if cur.get('USDJPY_trend_slope'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'USDJPY_trend_slope',
                    'value': cur['USDJPY_trend_slope'],
                    'source': 'Yahoo'
                })
            if cur.get('AUDUSD_current'):
                rows.append({
                    'timestamp': timestamp,
                    'metric_name': 'AUDUSD_current',
                    'value': cur['AUDUSD_current'],
                    'source': 'Yahoo'
                })
        
        return pd.DataFrame(rows)
    
    def save_snapshot(self, snapshot: Dict):
        """
        Save snapshot to CSV (append) and JSON (overwrite).
        
        Args:
            snapshot: Macro data snapshot to save
        """
        # Save to JSON (latest snapshot)
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved JSON snapshot: {self.json_path}")
        except Exception as e:
            logger.error(f"Failed to save JSON: {e}")
        
        # Save to CSV (append historical data)
        try:
            df = self._flatten_snapshot_for_csv(snapshot)
            
            if len(df) > 0:
                # Append to existing CSV or create new
                if self.csv_path.exists():
                    df.to_csv(self.csv_path, mode='a', header=False, index=False, encoding='utf-8')
                else:
                    df.to_csv(self.csv_path, index=False, encoding='utf-8')
                
                logger.info(f"Appended {len(df)} metrics to CSV: {self.csv_path}")
            else:
                logger.warning("No data to save to CSV")
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")
    
    def run(self) -> Dict[str, Any]:
        """
        Main execution: fetch all data and save.
        
        Returns:
            Macro data snapshot
        """
        snapshot = self.fetch_all_data()
        self.save_snapshot(snapshot)
        return snapshot
    
    def get_summary(self, snapshot: Dict) -> str:
        """
        Generate a human-readable summary of the macro snapshot.
        
        Args:
            snapshot: Macro data snapshot
            
        Returns:
            Summary string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("MACRO ECONOMIC SNAPSHOT")
        lines.append(f"Timestamp: {snapshot['snapshot_date']}")
        lines.append(f"Status: {snapshot['data_quality']['overall_status'].upper()}")
        lines.append("=" * 60)
        
        # Treasury yields
        if 'treasury_yields' in snapshot:
            lines.append("\n📊 Treasury Yields:")
            ty = snapshot['treasury_yields']
            if ty.get('GS10_current'):
                lines.append(f"  10-Year (GS10): {ty['GS10_current']:.2f}%")
            if ty.get('GS2_current'):
                lines.append(f"  2-Year (GS2):   {ty['GS2_current']:.2f}%")
            if ty.get('yield_curve_10y_2y'):
                spread = ty['yield_curve_10y_2y']
                status = "Normal" if spread > 0 else "⚠️ INVERTED"
                lines.append(f"  Yield Curve (10Y-2Y): {spread:+.2f}% ({status})")
        
        # Inflation
        if 'inflation' in snapshot:
            lines.append("\n📈 Inflation:")
            inf = snapshot['inflation']
            if inf.get('CPI_latest'):
                age = f" ({inf.get('data_age_days', '?')} days ago)" if inf.get('data_age_days') else ""
                lines.append(f"  CPI: {inf['CPI_latest']:.1f}{age}")
        
        # Market risk
        if 'market_risk' in snapshot:
            lines.append("\n⚡ Market Risk (VIX):")
            mr = snapshot['market_risk']
            if mr.get('VIX_current'):
                lines.append(f"  Current: {mr['VIX_current']:.2f}")
            if mr.get('VIX_avg'):
                lines.append(f"  10-Day Avg: {mr['VIX_avg']:.2f}")
            if mr.get('VIX_trend_direction'):
                trend_emoji = {"rising": "📈", "declining": "📉", "stable": "➡️"}.get(mr['VIX_trend_direction'], "")
                lines.append(f"  Trend: {trend_emoji} {mr['VIX_trend_direction'].upper()}")
        
        # Equity market
        if 'equity_market' in snapshot:
            lines.append("\n🏛️ Equity Market (S&P 500):")
            em = snapshot['equity_market']
            if em.get('SPX_current'):
                lines.append(f"  Level: {em['SPX_current']:.2f}")
            if em.get('SPX_forward_pe'):
                source = em.get('SPX_forward_pe_source', 'unknown')
                lines.append(f"  Forward PE: {em['SPX_forward_pe']:.2f} (source: {source})")
        
        # Currencies
        if 'currencies' in snapshot:
            lines.append("\n💱 Currencies:")
            cur = snapshot['currencies']
            if cur.get('DXY_current'):
                lines.append(f"  Dollar Index (DXY): {cur['DXY_current']:.2f}")
            if cur.get('USDJPY_current'):
                trend = cur.get('USDJPY_trend_direction', '')
                trend_emoji = {"rising": "📈", "declining": "📉", "stable": "➡️"}.get(trend, "")
                lines.append(f"  USD/JPY: {cur['USDJPY_current']:.2f} {trend_emoji}")
            if cur.get('AUDUSD_current'):
                lines.append(f"  AUD/USD: {cur['AUDUSD_current']:.4f}")
        
        # Warnings
        warnings = snapshot['data_quality'].get('warnings', [])
        if warnings:
            lines.append(f"\n⚠️ Warnings ({len(warnings)}):")
            for warning in warnings[:5]:  # Show first 5
                lines.append(f"  - {warning}")
            if len(warnings) > 5:
                lines.append(f"  ... and {len(warnings) - 5} more")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
