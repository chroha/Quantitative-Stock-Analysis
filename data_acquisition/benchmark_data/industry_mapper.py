"""
Industry mapping from Damodaran's granular industries to GICS sectors.
Maps 100+ Damodaran industries to Yahoo Finance's 11 GICS sectors.
"""

# Mapping from GICS Sector to list of Damodaran industry names
SECTOR_MAPPING = {
    'Technology': [
        'Software (System & Application)',
        'Software (Entertainment)',
        'Software (Internet)',
        'Semiconductor',
        'Semiconductor Equip',
        'Computer Services',
        'Computers/Peripherals',
        'Telecom. Equipment',
        'Electronics (Consumer & Office)',
        'Electronics (General)',
        'Information Services',
    ],
    
    'Healthcare': [
        'Drugs (Pharmaceutical)',
        'Drugs (Biotechnology)',
        'Healthcare Products',
        'Healthcare Support Services',
        'Healthcare Information and Technology',
        'Hospitals/Healthcare Facilities',
        'Medical Services',
    ],
    
    'Financials': [
        'Banks (Regional)',
        'Bank (Money Center)',
        'Brokerage & Investment Banking',
        'Financial Svcs. (Non-bank & Insurance)',
        'Insurance (General)',
        'Insurance (Life)',
        'Insurance (Prop/Cas.)',
        'Investments & Asset Management',
        'Real Estate (General/Diversified)',
        'Real Estate (Operations & Services)',
        'REIT',
    ],
    
    'Consumer Discretionary': [
        'Retail (Automotive)',
        'Retail (Building Supply)',
        'Retail (Distributors)',
        'Retail (General)',
        'Retail (Grocery and Food)',
        'Retail (Online)',
        'Retail (Special Lines)',
        'Auto & Truck',
        'Auto Parts',
        'Entertainment',
        'Entertainment Tech',
        'Hotel/Gaming',
        'Homebuilding',
        'Household Products',
        'Recreation',
        'Restaurant/Dining',
        'Shoes',
        'Apparel',
        'Furn/Home Furnishings',
    ],
    
    'Consumer Staples': [
        'Beverage (Alcoholic)',
        'Beverage (Soft)',
        'Food Processing',
        'Food Wholesalers',
        'Farming/Agriculture',
        'Tobacco',
    ],
    
    'Energy': [
        'Oil/Gas (Integrated)',
        'Oil/Gas (Production and Exploration)',
        'Oil/Gas Distribution',
        'Oilfield Svcs/Equip.',
        'Coal & Related Energy',
    ],
    
    'Industrials': [
        'Aerospace/Defense',
        'Air Transport',
        'Transportation',
        'Trucking',
        'Railroad',
        'Shipbuilding & Marine',
        'Machinery',
        'Electrical Equipment',
        'Engineering/Construction',
        'Environmental & Waste Services',
        'Packaging & Container',
    ],
    
    'Materials': [
        'Metals & Mining',
        'Steel',
        'Chemical (Basic)',
        'Chemical (Diversified)',
        'Chemical (Specialty)',
        'Paper/Forest Products',
    ],
    
    'Real Estate': [
        'Real  Estate (Development)',           # Note: two spaces between Real and Estate
        'Real Estate  (General/Diversified)',   # Note: two spaces before parenthesis
        'Real  Estate (Operations & Services)', # Note: two spaces between Real and Estate
        'Retail (REITs)',                       # REITs are under Retail in Damodaran data
    ],
    
    'Utilities': [
        'Utility (General)',
        'Utility (Water)',
        'Power',
    ],
    
    'Communication Services': [
        'Telecom. Services',
        'Cable TV',
        'Broadcasting',
        'Publishing & Newspapers',
        'Advertising',
    ],
}


def get_all_mapped_industries():
    """
    Get a flat list of all Damodaran industries that are mapped.
    
    Returns:
        Set of industry names
    """
    all_industries = set()
    for industries in SECTOR_MAPPING.values():
        all_industries.update(industries)
    return all_industries


def get_sector_for_industry(industry_name: str):
    """
    Find which GICS sector a Damodaran industry belongs to.
    
    Args:
        industry_name: Damodaran industry name
        
    Returns:
        GICS sector name or None if not mapped
    """
    for sector, industries in SECTOR_MAPPING.items():
        if industry_name in industries:
            return sector
    return None


def get_unmapped_industries(available_industries):
    """
    Find industries in the data that are not mapped to any sector.
    
    Args:
        available_industries: List or set of industry names from data
        
    Returns:
        Set of unmapped industry names
    """
    mapped = get_all_mapped_industries()
    available = set(available_industries)
    return available - mapped
