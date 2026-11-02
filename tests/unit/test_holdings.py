"""Unit tests for holdings file loading and format detection."""
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from etf_treemap.holdings import Holding, HoldingsFetcher, HoldingsFormatError

EXAMPLES = Path(__file__).resolve().parents[2] / "example-holdings"


@pytest.fixture
def fetcher() -> HoldingsFetcher:
    return HoldingsFetcher()


class TestSupportedFormats:
    """Each supported sample format parses into holdings."""

    def test_etfdb_style_with_metadata(self, fetcher):
        holdings = fetcher.get_holdings("QQQM", str(EXAMPLES / "QQQM-holdings.csv"))
        assert holdings[0] == Holding("NVDA", "NVIDIA Corporation", pytest.approx(0.0872))
        assert len(holdings) > 50

    def test_quoted_names_with_commas(self, fetcher):
        holdings = fetcher.get_holdings("RSP", str(EXAMPLES / "RSP-holdings.csv"))
        assert any(h.name == "Moderna, Inc." and h.symbol == "MRNA" for h in holdings)

    def test_invesco_monthly(self, fetcher):
        path = EXAMPLES / "invesco_nasdaq_100_etf-monthly_holdings.csv"
        holdings = fetcher.get_holdings("QQQM", str(path))
        assert holdings[0].symbol == "NVDA"
        assert holdings[0].name == "NVIDIA Corp"
        assert holdings[0].weight == pytest.approx(0.0872)

    def test_fund_administrator_export(self, fetcher):
        path = EXAMPLES / "SpearAdv.40FU.FU_Holdings.csv"
        holdings = fetcher.get_holdings("SPRX", str(path))
        assert holdings[0].symbol == "COHR"
        assert holdings[0].name == "Coherent Corp"
        assert holdings[0].weight == pytest.approx(0.0948)

    @pytest.mark.parametrize("sample", sorted(p.name for p in EXAMPLES.glob("*.csv")))
    def test_every_example_file_parses(self, fetcher, sample):
        assert fetcher.get_holdings("ANY", str(EXAMPLES / sample))

    def test_bom_is_ignored(self, fetcher, tmp_path):
        path = tmp_path / "h.csv"
        path.write_bytes(b"\xef\xbb\xbfSymbol,Name,Weight\nAAPL,Apple,5%\n")
        assert fetcher.get_holdings("X", str(path))[0].symbol == "AAPL"


class TestErrors:
    def test_missing_file_raises_file_not_found(self, fetcher, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            fetcher.get_holdings("UFO", str(tmp_path / "nope.csv"))

    def test_directory_is_not_a_file(self, fetcher, tmp_path):
        with pytest.raises(FileNotFoundError):
            fetcher.get_holdings("UFO", str(tmp_path))

    def test_unsupported_format_lists_supported_formats(self, fetcher, tmp_path):
        path = tmp_path / "bad.csv"
        path.write_text("Foo,Bar\n1,2\n")
        with pytest.raises(HoldingsFormatError, match="Supported holdings file formats") as exc:
            fetcher.get_holdings("UFO", str(path))
        assert isinstance(exc.value, ValueError)

    def test_empty_file(self, fetcher, tmp_path):
        path = tmp_path / "empty.csv"
        path.write_text("")
        with pytest.raises(HoldingsFormatError):
            fetcher.get_holdings("UFO", str(path))

    def test_header_without_rows(self, fetcher, tmp_path):
        path = tmp_path / "header.csv"
        path.write_text("Holding,Symbol,Weighting\n")
        with pytest.raises(HoldingsFormatError, match="No holdings rows"):
            fetcher.get_holdings("UFO", str(path))

    def test_binary_file(self, fetcher, tmp_path):
        path = tmp_path / "bin.csv"
        path.write_bytes(b"\xff\xfe\x00\x80\x81")
        with pytest.raises(HoldingsFormatError):
            fetcher.get_holdings("UFO", str(path))


class TestParseProperties:
    @given(
        st.lists(
            st.tuples(
                st.from_regex(r"[A-Z]{1,5}", fullmatch=True),
                st.floats(min_value=0.0001, max_value=100, allow_nan=False),
            ),
            min_size=1,
            max_size=20,
        )
    )
    def test_percentage_rows_round_trip(self, rows):
        content = "Holding,Symbol,Weighting\n" + "\n".join(
            f"Name {sym},{sym},{weight:.4f}%" for sym, weight in rows
        )
        holdings = HoldingsFetcher()._parse_csv(content, "T")
        assert [h.symbol for h in holdings] == [sym for sym, _ in rows]
        for holding, (_, weight) in zip(holdings, rows):
            assert holding.weight == pytest.approx(float(f"{weight:.4f}") / 100)
