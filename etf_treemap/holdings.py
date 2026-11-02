"""Holdings file loading and parsing module.

The tool does not download holdings. The user obtains a holdings file from
the ETF issuer (or a data provider) and passes its path to the tool. This
module detects which of the supported CSV layouts the file uses and parses it.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import csv
import logging

logger = logging.getLogger(__name__)

# Column header aliases (lower-case) for each logical field, in priority order.
_SYMBOL_COLUMNS = ("stockticker", "ticker", "symbol")
_NAME_COLUMNS = ("securityname", "name", "holding", "company", "description")
_WEIGHT_COLUMNS = (
    "weightings",
    "weighting",
    "weight",
    "% of net assets",
    "% tna",
    "% of fund",
    "% net assets",
)

SUPPORTED_FORMATS_HELP = (
    "Supported holdings file formats (CSV):\n"
    "  - ETF Database export: optional metadata lines, then a header row "
    "'Holding,Symbol,Weighting' with percentages such as 8.72%\n"
    "  - Invesco monthly holdings: header row with 'Ticker', 'Company' and "
    "'% TNA'\n"
    "  - Fund-administrator export (e.g. Spear Advisors): header row with "
    "'StockTicker', 'SecurityName' and 'Weightings'\n"
    "  - Any CSV whose header row has a symbol column (Symbol, Ticker or "
    "StockTicker) and a weight column (Weighting, Weightings, Weight, "
    "% of Net Assets or % TNA)"
)


@dataclass
class Holding:
    """Represents a single holding in an ETF portfolio.

    Attributes:
        symbol (str): Ticker symbol of the holding (e.g., "AAPL", "MSFT").
        name (str): Full company or security name (e.g., "Apple Inc.").
        weight (float): Portfolio weight as a decimal (e.g., 0.059589 for 5.9589%).

    Examples:
        >>> holding = Holding(symbol="AAPL", name="Apple Inc.", weight=0.05)
        >>> print(f"{holding.symbol}: {holding.weight * 100:.2f}%")
        AAPL: 5.00%
    """
    symbol: str          # Ticker symbol (e.g., "PL")
    name: str           # Full name (e.g., "Planet Labs")
    weight: float       # Portfolio weight as decimal (e.g., 0.059589 for 5.9589%)


class HoldingsFormatError(ValueError):
    """Raised when a holdings file is empty or not in a supported format."""


def _normalize(cell: str) -> str:
    """Normalize a header cell for alias matching."""
    return cell.strip().lower()


def _find_column(header: List[str], aliases: tuple[str, ...]) -> Optional[int]:
    """Return the index of the first header cell matching an alias (by priority)."""
    normalized = [_normalize(cell) for cell in header]
    for alias in aliases:
        if alias in normalized:
            return normalized.index(alias)
    return None


class HoldingsFetcher:
    """Loads ETF holdings from a user-supplied CSV file.

    Examples:
        >>> fetcher = HoldingsFetcher()
        >>> holdings = fetcher.get_holdings("QQQM", "example-holdings/QQQM-holdings.csv")
        >>> holdings[0].symbol
        'NVDA'
    """

    def __init__(self) -> None:
        """Initialize holdings fetcher."""
        pass

    def get_holdings(self, etf_symbol: str, csv_file: str) -> List[Holding]:
        """Load and parse holdings from a local CSV file.

        Args:
            etf_symbol (str): ETF ticker symbol (used for logging).
            csv_file (str): Path to the holdings CSV file.

        Returns:
            List[Holding]: Parsed holdings.

        Raises:
            FileNotFoundError: If the file does not exist (or is not a file).
            PermissionError / OSError: If the file cannot be read.
            HoldingsFormatError: If the file is not text, is in an unsupported
                format or contains no holdings rows. The message lists the
                supported formats. (Subclass of ValueError.)
        """
        path = Path(csv_file)
        logger.info(f"Loading holdings for {etf_symbol} from {path}")
        if not path.is_file():
            raise FileNotFoundError(f"Holdings file not found: '{csv_file}'")

        try:
            csv_content = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as e:
            raise HoldingsFormatError(
                f"Holdings file '{csv_file}' is not a UTF-8 text file ({e.reason}).\n"
                f"{SUPPORTED_FORMATS_HELP}"
            ) from e

        holdings = self._parse_csv(csv_content, etf_symbol, source=csv_file)
        logger.info(f"Loaded {len(holdings)} holdings from {csv_file}")
        return holdings

    def _parse_csv(self, csv_content: str, etf_symbol: str, source: str = "<string>") -> List[Holding]:
        """Parse CSV content into Holding objects.

        Detects the header row (skipping any metadata lines before it) by
        looking for a row with a recognised symbol column and weight column.

        Args:
            csv_content: CSV content as string.
            etf_symbol: ETF ticker symbol (for logging).
            source: Description of where the content came from (for errors).

        Returns:
            List[Holding]: Parsed holdings.

        Raises:
            HoldingsFormatError: If no header row is recognised or no rows
                yield a holding.
        """
        rows = list(csv.reader(csv_content.splitlines()))

        header_idx: Optional[int] = None
        columns: Dict[str, Optional[int]] = {}
        for i, row in enumerate(rows):
            symbol_col = _find_column(row, _SYMBOL_COLUMNS)
            weight_col = _find_column(row, _WEIGHT_COLUMNS)
            if symbol_col is not None and weight_col is not None:
                header_idx = i
                columns = {
                    "symbol": symbol_col,
                    "weight": weight_col,
                    "name": _find_column(row, _NAME_COLUMNS),
                }
                break

        if header_idx is None:
            raise HoldingsFormatError(
                f"Unrecognised holdings format in '{source}': could not find a header row "
                f"with a symbol column and a weight column.\n{SUPPORTED_FORMATS_HELP}"
            )

        holdings: List[Holding] = []
        symbol_col = columns["symbol"]
        weight_col = columns["weight"]
        name_col = columns["name"]
        assert symbol_col is not None and weight_col is not None

        for row in rows[header_idx + 1:]:
            if not row or all(not cell.strip() for cell in row):
                continue
            try:
                symbol = row[symbol_col].strip()
                weight_str = row[weight_col].strip()
                name = row[name_col].strip() if name_col is not None and name_col < len(row) else ""

                # Skip if essential fields are missing
                if not symbol or not weight_str:
                    continue

                # "6.15%" -> 0.0615; a bare number is used as given
                has_percent = weight_str.endswith('%')
                weight = float(weight_str.rstrip('%').replace(',', ''))
                if has_percent:
                    weight = weight / 100.0

                holdings.append(Holding(symbol=symbol, name=name or symbol, weight=weight))
            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping malformed CSV row: {row}. Error: {e}")
                continue

        if not holdings:
            raise HoldingsFormatError(
                f"No holdings rows found in '{source}' for {etf_symbol}: the file has a "
                f"recognised header but no usable data rows.\n{SUPPORTED_FORMATS_HELP}"
            )

        return holdings
