"""Tests for the robustness pass: date range, market clock, 1d change, headless output, error handling."""

import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from hypothesis import given, strategies as st

from etf_treemap.calculator import TreemapBlock
from etf_treemap.holdings import Holding
from etf_treemap.main import main
from etf_treemap.prices import MARKET_TZ, PriceFetcher, compute_date_range
from etf_treemap.visualizer import TreemapVisualizer

ET = MARKET_TZ
PERIODS = st.tuples(
    st.integers(min_value=1, max_value=400), st.sampled_from(["d", "w", "m", "y"])
).map(lambda t: f"{t[0]}{t[1]}")
UNIT_DAYS = {"d": 1, "w": 7, "m": 30, "y": 365}


# --- Finding 5: date range and logging -------------------------------------

@given(
    period=PERIODS,
    end=st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2100, 1, 1)),
)
def test_compute_date_range_property(period: str, end: datetime) -> None:
    """The window ends at ``end`` and spans exactly value * unit-days."""
    start, got_end = compute_date_range(period, end)
    assert got_end == end
    assert end - start == timedelta(days=int(period[:-1]) * UNIT_DAYS[period[-1]])


def test_date_range_is_computed_once() -> None:
    """The public range is fixed at construction, so title and fetch agree."""
    fetcher = PriceFetcher("2w", now=datetime(2024, 1, 15, 12, 0))
    first = fetcher.date_range
    assert first == (datetime(2024, 1, 1, 12, 0), datetime(2024, 1, 15, 12, 0))
    assert fetcher.date_range is first


def test_date_range_default_is_eastern_aware() -> None:
    start, end = PriceFetcher("1w").date_range
    assert end.tzinfo is not None
    assert end.utcoffset() == datetime.now(ET).utcoffset()


@patch("etf_treemap.prices.yf.Ticker")
def test_price_fetch_uses_fetcher_date_range(mock_ticker_class: Mock) -> None:
    mock_ticker = Mock()
    mock_ticker.history.return_value = pd.DataFrame({"Close": [100.0, 110.0]})
    mock_ticker_class.return_value = mock_ticker
    fetcher = PriceFetcher("1w", now=datetime(2024, 1, 15))
    fetcher.get_price_change("AAPL")
    mock_ticker.history.assert_called_once_with(
        start=datetime(2024, 1, 8), end=datetime(2024, 1, 15)
    )


def test_import_does_not_configure_logging() -> None:
    """Importing the entry module must not touch the root logger."""
    code = (
        "import logging, etf_treemap.main;"
        "import sys; sys.exit(1 if logging.getLogger().handlers else 0)"
    )
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


@patch("etf_treemap.main.logging.basicConfig")
@patch("etf_treemap.main.parse_arguments", side_effect=KeyboardInterrupt)
def test_main_configures_logging(_parse: Mock, mock_basic_config: Mock) -> None:
    assert main() == 130
    mock_basic_config.assert_called_once()


@patch("etf_treemap.main.parse_arguments")
@patch("etf_treemap.main.HoldingsFetcher")
@patch("etf_treemap.main.PriceFetcher")
@patch("etf_treemap.main.PerformanceCalculator")
@patch("etf_treemap.main.TreemapVisualizer")
def test_main_passes_fetcher_range_to_title(
    mock_vis_class: Mock, mock_calc_class: Mock, mock_pf_class: Mock,
    mock_hf_class: Mock, mock_parse: Mock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    mock_parse.return_value = ("UFO", "1w", "h.csv")
    mock_hf_class.return_value.get_holdings.return_value = [Holding("AAPL", "Apple", 0.1)]
    sentinel = (datetime(2024, 1, 1), datetime(2024, 1, 8))
    mock_pf_class.return_value.get_price_change.return_value = 1.0
    mock_pf_class.return_value.date_range = sentinel
    mock_calc_class.return_value.prepare_treemap_data.return_value = [
        TreemapBlock("AAPL", 0.1, 1.0, 0.1, "up")
    ]
    assert main() == 0
    mock_vis_class.assert_called_once_with("UFO", sentinel)


# --- Finding 6: market clock and 1d change ---------------------------------

@pytest.mark.parametrize(
    "now, expected",
    [
        (datetime(2024, 1, 9, 9, 29), False),
        (datetime(2024, 1, 9, 9, 30), True),
        (datetime(2024, 1, 9, 15, 59), True),
        (datetime(2024, 1, 9, 16, 0), False),
        (datetime(2024, 1, 13, 12, 0), False),  # Saturday
        (datetime(2024, 1, 14, 12, 0), False),  # Sunday
    ],
)
def test_is_market_open_naive_is_eastern(now: datetime, expected: bool) -> None:
    assert PriceFetcher("1d")._is_market_open(now) is expected


def test_is_market_open_converts_other_zones() -> None:
    """14:30 UTC in January is 09:30 ET (open); 14:29 UTC is not."""
    from datetime import timezone
    fetcher = PriceFetcher("1d")
    assert fetcher._is_market_open(datetime(2024, 1, 9, 14, 30, tzinfo=timezone.utc)) is True
    assert fetcher._is_market_open(datetime(2024, 1, 9, 14, 29, tzinfo=timezone.utc)) is False


@given(
    st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)).map(
        lambda d: d.replace(tzinfo=ET)
    )
)
def test_is_market_open_property(now: datetime) -> None:
    expected = now.weekday() < 5 and (9, 30) <= (now.hour, now.minute) < (16, 0)
    assert PriceFetcher("1d")._is_market_open(now) is expected


def _daily(closes: list[float], end_day: str) -> pd.DataFrame:
    idx = pd.bdate_range(end=end_day, periods=len(closes), tz=ET)
    return pd.DataFrame({"Close": closes}, index=idx)


def _intraday(prices: list[float], day: str) -> pd.DataFrame:
    idx = pd.date_range(f"{day} 09:30", periods=len(prices), freq="1min", tz=ET)
    return pd.DataFrame({"Close": prices}, index=idx)


def _ticker(intraday: pd.DataFrame, daily: pd.DataFrame) -> Mock:
    ticker = Mock()
    ticker.history.side_effect = lambda **kw: intraday if kw["interval"] == "1m" else daily
    return ticker


def _fixed_now(day: str) -> Mock:
    now = Mock()
    now.date.return_value = pd.Timestamp(day).date()
    return now


@patch("etf_treemap.prices.PriceFetcher._is_market_open", return_value=True)
@patch("etf_treemap.prices.datetime")
@patch("etf_treemap.prices.yf.Ticker")
def test_1d_open_is_relative_to_previous_close(mock_cls: Mock, mock_dt: Mock, _open: Mock) -> None:
    mock_dt.now.return_value = _fixed_now("2024-01-10")
    # Gap up at the open: first bar 105, prior close 100, latest 110.
    mock_cls.return_value = _ticker(
        _intraday([105.0, 108.0, 110.0], "2024-01-10"),
        _daily([98.0, 100.0, 109.0], "2024-01-10"),  # today's partial bar is ignored
    )
    change = PriceFetcher("1d", now=datetime(2024, 1, 10)).get_price_change("AAPL")
    assert change == pytest.approx(10.0)  # first-to-last would be ~4.76


@patch("etf_treemap.prices.PriceFetcher._is_market_open", return_value=True)
@patch("etf_treemap.prices.datetime")
@patch("etf_treemap.prices.yf.Ticker")
def test_1d_open_falls_back_to_first_bar(mock_cls: Mock, mock_dt: Mock, _open: Mock) -> None:
    mock_dt.now.return_value = _fixed_now("2024-01-10")
    mock_cls.return_value = _ticker(
        _intraday([100.0, 105.0, 110.0], "2024-01-10"), pd.DataFrame()
    )
    change = PriceFetcher("1d", now=datetime(2024, 1, 10)).get_price_change("AAPL")
    assert change == pytest.approx(10.0)


@patch("etf_treemap.prices.PriceFetcher._is_market_open", return_value=True)
@patch("etf_treemap.prices.datetime")
@patch("etf_treemap.prices.yf.Ticker")
def test_1d_holiday_detected_from_data(mock_cls: Mock, mock_dt: Mock, _open: Mock) -> None:
    """Weekday in market hours but the newest bars are from an earlier day: use daily closes."""
    mock_dt.now.return_value = _fixed_now("2024-01-15")  # MLK day
    mock_cls.return_value = _ticker(
        _intraday([100.0, 101.0], "2024-01-12"), _daily([100.0, 102.0, 104.0], "2024-01-12")
    )
    change = PriceFetcher("1d", now=datetime(2024, 1, 15)).get_price_change("AAPL")
    assert change == pytest.approx((104.0 - 102.0) / 102.0 * 100)


@patch("etf_treemap.prices.PriceFetcher._is_market_open", return_value=False)
@patch("etf_treemap.prices.yf.Ticker")
def test_1d_closed_uses_last_two_daily_closes(mock_cls: Mock, _open: Mock) -> None:
    ticker = Mock()
    ticker.history.return_value = _daily([90.0, 100.0, 110.0], "2024-01-12")
    mock_cls.return_value = ticker
    change = PriceFetcher("1d", now=datetime(2024, 1, 13)).get_price_change("AAPL")
    ticker.history.assert_called_once_with(period="5d", interval="1d")
    assert change == pytest.approx(10.0)


@given(
    prev=st.floats(min_value=1, max_value=1e4),
    last=st.floats(min_value=1, max_value=1e4),
)
def test_1d_closed_change_property(prev: float, last: float) -> None:
    ticker = Mock()
    ticker.history.return_value = _daily([prev * 2, prev, last], "2024-01-12")
    with patch("etf_treemap.prices.yf.Ticker", return_value=ticker), patch(
        "etf_treemap.prices.PriceFetcher._is_market_open", return_value=False
    ):
        change = PriceFetcher("1d", now=datetime(2024, 1, 13)).get_price_change("AAPL")
    assert change == pytest.approx((last - prev) / prev * 100)


# --- Finding 9: headless rendering and error handling ----------------------

def _blocks() -> list[TreemapBlock]:
    return [
        TreemapBlock("AAPL", 0.5, 5.0, 2.5, "up"),
        TreemapBlock("MSFT", 0.5, -3.0, 1.5, "down"),
    ]


def test_headless_render_without_display(tmp_path: Path) -> None:
    """Rendering must work with no DISPLAY and no MPLBACKEND, in a fresh interpreter."""
    out = tmp_path / "t.png"
    code = (
        "from datetime import datetime;"
        "from etf_treemap.calculator import TreemapBlock;"
        "from etf_treemap.visualizer import TreemapVisualizer;"
        "TreemapVisualizer('T', (datetime(2024,1,1), datetime(2024,1,8)))"
        f".generate_treemap([TreemapBlock('A',.5,5.,2.5,'up'),TreemapBlock('B',.5,-3.,1.5,'down')], {str(out)!r});"
        "import sys; sys.exit(1 if 'matplotlib.pyplot' in sys.modules else 0)"
    )
    env = {k: v for k, v in __import__("os").environ.items() if k not in ("DISPLAY", "MPLBACKEND")}
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert out.stat().st_size > 0


def _run_main_with_visualizer_error(exc: Exception, tmp_path: Path,
                                    monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.chdir(tmp_path)
    with patch("etf_treemap.main.parse_arguments", return_value=("UFO", "1w", "h.csv")), \
         patch("etf_treemap.main.HoldingsFetcher") as hf, \
         patch("etf_treemap.main.PriceFetcher") as pf, \
         patch("etf_treemap.main.PerformanceCalculator") as calc, \
         patch("etf_treemap.main.TreemapVisualizer") as vis:
        hf.return_value.get_holdings.return_value = [Holding("AAPL", "Apple", 0.1)]
        pf.return_value.get_price_change.return_value = 1.0
        pf.return_value.date_range = (datetime(2024, 1, 1), datetime(2024, 1, 8))
        calc.return_value.prepare_treemap_data.return_value = _blocks()
        vis.return_value.generate_treemap.side_effect = exc
        return main()


@pytest.mark.parametrize(
    "exc, message",
    [
        (OSError(28, "No space left on device"), "Could not save file"),
        (RuntimeError("boom"), "Visualization error"),
        (ZeroDivisionError("x"), "Visualization error"),
    ],
)
def test_visualization_errors_logged_with_traceback(
    exc: Exception, message: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR):
        code = _run_main_with_visualizer_error(exc, tmp_path, monkeypatch)
    assert code == 1
    assert message in capsys.readouterr().out
    assert any(r.exc_info and r.exc_info[1] is exc for r in caplog.records)


def test_unexpected_visualization_error_is_not_swallowed_as_visualization_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Programming errors (e.g. AttributeError) fall through to the top-level handler."""
    code = _run_main_with_visualizer_error(AttributeError("bug"), tmp_path, monkeypatch)
    assert code == 1
    out = capsys.readouterr().out
    assert "Unexpected error" in out and "Visualization error" not in out
