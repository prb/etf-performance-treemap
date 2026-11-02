"""Price data fetching module using yfinance."""

import logging
import math
import time
from typing import Optional, Tuple
from datetime import date, datetime, time as dt_time, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf

from etf_treemap.cli import parse_lookback_period
from etf_treemap.symbol_mapper import normalize_symbol

logger = logging.getLogger(__name__)

# US equity market clock. All market-hours and "today" logic uses this zone,
# regardless of the machine's local time zone.
# Note: market holidays are not hard-coded; they are derived from yfinance data
# (no bars dated today during market hours means a holiday). See _one_day_prices.
MARKET_TZ = ZoneInfo("America/New_York")
MARKET_OPEN = dt_time(9, 30)
MARKET_CLOSE = dt_time(16, 0)


def compute_date_range(lookback_period: str, end: datetime) -> Tuple[datetime, datetime]:
    """Compute the (start, end) window for a lookback period ending at ``end``.

    Months are approximated as 30 days and years as 365 days.

    Args:
        lookback_period (str): Period such as "1d", "2w", "3m" or "1y".
        end (datetime): End of the window.

    Returns:
        Tuple[datetime, datetime]: ``(end - period, end)``.
    """
    value, unit = parse_lookback_period(lookback_period)
    if unit == 'd':
        delta = timedelta(days=value)
    elif unit == 'w':
        delta = timedelta(weeks=value)
    elif unit == 'm':
        delta = timedelta(days=value * 30)
    elif unit == 'y':
        delta = timedelta(days=value * 365)
    else:
        raise ValueError(f"Invalid time unit: {unit}")
    return (end - delta, end)


class PriceFetcher:
    """Fetches price data and calculates price changes using yfinance.
    
    This class handles retrieving historical and intraday price data for
    securities, calculating percentage changes over specified lookback periods.
    
    Attributes:
        lookback_period (str): Time period string (e.g., "1d", "3m", "1y").
    
    Examples:
        >>> fetcher = PriceFetcher("1d")
        >>> price_change = fetcher.get_price_change("AAPL")
        >>> if price_change is not None:
        ...     print(f"AAPL changed {price_change:.2f}% today")
        AAPL changed 2.35% today
        
        >>> fetcher = PriceFetcher("3m")
        >>> change = fetcher.get_price_change("SPY")
        >>> print(f"SPY 3-month change: {change:.2f}%")
        SPY 3-month change: 8.45%
    """
    
    def __init__(self, lookback_period: str, now: Optional[datetime] = None) -> None:
        """Initialize price fetcher with a lookback period.
        
        Args:
            lookback_period (str): Time period string in format: positive integer
                followed by 'd' (days), 'w' (weeks), 'm' (months), or 'y' (years).
                Examples: "1d", "3m", "1y".
            now (Optional[datetime]): Reference end time, mainly for tests.
                Defaults to the current US/Eastern time.

        The date range is computed once here and reused for every price fetch
        and for the chart title (see :attr:`date_range`).

        Examples:
            >>> fetcher = PriceFetcher("1d")
            >>> print(fetcher.lookback_period)
            1d
            >>> fetcher = PriceFetcher("6m")
            >>> print(fetcher.lookback_period)
            6m
        """
        self.lookback_period = lookback_period
        self._date_range = compute_date_range(
            lookback_period, now if now is not None else datetime.now(MARKET_TZ)
        )

    @property
    def date_range(self) -> Tuple[datetime, datetime]:
        """The (start, end) window, fixed when the fetcher was created.

        Used for both the price fetch and the chart title so they always agree.
        Datetimes are US/Eastern aware unless ``now`` was passed to the constructor.
        """
        return self._date_range
    
    def get_price_change(self, symbol: str, max_retries: int = 3, company_name: str = "") -> Optional[float]:
        """Fetch price data and calculate percentage change for a symbol.
        
        Retrieves historical or intraday price data using yfinance and calculates
        the percentage change over the lookback period. For "1d" periods during
        market hours, uses intraday data; otherwise uses daily closing prices.
        
        Automatically normalizes symbols from issuer format (e.g., "MDA CN") to
        Yahoo Finance format (e.g., "MDA.TO") before fetching data.
        
        Includes retry logic with exponential backoff to handle Yahoo Finance API flakiness.
        
        Args:
            symbol (str): Stock ticker symbol (e.g., "AAPL", "MDA CN", "AIR FP").
            max_retries (int): Maximum number of retry attempts (default: 3).
            company_name (str): Optional company name for heuristic symbol normalization.
            
        Returns:
            Optional[float]: Percentage price change, or None if data is unavailable
                or an error occurs. Positive values indicate price increases,
                negative values indicate decreases.
        
        Examples:
            >>> fetcher = PriceFetcher("1d")
            >>> change = fetcher.get_price_change("AAPL")
            >>> if change is not None:
            ...     print(f"Price changed {change:.2f}%")
            Price changed 2.35%
            
            >>> # International symbol with country code
            >>> change = fetcher.get_price_change("MDA CN")
            >>> if change:
            ...     print(f"MDA changed {change:.2f}%")
            MDA changed 1.23%
            
            >>> # Symbol with company name for heuristic detection
            >>> change = fetcher.get_price_change("GOMX", company_name="GomSpace Group AB")
            >>> if change:
            ...     print(f"GOMX changed {change:.2f}%")
            GOMX changed 3.45%
        """
        # Normalize symbol to Yahoo Finance format
        normalized_symbol = normalize_symbol(symbol, company_name)
        if normalized_symbol != symbol:
            logger.info(f"Normalized symbol: {symbol} → {normalized_symbol}")
        
        # Try fetching with retries
        for attempt in range(max_retries):
            try:
                # Date range was fixed at construction (shared with the title)
                start_date, end_date = self._date_range
                
                # Create ticker object with normalized symbol
                ticker = yf.Ticker(normalized_symbol)
                
                prices = self._select_prices(ticker, start_date, end_date)
                
                # Check if we have data
                if prices is None:
                    if attempt < max_retries - 1:
                        # Retry with exponential backoff
                        wait_time = 2 ** attempt  # 1s, 2s, 4s
                        logger.debug(f"Empty data for {symbol}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"Insufficient price data for symbol: {symbol} (normalized: {normalized_symbol})")
                        return None
                
                # Get start and end prices
                start_price, end_price = prices

                # Reject missing (NaN/inf) prices so they never reach the calculator
                if not (math.isfinite(start_price) and math.isfinite(end_price)):
                    logger.warning(f"Non-finite price data for symbol: {symbol}")
                    return None
                
                # Calculate percentage change: ((P2 - P1) / P1) * 100
                if start_price == 0:
                    logger.warning(f"Start price is zero for symbol: {symbol}")
                    return None
                
                price_change = ((end_price - start_price) / start_price) * 100
                
                # Success - return the result
                return price_change
                
            except Exception as e:
                if attempt < max_retries - 1:
                    # Retry with exponential backoff
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.debug(f"Error fetching {symbol}: {e}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"Failed to fetch price data for {symbol} after {max_retries} attempts: {e}")
                    return None
        
        return None

    def _select_prices(self, ticker: yf.Ticker, start_date: datetime,
                       end_date: datetime) -> Optional[Tuple[float, float]]:
        """Pick the (start, end) prices to compare, or None if data is insufficient."""
        if self.lookback_period == "1d":
            return self._one_day_prices(ticker)
        hist = ticker.history(start=start_date, end=end_date)
        if hist.empty or len(hist) < 2:
            return None
        return float(hist['Close'].iloc[0]), float(hist['Close'].iloc[-1])

    def _one_day_prices(self, ticker: yf.Ticker) -> Optional[Tuple[float, float]]:
        """Return (previous close, latest price) for the "1d" lookback.

        During US market hours the latest price is the last 1-minute bar and the
        reference is the previous session's daily close. Holidays are detected
        from the data: if the last intraday bar is not from today (US/Eastern),
        the market is treated as closed. When closed, the last two daily closes
        are compared. If the previous close is unavailable while the market is
        open, falls back to the first bar of the day.
        """
        today = datetime.now(MARKET_TZ).date()
        if self._is_market_open():
            intraday = ticker.history(period="1d", interval="1m")
            if not intraday.empty and _last_bar_date(intraday) in (None, today):
                latest = float(intraday['Close'].iloc[-1])
                daily = ticker.history(period="5d", interval="1d")
                previous = _previous_close(daily, today)
                if previous is None:
                    if len(intraday) < 2:
                        return None
                    logger.debug("No previous close available; using first intraday bar")
                    previous = float(intraday['Close'].iloc[0])
                return previous, latest
            logger.debug("No bars for today despite market hours (holiday?); using daily data")
        daily = ticker.history(period="5d", interval="1d")
        if daily.empty:
            return None
        closes = daily['Close'].dropna()
        if len(closes) < 2:
            return None
        return float(closes.iloc[-2]), float(closes.iloc[-1])

    def _is_market_open(self, now: Optional[datetime] = None) -> bool:
        """Check whether the regular US equity session is in progress.

        Uses US/Eastern time (09:30 inclusive to 16:00 exclusive, Monday to
        Friday). Market holidays are not hard-coded: on a holiday this returns
        True during the usual hours, and :meth:`_one_day_prices` detects that
        from the absence of bars dated today and falls back to daily data.

        Args:
            now (Optional[datetime]): Time to test (naive values are taken as
                US/Eastern). Defaults to the current time.

        Returns:
            bool: True if inside regular trading hours on a weekday.
        """
        if now is None:
            now = datetime.now(MARKET_TZ)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=MARKET_TZ)
        else:
            now = now.astimezone(MARKET_TZ)

        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        return MARKET_OPEN <= now.time() < MARKET_CLOSE


def _last_bar_date(hist: pd.DataFrame) -> Optional[date]:
    """Date of the last bar in the index's own time zone, or None if unknown."""
    if not isinstance(hist.index, pd.DatetimeIndex) or len(hist.index) == 0:
        return None
    return hist.index[-1].date()


def _previous_close(daily: pd.DataFrame, today: date) -> Optional[float]:
    """Last finite daily close from a session before ``today``, if any."""
    if daily.empty or not isinstance(daily.index, pd.DatetimeIndex):
        return None
    closes = daily['Close'][daily.index.date < today].dropna()
    if closes.empty:
        return None
    return float(closes.iloc[-1])
