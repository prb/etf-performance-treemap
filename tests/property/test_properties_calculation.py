"""Property-based tests for calculation functions."""
import math

from hypothesis import given, strategies as st

from etf_treemap.calculator import PerformanceCalculator, TreemapBlock
from etf_treemap.holdings import Holding

weights = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
changes = st.floats(min_value=-100.0, max_value=1000.0, allow_nan=False)
symbols = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=1, max_size=6)

holding_lists = st.lists(
    st.builds(Holding, symbol=symbols, name=st.just("N"), weight=weights),
    max_size=30, unique_by=lambda h: h.symbol,
)

calc = PerformanceCalculator()


@given(weight=weights, change=changes)
def test_contribution_is_weight_times_change(weight: float, change: float) -> None:
    assert calc.calculate_contribution(Holding("X", "X", weight), change) == weight * change


@given(change=changes)
def test_direction_matches_sign(change: float) -> None:
    expected = "up" if change > 0 else "down" if change < 0 else "flat"
    assert calc.classify_direction(change) == expected


@given(holdings=holding_lists, data=st.data())
def test_blocks_cover_exactly_priced_holdings(holdings: list[Holding], data: st.DataObject) -> None:
    priced = {h.symbol: data.draw(changes) for h in holdings if data.draw(st.booleans())}
    blocks = calc.prepare_treemap_data(holdings, priced)
    # Exactly the holdings with prices, in input order
    assert [b.symbol for b in blocks] == [h.symbol for h in holdings if h.symbol in priced]
    by_symbol = {h.symbol: h for h in holdings}
    for block in blocks:
        holding = by_symbol[block.symbol]
        assert block.contribution >= 0
        assert math.isclose(block.contribution, abs(holding.weight * priced[block.symbol]))
        assert block.weight == holding.weight
        assert block.direction == calc.classify_direction(priced[block.symbol])


@given(holdings=holding_lists)
def test_no_prices_gives_no_blocks(holdings: list[Holding]) -> None:
    assert calc.prepare_treemap_data(holdings, {}) == []


@given(symbol=symbols, change=changes)
def test_label_shape(symbol: str, change: float) -> None:
    direction = calc.classify_direction(change)
    label = TreemapBlock(symbol, 0.1, change, abs(0.1 * change), direction).get_label()
    assert label.startswith(f"{symbol} ")
    assert label.endswith("%")
    # Arrow only for non-flat values; the number is always the absolute change
    assert ("⬆" in label) == (direction == "up")
    assert ("⬇" in label) == (direction == "down")
    assert f"{abs(change):.2f}%" in label
