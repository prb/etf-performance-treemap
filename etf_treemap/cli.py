"""Command-line interface and argument parsing for ETF Treemap tool."""

import argparse
import os
import re
from typing import Tuple

from etf_treemap.holdings import SUPPORTED_FORMATS_HELP


SUPPORTED_FORMATS_HELP_ESCAPED = SUPPORTED_FORMATS_HELP.replace('%', '%%')
_SYMBOL_PATTERN = re.compile(r'[A-Za-z0-9][A-Za-z0-9.\-]{0,14}')


def validate_etf_symbol(symbol: str) -> bool:
    """Check that an ETF symbol is safe to use in file names and lookups.

    Allows 1-15 letters, digits, dots and hyphens, starting with a letter or
    digit. Path separators and other special characters are rejected because
    the symbol is used in the output file name.

    Examples:
        >>> validate_etf_symbol("QQQM")
        True
        >>> validate_etf_symbol("BRK.B")
        True
        >>> validate_etf_symbol("../etc")
        False
    """
    return isinstance(symbol, str) and bool(_SYMBOL_PATTERN.fullmatch(symbol))


def parse_arguments() -> Tuple[str, str, str]:
    """Parse command-line arguments and return ETF configuration.

    The user must supply a holdings file (downloaded from the ETF issuer) with
    ``--csv`` (alias ``--holdings``). The tool never downloads holdings itself.

    Returns:
        Tuple[str, str, str]: A tuple containing:
            - etf_symbol (str): ETF ticker symbol (e.g., "UFO", "SPY")
            - lookback_period (str): Time period (e.g., "1d", "3m", "1y")
            - csv_file (str): Path to the holdings CSV file

    Raises:
        SystemExit: If arguments are missing or invalid, or the holdings file
            does not exist or cannot be read.
    """
    parser = argparse.ArgumentParser(
        description=(
            'Generate a treemap of ETF holdings performance. You provide the '
            'ETF holdings file (downloaded from the issuer); prices come from yfinance.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s QQQM 1w --csv example-holdings/QQQM-holdings.csv
  %(prog)s UFO 1d --csv ~/Downloads/UFO-holdings.csv

{SUPPORTED_FORMATS_HELP_ESCAPED}
        """
    )

    parser.add_argument(
        'etf_symbol',
        type=str,
        help='ETF ticker symbol (e.g., UFO, SPY, QQQ)'
    )

    parser.add_argument(
        'lookback_period',
        type=str,
        help='Lookback period: positive integer followed by d/w/m/y (e.g., 1d, 3m, 1y)'
    )

    parser.add_argument(
        '--csv', '--holdings',
        type=str,
        dest='csv_file',
        required=True,
        metavar='HOLDINGS_FILE',
        help='Path to the ETF holdings CSV file you downloaded (required)'
    )

    args = parser.parse_args()

    if not validate_etf_symbol(args.etf_symbol):
        parser.error(
            f"Invalid ETF symbol: '{args.etf_symbol}'. Use 1-15 letters, digits, "
            "'.' or '-' (e.g., 'QQQM', 'BRK.B')"
        )

    if not validate_lookback_period(args.lookback_period):
        parser.error(
            f"Invalid lookback period format: '{args.lookback_period}'. "
            "Expected format: positive integer followed by d/w/m/y (e.g., '1d', '3m', '1y')"
        )

    if not os.path.isfile(args.csv_file):
        parser.error(
            f"Holdings file not found: '{args.csv_file}'. Download the holdings "
            "file from the ETF issuer and pass its path with --csv."
        )
    if not os.access(args.csv_file, os.R_OK):
        parser.error(f"Holdings file is not readable: '{args.csv_file}'")

    return (args.etf_symbol, args.lookback_period, args.csv_file)


def validate_lookback_period(period: str) -> bool:
    """Validate lookback period format against expected pattern.
    
    Checks if the period string matches the pattern of a positive integer
    followed by exactly one time unit character (d/w/m/y).
    
    Args:
        period (str): Lookback period string to validate.
        
    Returns:
        bool: True if the period matches the valid format, False otherwise.
    
    Examples:
        >>> validate_lookback_period("1d")
        True
        >>> validate_lookback_period("3m")
        True
        >>> validate_lookback_period("52w")
        True
        >>> validate_lookback_period("0d")  # Zero not allowed
        False
        >>> validate_lookback_period("1x")  # Invalid unit
        False
        >>> validate_lookback_period("d1")  # Wrong order
        False
    """
    if not period or not isinstance(period, str):
        return False
    
    # Pattern: positive integer followed by exactly one of d/w/m/y
    pattern = r'^[1-9]\d*[dwmy]$'
    return bool(re.match(pattern, period))


def parse_lookback_period(period: str) -> Tuple[int, str]:
    """Extract numeric value and time unit from a lookback period string.
    
    Parses a validated lookback period string into its numeric component
    and time unit character.
    
    Args:
        period (str): Lookback period string (e.g., "1d", "3m", "1y").
        
    Returns:
        Tuple[int, str]: A tuple containing:
            - value (int): The numeric portion of the period
            - unit (str): The time unit character ('d', 'w', 'm', or 'y')
        
    Raises:
        ValueError: If the period format is invalid.
    
    Examples:
        >>> parse_lookback_period("1d")
        (1, 'd')
        >>> parse_lookback_period("3m")
        (3, 'm')
        >>> parse_lookback_period("52w")
        (52, 'w')
        >>> parse_lookback_period("2y")
        (2, 'y')
        >>> parse_lookback_period("invalid")
        Traceback (most recent call last):
            ...
        ValueError: Invalid lookback period format: 'invalid'...
    """
    if not validate_lookback_period(period):
        raise ValueError(
            f"Invalid lookback period format: '{period}'. "
            "Expected format: positive integer followed by d/w/m/y (e.g., '1d', '3m', '1y')"
        )
    
    # Extract numeric part and unit
    # The last character is the unit, everything before is the number
    unit = period[-1]
    value = int(period[:-1])
    
    return (value, unit)
