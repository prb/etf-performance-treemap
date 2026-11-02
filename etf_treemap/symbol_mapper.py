"""Symbol normalization for converting issuer ticker formats to Yahoo Finance format."""

import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)


# Mapping of issuer country/exchange codes to Yahoo Finance suffixes
SYMBOL_SUFFIX_MAP: Dict[str, str] = {
    # North America
    'CN': '.TO',      # Canada → Toronto Stock Exchange
    
    # Europe
    'FP': '.PA',      # France → Paris (Euronext)
    'IM': '.MI',      # Italy → Milan (Borsa Italiana)
    'IT': '.MI',      # Italy alternate code
    'NA': '.AS',      # Netherlands → Amsterdam (Euronext)
    'SS': '.ST',      # Sweden → Stockholm
    'GR': '.DE',      # Germany → Deutsche Börse (XETRA)
    'LN': '.L',       # UK → London Stock Exchange
    'SW': '.SW',      # Switzerland → SIX Swiss Exchange
    'NO': '.OL',      # Norway → Oslo Børs
    'DC': '.CO',      # Denmark → Copenhagen
    'FH': '.HE',      # Finland → Helsinki
    'BB': '.BR',      # Belgium → Brussels (Euronext)
    'SM': '.MA',      # Spain → Madrid
    'PL': '.LS',      # Portugal → Lisbon
    
    # Asia-Pacific
    'JP': '.T',       # Japan → Tokyo Stock Exchange
    'KS': '.KS',      # South Korea → Korea Stock Exchange
    'HK': '.HK',      # Hong Kong → Hong Kong Stock Exchange
    'AU': '.AX',      # Australia → Australian Securities Exchange
    'SP': '.SI',      # Singapore → Singapore Exchange
    'TB': '.BK',      # Thailand → Bangkok
    'TT': '.TW',      # Taiwan → Taiwan Stock Exchange
    'IN': '.NS',      # India → National Stock Exchange (or .BO for Bombay)
    
    # Other
    'BZ': '.SA',      # Brazil → B3 (São Paulo)
}


# Manual override map for symbols that need specific exchange suffixes
# Used when the CSV doesn't include country codes but we know the correct exchange
SYMBOL_OVERRIDE_MAP: Dict[str, str] = {
    # Canadian stocks
    'MDA': 'MDA.TO',        # MDA Space Ltd
    
    # Swedish stocks
    'GOMX': 'GOMX.ST',      # GomSpace Group AB
    'OVZON': 'OVZON.ST',    # Ovzon AB
    
    # Dutch stocks
    'TOM2': 'TOM2.AS',      # TomTom NV
    
    # Italian stocks
    'LDO': 'LDO.MI',        # Leonardo SpA
    
    # French stocks
    'HO': 'HO.PA',          # Thales SA
    'ETL': 'ETL.PA',        # Eutelsat Communications SA
    
    # Luxembourg stocks
    'SESG': 'SESG.PA',      # SES SA (trades on Euronext Paris)
    
    # Israeli stocks
    'SCC': 'SCC.TA',        # Space-Communication Limited
    
    # Japanese stocks
    '9412': '9412.T',       # SKY Perfect JSAT Holdings Inc.
    '186A': '186A.T',       # Astroscale Holdings Inc.
    '464A': '464A.T',       # QPS Holdings, Inc.
    '9348': '9348.T',       # ispace, inc.
    '4825': '4825.T',       # Weathernews Inc.
    '290A': '290A.T',       # Synspective Inc. (Tokyo; example-holdings lists it as Synspective Inc.)
    
    # Korean stocks
    '189300': '189300.KS',  # Intellian Technologies, Inc.
    '474170': '474170.KQ',  # Lumir Inc. (KOSDAQ)
}


# Company name suffix to exchange mapping (for heuristic detection)
COMPANY_SUFFIX_TO_EXCHANGE: Dict[str, str] = {
    'AB': '.ST',        # Swedish: Aktiebolag
    'NV': '.AS',        # Dutch: Naamloze Vennootschap
    'SpA': '.MI',       # Italian: Società per Azioni
    'SA': '.PA',        # French: Société Anonyme (default to Paris, could also be other countries)
}


# Legal-form suffixes are matched as whole trailing words, case-sensitively
# (legal forms are written in capitals, e.g. "AB", "N.V.", "S.A.", "SpA"), so
# names that merely end in the same letters ("NASA", "Kebab", "Nova") do not match.
_COMPANY_SUFFIX_PATTERNS: Dict[str, re.Pattern[str]] = {
    'AB': re.compile(r'(?<![\w.])AB\.?\s*$'),
    'NV': re.compile(r'(?<![\w.])N\.?V\.?\s*$'),
    'SpA': re.compile(r'(?<![\w.])S\.?p\.?A\.?\s*$'),
    'SA': re.compile(r'(?<![\w.])S\.?A\.?\s*$'),
}
def _exchange_from_company_name(company_name: str) -> str | None:
    """Return the exchange suffix implied by a trailing legal-form word, if any."""
    name = company_name.strip()
    for suffix, pattern in _COMPANY_SUFFIX_PATTERNS.items():
        if pattern.search(name):
            return COMPANY_SUFFIX_TO_EXCHANGE[suffix]
    return None
def normalize_symbol(symbol: str, company_name: str = "") -> str:
    """Convert issuer symbol format to Yahoo Finance format.
    
    Many ETF issuers use country codes (e.g., "MDA CN" for Canadian stocks),
    while Yahoo Finance uses exchange suffixes (e.g., "MDA.TO" for Toronto).
    This function normalizes symbols to Yahoo Finance format.
    
    Also handles:
    - Share class symbols where periods should be hyphens (e.g., "BRK.B" → "BRK-B")
    - Manual overrides for known symbols (e.g., "GOMX" → "GOMX.ST")
    - Company name heuristics (e.g., "AB" suffix → Swedish stock)
    
    Args:
        symbol (str): Symbol in issuer format (e.g., "MDA CN", "AIR FP", "AAPL", "BRK.B", "GOMX")
        company_name (str): Optional company name for heuristic detection (e.g., "GomSpace Group AB")
        
    Returns:
        str: Symbol in Yahoo Finance format (e.g., "MDA.TO", "AIR.PA", "AAPL", "BRK-B", "GOMX.ST")
        
    Examples:
        >>> normalize_symbol("MDA CN")
        'MDA.TO'
        >>> normalize_symbol("AIR FP")
        'AIR.PA'
        >>> normalize_symbol("AAPL")
        'AAPL'
        >>> normalize_symbol("9412 JP")
        '9412.T'
        >>> normalize_symbol("BRK.B")
        'BRK-B'
        >>> normalize_symbol("GOMX", "GomSpace Group AB")
        'GOMX.ST'
    """
    # Step 1: Check manual override map first
    if symbol in SYMBOL_OVERRIDE_MAP:
        normalized = SYMBOL_OVERRIDE_MAP[symbol]
        logger.debug(f"Normalized symbol (override): {symbol} → {normalized}")
        return normalized
    
    # Step 2: Handle symbols with spaces (e.g., "MDA CN")
    parts = symbol.strip().split()
    
    if len(parts) == 2:
        ticker, country_code = parts
        
        # Check if we have a mapping for this country code
        if country_code in SYMBOL_SUFFIX_MAP:
            normalized = f"{ticker}{SYMBOL_SUFFIX_MAP[country_code]}"
            logger.debug(f"Normalized symbol: {symbol} → {normalized}")
            return normalized
        else:
            # Unknown country code - log warning and return original
            logger.warning(
                f"Unknown country/exchange code '{country_code}' for symbol '{symbol}'. "
                f"Add mapping to SYMBOL_SUFFIX_MAP in symbol_mapper.py"
            )
            return symbol
    
    # Step 3: Handle share class symbols (e.g., BRK.B → BRK-B)
    # Yahoo Finance uses hyphens for share classes, not periods
    if '.' in symbol and len(symbol.split('.')) == 2:
        base, share_class = symbol.split('.')
        # Check if share class is a single letter (A, B, C, etc.)
        if len(share_class) == 1 and share_class.isalpha():
            normalized = f"{base}-{share_class}"
            logger.debug(f"Normalized share class symbol: {symbol} → {normalized}")
            return normalized
    
    # Step 4: Try company name heuristics if provided
    if company_name:
        exchange = _exchange_from_company_name(company_name)
        if exchange is not None:
            normalized = f"{symbol}{exchange}"
            logger.debug(f"Normalized symbol (name heuristic): {symbol} → {normalized}")
            return normalized
    
    # No normalization needed - return as-is
    return symbol


def get_display_symbol(symbol: str) -> str:
    """Get the display version of a symbol (original format).
    
    This is useful for showing the original symbol in logs/UI while using
    the normalized version for API calls.
    
    Args:
        symbol (str): Symbol in any format
        
    Returns:
        str: Symbol suitable for display (removes Yahoo Finance suffixes)
        
    Examples:
        >>> get_display_symbol("MDA.TO")
        'MDA'
        >>> get_display_symbol("AAPL")
        'AAPL'
        >>> get_display_symbol("9412.T")
        '9412'
    """
    # Remove Yahoo Finance suffixes for cleaner display
    if '.' in symbol:
        return symbol.split('.')[0]
    return symbol
