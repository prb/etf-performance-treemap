"""Property-based tests for lookback-period and holdings-file parsing."""
import csv
import io

import pytest
from hypothesis import given, strategies as st

from etf_treemap.cli import parse_lookback_period, validate_lookback_period
from etf_treemap.holdings import HoldingsFetcher, HoldingsFormatError

units = st.sampled_from(["d", "w", "m", "y"])


@given(value=st.integers(1, 10_000), unit=units)
def test_lookback_roundtrip(value: int, unit: str) -> None:
    period = f"{value}{unit}"
    assert validate_lookback_period(period)
    assert parse_lookback_period(period) == (value, unit)


@given(text=st.text(max_size=8))
def test_parse_agrees_with_validate(text: str) -> None:
    if validate_lookback_period(text):
        value, unit = parse_lookback_period(text)
        assert value > 0 and unit in "dwmy"
    else:
        with pytest.raises(ValueError):
            parse_lookback_period(text)


tickers = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=1, max_size=6)
rows = st.lists(
    st.tuples(
        st.text(alphabet="abcdefghij ,.", min_size=1, max_size=20).filter(lambda s: s.strip()),
        tickers,
        st.integers(1, 99_999),  # weight in basis points of a percent: 0.001% .. 99.999%
    ),
    min_size=1, max_size=25,
)


@given(rows=rows, metadata=st.lists(st.text(alphabet="abc :", max_size=15), max_size=4))
def test_etfdb_csv_roundtrip(rows: list[tuple[str, str, int]], metadata: list[str]) -> None:
    """Names (with commas), symbols and percent weights survive writing and parsing,
    even with metadata lines before the header."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    for line in metadata:
        buf.write(line.replace(",", " ") + "\n")
    writer.writerow(["Holding", "Symbol", "Weighting"])
    for name, symbol, bp in rows:
        writer.writerow([name, symbol, f"{bp / 1000:.3f}%"])
    parsed = HoldingsFetcher()._parse_csv(buf.getvalue(), "TEST")
    assert len(parsed) == len(rows)
    for holding, (name, symbol, bp) in zip(parsed, rows):
        assert holding.symbol == symbol
        assert holding.name == name.strip()
        assert holding.weight == pytest.approx(bp / 100_000)


@given(text=st.text(alphabet="xyz ,\n", max_size=60))
def test_headerless_text_is_rejected(text: str) -> None:
    with pytest.raises(HoldingsFormatError):
        HoldingsFetcher()._parse_csv(text, "TEST")
