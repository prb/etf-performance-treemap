"""Offline end-to-end tests: example holdings CSV + mocked yfinance -> PNG."""
import shutil
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from etf_treemap.main import main

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXAMPLE_CSV = Path(__file__).resolve().parents[2] / "example-holdings" / "QQQM-holdings.csv"


def _fake_ticker(symbol: str) -> Mock:
    """Deterministic fake yfinance Ticker: up, down or flat by symbol hash."""
    start = 100.0
    end = start * (1 + ((sum(map(ord, symbol)) % 21) - 10) / 100)
    ticker = Mock()
    ticker.history.return_value = pd.DataFrame({"Close": [start, (start + end) / 2, end]})
    return ticker


def _run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *args: str) -> int:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["etf-treemap", *args])
    return main()


def test_example_holdings_to_png(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                                 capsys: pytest.CaptureFixture[str]) -> None:
    """Full pipeline writes a non-trivial PNG named after the ETF and period."""
    csv_path = tmp_path / "QQQM-holdings.csv"
    shutil.copy(EXAMPLE_CSV, csv_path)
    with patch("etf_treemap.prices.yf.Ticker", side_effect=_fake_ticker):
        code = _run(monkeypatch, tmp_path, "QQQM", "1w", "--csv", str(csv_path))
    output = tmp_path / "QQQM-1w-treemap.png"
    assert code == 0
    assert output.is_file()
    data = output.read_bytes()
    assert data.startswith(PNG_SIGNATURE)
    assert len(data) > 10_000
    assert str(output) in capsys.readouterr().out


def test_missing_price_data_is_excluded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Holdings with no price history are dropped but the chart is still written."""
    csv_path = tmp_path / "h.csv"
    csv_path.write_text("Holding,Symbol,Weighting\nA Inc,AAA,60%\nB Inc,BBB,40%\n")

    def fake(symbol: str) -> Mock:
        if symbol == "BBB":
            ticker = Mock()
            ticker.history.return_value = pd.DataFrame({"Close": []})
            return ticker
        return _fake_ticker(symbol)

    with patch("etf_treemap.prices.yf.Ticker", side_effect=fake), \
            patch("etf_treemap.prices.time.sleep"):
        code = _run(monkeypatch, tmp_path, "TEST", "1w", "--csv", str(csv_path))
    assert code == 0
    assert (tmp_path / "TEST-1w-treemap.png").read_bytes().startswith(PNG_SIGNATURE)


def test_no_price_data_fails_without_png(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                                         capsys: pytest.CaptureFixture[str]) -> None:
    csv_path = tmp_path / "h.csv"
    csv_path.write_text("Holding,Symbol,Weighting\nA Inc,AAA,100%\n")
    empty = Mock()
    empty.history.return_value = pd.DataFrame({"Close": []})
    with patch("etf_treemap.prices.yf.Ticker", return_value=empty), \
            patch("etf_treemap.prices.time.sleep"):
        code = _run(monkeypatch, tmp_path, "TEST", "1w", "--csv", str(csv_path))
    assert code == 1
    assert "No valid price data" in capsys.readouterr().out
    assert not (tmp_path / "TEST-1w-treemap.png").exists()


def test_missing_holdings_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                               capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI rejects a missing file with a usage error (exit 2) and no PNG."""
    with pytest.raises(SystemExit) as excinfo:
        _run(monkeypatch, tmp_path, "TEST", "1w", "--csv", str(tmp_path / "nope.csv"))
    assert excinfo.value.code == 2
    assert "Holdings file not found" in capsys.readouterr().err
    assert not list(tmp_path.glob("*.png"))
