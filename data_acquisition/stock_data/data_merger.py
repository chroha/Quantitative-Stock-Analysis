"""
Data merger - utility functions for combining data from multiple sources.
Priority: Yahoo > FMP > Alpha Vantage > Manual
[INTERNAL PROCESS MODULE] - This module is used by StockDataLoader, do not call directly.
"""

from typing import Optional
from utils.logger import setup_logger
from utils.unified_schema import (
    CompanyProfile, FieldWithSource, TextFieldWithSource
)

logger = setup_logger('data_merger')

# Sector name normalization mapping
# Maps variations from different data sources to standardized GICS sector names
SECTOR_NORMALIZATION_MAP = {
    "Financial Services": "Financials",
    "Basic Materials": "Materials",
    "Telecommunication Services": "Communication Services",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    # Add more mappings as encountered
}


class DataMerger:
    """
    智能合并多源数据的工具类。
    Utility class for intelligently merging data from multiple sources.
    """

    @staticmethod
    def _fill_missing_fields_in_stmt(target_stmt, source_stmt) -> int:
        """
        Fill missing fields (None or Value=None) in target_stmt using values from source_stmt.
        Returns number of fields filled.
        """
        filled_count = 0
        
        if not target_stmt or not source_stmt:
            return 0
            
        # Get all fields
        fields = target_stmt.model_fields.keys()
        
        for field_name in fields:
            if field_name == 'std_period': 
                continue
                
            current_val = getattr(target_stmt, field_name)
            source_val = getattr(source_stmt, field_name)
            
            # Check if current is 'empty'
            is_empty = False
            if current_val is None:
                is_empty = True
            elif isinstance(current_val, FieldWithSource) and current_val.value is None:
                is_empty = True
                
            # If empty, try to fill from source
            if is_empty and source_val is not None:
                if isinstance(source_val, FieldWithSource) and source_val.value is not None:
                    setattr(target_stmt, field_name, source_val)
                    filled_count += 1
        
        return filled_count
        
    @staticmethod
    def _merge_field(
        primary: Optional[FieldWithSource],
        secondary: Optional[FieldWithSource]
    ) -> Optional[FieldWithSource]:
        """Merge a single field, prioritizing primary source."""
        if primary and primary.value is not None:
            return primary
        if secondary and secondary.value is not None:
            return secondary
        return None
    
    @staticmethod
    def normalize_sector(sector_field: Optional[TextFieldWithSource]) -> Optional[TextFieldWithSource]:
        """
        Normalize sector name to standard GICS sector names.
        Maps common variations (e.g., 'Financial Services' -> 'Financials').
        
        Args:
            sector_field: TextFieldWithSource containing sector name
            
        Returns:
            Normalized TextFieldWithSource or original if no mapping found
        """
        if not sector_field or not sector_field.value:
            return sector_field
        
        normalized = SECTOR_NORMALIZATION_MAP.get(sector_field.value, sector_field.value)
        if normalized != sector_field.value:
            logger.info(f"Normalized sector '{sector_field.value}' -> '{normalized}'")
            return TextFieldWithSource(value=normalized, source=sector_field.source)
        return sector_field
    
    @staticmethod
    def merge_profile(
        yahoo_profile: Optional[CompanyProfile],
        fmp_profile: Optional[CompanyProfile],
        av_profile: Optional[CompanyProfile] = None
    ) -> CompanyProfile:
        """
        Merge company profiles from multiple sources.
        Priority: Yahoo > FMP > Alpha Vantage
        """
        profiles = [p for p in [yahoo_profile, fmp_profile, av_profile] if p is not None]
        
        if not profiles:
            logger.warning("No profile data from any source")
            return CompanyProfile()
        
        if len(profiles) == 1:
            profile = profiles[0]
            profile.std_sector = DataMerger.normalize_sector(profile.std_sector)
            return profile
        
        # Merge fields intelligently - use first available (priority order)
        def get_first_valid(*fields):
            for f in fields:
                if f and hasattr(f, 'value') and f.value is not None:
                    return f
            return None
        
        merged_sector = get_first_valid(
            yahoo_profile.std_sector if yahoo_profile else None,
            fmp_profile.std_sector if fmp_profile else None,
            av_profile.std_sector if av_profile else None
        )
        merged_sector = DataMerger.normalize_sector(merged_sector)
        
        merged = CompanyProfile(
            std_symbol=(yahoo_profile or fmp_profile or av_profile).std_symbol,
            std_company_name=get_first_valid(
                yahoo_profile.std_company_name if yahoo_profile else None,
                fmp_profile.std_company_name if fmp_profile else None,
                av_profile.std_company_name if av_profile else None
            ),
            std_industry=get_first_valid(
                yahoo_profile.std_industry if yahoo_profile else None,
                fmp_profile.std_industry if fmp_profile else None,
                av_profile.std_industry if av_profile else None
            ),
            std_sector=merged_sector,
            std_market_cap=get_first_valid(
                yahoo_profile.std_market_cap if yahoo_profile else None,
                fmp_profile.std_market_cap if fmp_profile else None,
                av_profile.std_market_cap if av_profile else None
            ),
            std_description=get_first_valid(
                yahoo_profile.std_description if yahoo_profile else None,
                fmp_profile.std_description if fmp_profile else None,
                av_profile.std_description if av_profile else None
            ),
            std_website=get_first_valid(
                yahoo_profile.std_website if yahoo_profile else None,
                fmp_profile.std_website if fmp_profile else None,
            ),
            std_ceo=get_first_valid(
                yahoo_profile.std_ceo if yahoo_profile else None,
                fmp_profile.std_ceo if fmp_profile else None,
            ),
            std_beta=get_first_valid(
                yahoo_profile.std_beta if yahoo_profile else None,
                fmp_profile.std_beta if fmp_profile else None,
                av_profile.std_beta if av_profile else None
            ),
        )
        
        return merged
