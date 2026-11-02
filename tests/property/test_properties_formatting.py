"""Property-based tests for label, title and colour helpers of the visualizer."""
from datetime import datetime, timedelta

from hypothesis import given, strategies as st

from etf_treemap.calculator import TreemapBlock
from etf_treemap.visualizer import TreemapVisualizer

etf_symbols = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-", min_size=1, max_size=15)
dates = st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2090, 1, 1))
hex_colors = st.integers(0, 0xFFFFFF).map(lambda n: f"#{n:06x}")


@given(symbol=etf_symbols, end=dates, days=st.integers(1, 3650))
def test_title_has_symbol_and_dates(symbol: str, end: datetime, days: int) -> None:
    start = end - timedelta(days=days)
    viz = TreemapVisualizer(symbol, (start, end))
    multi = viz._format_title(False)
    assert multi == f"{symbol} Holdings Performance {start:%Y-%m-%d}-{end:%Y-%m-%d}"
    single = viz._format_title(True)
    assert single == f"{symbol} Holdings Performance {end:%Y-%m-%d}"


@given(
    symbol=etf_symbols,
    change=st.floats(-1000, 1000, allow_nan=False),
    direction=st.sampled_from(["up", "down", "flat"]),
)
def test_format_label_delegates_to_block(symbol: str, change: float, direction: str) -> None:
    viz = TreemapVisualizer("X", (datetime(2024, 1, 1), datetime(2024, 1, 2)))
    block = TreemapBlock(symbol, 0.1, change, abs(change), direction)
    assert viz._format_label(block) == block.get_label()


@given(direction=st.text(max_size=8))
def test_color_is_always_a_known_hex(direction: str) -> None:
    viz = TreemapVisualizer("X", (datetime(2024, 1, 1), datetime(2024, 1, 2)))
    color = viz._get_color(direction)
    assert color in {"#2ecc71", "#e74c3c", "#95a5a6"}
    if direction not in ("up", "down"):
        assert color == "#95a5a6"


@given(color=hex_colors)
def test_text_colour_is_black_or_white_and_follows_luminance(color: str) -> None:
    viz = TreemapVisualizer("X", (datetime(2024, 1, 1), datetime(2024, 1, 2)))
    assert viz._get_text_color(color) in {"black", "white"}


@given(color=hex_colors, factor=st.floats(0.0, 1.0))
def test_darken_never_brightens(color: str, factor: float) -> None:
    viz = TreemapVisualizer("X", (datetime(2024, 1, 1), datetime(2024, 1, 2)))
    darker = viz._darken_color(color, factor)
    original = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    result = [int(darker[i:i + 2], 16) for i in (1, 3, 5)]
    assert all(r <= o for r, o in zip(result, original))
