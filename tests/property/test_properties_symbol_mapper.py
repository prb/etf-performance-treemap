"""Property-based tests for symbol normalisation."""
import pytest
from hypothesis import assume, given, strategies as st

from etf_treemap.symbol_mapper import (
    SYMBOL_OVERRIDE_MAP,
    SYMBOL_SUFFIX_MAP,
    get_display_symbol,
    normalize_symbol,
)

tickers = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=1, max_size=8)
plain_names = st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=0, max_size=30)


@given(ticker=tickers, code=st.sampled_from(sorted(SYMBOL_SUFFIX_MAP)))
def test_country_code_maps_to_suffix(ticker: str, code: str) -> None:
    assume(ticker not in SYMBOL_OVERRIDE_MAP)
    assert normalize_symbol(f"{ticker} {code}") == ticker + SYMBOL_SUFFIX_MAP[code]


@given(ticker=tickers, name=plain_names)
def test_lowercase_names_never_trigger_heuristic(ticker: str, name: str) -> None:
    assume(ticker not in SYMBOL_OVERRIDE_MAP)
    assert normalize_symbol(ticker, name) == ticker


@given(
    ticker=tickers,
    prefix=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10),
    suffix=st.sampled_from(["AB", "NV", "SA", "SpA"]),
)
def test_suffix_glued_to_a_word_is_not_a_legal_form(ticker: str, prefix: str, suffix: str) -> None:
    """'Kebab' style endings: suffix letters inside a word do not count."""
    assume(ticker not in SYMBOL_OVERRIDE_MAP)
    assert normalize_symbol(ticker, prefix + suffix) == ticker
    assert normalize_symbol(ticker, "NASA") == ticker


@given(
    ticker=tickers,
    prefix=st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=15),
    suffix=st.sampled_from([("AB", ".ST"), ("NV", ".AS"), ("SpA", ".MI"), ("SA", ".PA")]),
)
def test_whole_word_suffix_triggers_heuristic(ticker: str, prefix: str, suffix: tuple[str, str]) -> None:
    assume(ticker not in SYMBOL_OVERRIDE_MAP)
    result = normalize_symbol(ticker, f"{prefix} {suffix[0]}")
    assert result == ticker + suffix[1]


@given(ticker=tickers, share_class=st.sampled_from(list("ABCDEFG")))
def test_share_class_period_becomes_hyphen(ticker: str, share_class: str) -> None:
    assume(f"{ticker}.{share_class}" not in SYMBOL_OVERRIDE_MAP)
    assert normalize_symbol(f"{ticker}.{share_class}") == f"{ticker}-{share_class}"


@given(symbol=st.text(max_size=12), name=st.text(max_size=30))
def test_normalize_never_raises_and_is_str(symbol: str, name: str) -> None:
    assert isinstance(normalize_symbol(symbol, name), str)


@pytest.mark.parametrize("symbol", sorted(SYMBOL_OVERRIDE_MAP))
def test_override_targets_have_exchange_suffix_and_display_roundtrip(symbol: str) -> None:
    target = SYMBOL_OVERRIDE_MAP[symbol]
    assert target.startswith(symbol + ".")
    assert get_display_symbol(target) == symbol


@given(base=tickers, ext=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=3))
def test_display_symbol_strips_suffix(base: str, ext: str) -> None:
    assert get_display_symbol(f"{base}.{ext}") == base
    assert get_display_symbol(base) == base
