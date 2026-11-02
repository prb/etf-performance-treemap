"""Property-based tests for calculator -> visualizer scenarios."""
import struct
from datetime import datetime
from pathlib import Path

from hypothesis import HealthCheck, given, settings, strategies as st

from etf_treemap.calculator import PerformanceCalculator
from etf_treemap.holdings import Holding
from etf_treemap.visualizer import TreemapVisualizer

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

scenarios = st.lists(
    st.tuples(
        st.floats(0.0001, 0.2, allow_nan=False),
        # Realistic moves only: exactly flat, or at least 0.01%. Subnormal-scale
        # moves (~1e-214) make squarify divide by zero; see quality-pass report.
        st.floats(-50, 50, allow_nan=False).filter(lambda c: c == 0 or abs(c) >= 0.01),
    ),
    min_size=1, max_size=15,
)


@settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(scenario=scenarios)
def test_any_nonzero_scenario_renders_png(scenario: list[tuple[float, float]], tmp_path_factory) -> None:
    """Any holdings/price-change mix with some non-zero contribution renders a valid PNG;
    an all-zero mix is rejected with ValueError instead of producing a file."""
    holdings = [Holding(f"S{i}", f"Name {i}", w) for i, (w, _) in enumerate(scenario)]
    changes = {f"S{i}": c for i, (_, c) in enumerate(scenario)}
    blocks = PerformanceCalculator().prepare_treemap_data(holdings, changes)
    out = Path(tmp_path_factory.mktemp("render")) / "out.png"
    viz = TreemapVisualizer("TEST", (datetime(2024, 1, 1), datetime(2024, 1, 8)))
    if any(b.contribution > 0 for b in blocks):
        viz.generate_treemap(blocks, str(out))
        data = out.read_bytes()
        assert data.startswith(PNG_SIGNATURE)
        width, height = struct.unpack(">II", data[16:24])
        assert width > 0 and height > 0
    else:
        try:
            viz.generate_treemap(blocks, str(out))
        except ValueError:
            assert not out.exists()
        else:  # pragma: no cover
            raise AssertionError("expected ValueError")
