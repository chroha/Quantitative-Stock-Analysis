"""
Currency Normalizer Utility
===========================

Handles conversion of financial statements from reporting currency (e.g., TWD)
to listing currency (e.g., USD) for ADRs and international stocks.
"""

import yfinance as yf
from typing import Optional
from utils.unified_schema import StockData, FieldWithSource
from utils.logger import setup_logger

logger = setup_logger('currency_normalizer')

class CurrencyNormalizer:
    """
    Normalizes StockData currency and share counts.
    """
    
    MONETARY_FIELDS = [
        'std_revenue', 'std_cost_of_revenue', 'std_gross_profit', 'std_operating_income',
        'std_pretax_income', 'std_interest_expense', 'std_income_tax_expense',
        'std_net_income', 'std_ebitda', 'std_ebit', 'std_operating_expenses',
        'std_total_assets', 'std_current_assets', 'std_cash', 'std_accounts_receivable',
        'std_inventory', 'std_total_liabilities', 'std_current_liabilities',
        'std_total_debt', 'std_shareholder_equity',
        'std_operating_cash_flow', 'std_investing_cash_flow', 'std_financing_cash_flow',
        'std_capex', 'std_free_cash_flow', 'std_dividends_paid', 'std_stock_based_compensation',
        'std_repurchase_of_stock', 'std_eps', 'std_eps_diluted'
    ]

    @classmethod
    def normalize(cls, data: StockData) -> StockData:
        """
        Detect and resolve currency mismatch in StockData.
        
        Args:
            data: StockData object to normalize
            
        Returns:
            Normalized StockData object
        """
        if not data.profile:
            return data
            
        fin_currency = data.profile.std_financial_currency.value if data.profile.std_financial_currency else None
        list_currency = data.profile.std_listing_currency.value if data.profile.std_listing_currency else None
        
        if not fin_currency or not list_currency or fin_currency == list_currency:
            return data
            
        logger.info(f"[{data.symbol}] Currency mismatch: Financials in {fin_currency}, Listing in {list_currency}")
        
        # 1. Fetch FX Rate
        fx_rate = cls._fetch_fx_rate(fin_currency, list_currency)
        if not fx_rate or fx_rate == 1.0:
            logger.warning(f"[{data.symbol}] Could not fetch valid FX rate for {fin_currency}{list_currency}=X. Skipping conversion.")
            return data
            
        logger.info(f"[{data.symbol}] Applying FX Rate: {fx_rate:.4f}")
        
        # 2. Convert monetary fields in statements
        cls._convert_statements(data, fx_rate)
        
        # 3. Handle ADR Share Normalization
        # Implied Shares = Market Cap / Current Price
        # ADR Market Cap in Yahoo matches Listing Currency USD.
        # If Shares Outstanding is in Local Units (20B for TSM), it will cause PE mismatch.
        # We calculate Implied ADR Shares from Market Cap and Current Price (both in Listing Currency).
        implied_adr_shares = cls._calculate_implied_adr_shares(data)
        
        if implied_adr_shares:
            logger.info(f"[{data.symbol}] Using Implied ADR Shares: {implied_adr_shares:,.0f}")
            cls._apply_adr_normalization(data, implied_adr_shares)
        
        # Update metadata
        data.metadata['currency_normalized'] = True
        data.metadata['fx_rate'] = fx_rate
        data.metadata['implied_adr_shares'] = implied_adr_shares
        
        return data

    @staticmethod
    def _fetch_fx_rate(base: str, target: str) -> float:
        """Fetch FX rate from Yahoo Finance."""
        try:
            symbol = f"{base}{target}=X"
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                return hist['Close'].iloc[-1]
            return 1.0
        except Exception as e:
            logger.warning(f"FX fetch failed for {base}{target}: {e}")
            return 1.0

    @classmethod
    def _convert_statements(cls, data: StockData, fx_rate: float):
        """Apply FX rate to all monetary fields in financial statements (Global Coverage)."""
        logger.info(f"[{data.symbol}] Converting ALL monetary fields (Rate: {fx_rate:.4f})...")
        converted_count = 0
        
        # Helper to process a list of statements in place
        def process_list(stmt_list, name):
            count = 0
            for stmt in stmt_list:
                for field in cls.MONETARY_FIELDS:
                    val_obj = getattr(stmt, field, None)
                    if val_obj and val_obj.value is not None:
                        # CRITICAL: We no longer check source == 'yahoo'. 
                        # Many sources (FMP/SEC) still provide TWD if the company reports in TWD.
                        # However, we only convert IF the value is Large (> 1M), 
                        # or if we are confident it hasn't been converted already.
                        # Rule: If it's sourced from 'manual', it's already converted.
                        if val_obj.source == 'manual':
                            continue
                            
                        old_val = val_obj.value
                        new_val = old_val * fx_rate
                        
                        # Use setattr with a fresh FieldWithSource
                        new_obj = FieldWithSource(value=new_val, source='normalized')
                        setattr(stmt, field, new_obj)
                        
                        if count < 3: # Minimal trace
                            logger.info(f"  [{name}][{stmt.std_period}] {field}: {old_val:,.0f} -> {new_val:,.0f}")
                        count += 1
            return count

        converted_count += process_list(data.income_statements, "Income")
        converted_count += process_list(data.balance_sheets, "Balance")
        converted_count += process_list(data.cash_flows, "CashFlow")
        
        logger.info(f"[{data.symbol}] Total converted fields: {converted_count}")

    @staticmethod
    def _calculate_implied_adr_shares(data: StockData) -> Optional[float]:
        """Calculate implied ADR shares from Market Cap and Price."""
        if not data.profile:
            return None
            
        # 1. Check if profile already has a reliable share count from Yahoo
        # For TSM, Yahoo's sharesOutstanding in 'info' is 5.18B (ADR count)
        profile_shares_obj = data.profile.std_shares_outstanding
        profile_shares = profile_shares_obj.value if profile_shares_obj else None
        
        # 2. Get latest price from history
        if not data.price_history:
            return profile_shares
        latest_price = data.price_history[0].std_close.value
        
        # 3. Get Market Cap
        mkt_cap_obj = data.profile.std_market_cap
        mkt_cap = mkt_cap_obj.value if mkt_cap_obj else None
        
        if not mkt_cap or not latest_price or latest_price <= 0:
            return profile_shares
            
        profile_shares_str = f"{profile_shares:,.0f}" if profile_shares is not None else "None"
        logger.info(f"[{data.symbol}] MC: {mkt_cap:,.0f} (Source: {mkt_cap_obj.source}), Price: {latest_price:.2f}, Profile Shares: {profile_shares_str}")
        
        implied = mkt_cap / latest_price
        
        # Logic: If profile_shares exists, compare with implied (Mc/Price).
        # We prefer profile_shares (reliable count) if it's in the same ballpark.
        # If profile_shares is 25B and implied is 5B, then profile_shares is likely "local" (TWD) shares.
        
        if profile_shares:
            # Ballpark check (20% margin)
            if 0.5 <= (profile_shares / implied) <= 1.5:
                # Close enough, use profile count for precision
                return profile_shares
            
            # If profile is much larger than implied, use implied (it's the ADR count)
            if profile_shares > implied * 2:
                logger.info(f"[{data.symbol}] Profile shares ({profile_shares:,.0f}) look like local units. Using implied ADR shares ({implied:,.0f}).")
                return implied
                
        return implied

    @staticmethod
    def _apply_adr_normalization(data: StockData, adr_shares: float):
        """Apply ADR share count and recalculate EPS."""
        logger.info(f"[{data.symbol}] Applying ADR Normalization (Shares: {adr_shares:,.0f})...")
        for stmt in data.income_statements:
            # Update shares outstanding to ADR count
            stmt.std_shares_outstanding = FieldWithSource(value=adr_shares, source='manual')
            
            # Recalculate EPS = Net Income / ADR Shares
            # This is the most reliable way to get USD EPS for an ADR
            if stmt.std_net_income and stmt.std_net_income.value is not None:
                new_eps = stmt.std_net_income.value / adr_shares
                stmt.std_eps = FieldWithSource(value=new_eps, source='manual')
                stmt.std_eps_diluted = FieldWithSource(value=new_eps, source='manual')
                
                # Trace one
                if stmt.std_period_type == 'FY':
                    logger.info(f"  [{stmt.std_period}] Recalculated EPS: {new_eps:.2f} (NetInc: {stmt.std_net_income.value:,.0f} / Shares: {adr_shares:,.0f})")
        
        # Sync profile metrics
        ttm_inc = next((s for s in data.income_statements if s.std_period_type == 'TTM'), None)
        if ttm_inc and ttm_inc.std_eps and data.profile:
            data.profile.std_eps = ttm_inc.std_eps
            
        if ttm_inc and ttm_inc.std_shares_outstanding and data.profile:
            data.profile.std_shares_outstanding = ttm_inc.std_shares_outstanding
