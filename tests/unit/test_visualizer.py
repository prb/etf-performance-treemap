"""Unit tests for visualizer module."""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import os
from etf_treemap.visualizer import TreemapVisualizer
from etf_treemap.calculator import TreemapBlock


class TestTreemapVisualizer:
    """Test cases for TreemapVisualizer class."""
    
    @pytest.fixture
    def sample_blocks(self):
        """Create sample treemap blocks for testing."""
        return [
            TreemapBlock(
                symbol="AAPL",
                weight=0.30,
                price_change=5.5,
                contribution=1.65,
                direction="up"
            ),
            TreemapBlock(
                symbol="GOOGL",
                weight=0.25,
                price_change=-3.2,
                contribution=0.80,
                direction="down"
            ),
            TreemapBlock(
                symbol="MSFT",
                weight=0.20,
                price_change=0.0,
                contribution=0.0,
                direction="flat"
            ),
            TreemapBlock(
                symbol="TSLA",
                weight=0.15,
                price_change=-8.7,
                contribution=1.305,
                direction="down"
            ),
            TreemapBlock(
                symbol="NVDA",
                weight=0.10,
                price_change=12.3,
                contribution=1.23,
                direction="up"
            )
        ]
    
    @pytest.fixture
    def single_day_visualizer(self):
        """Create visualizer for single day (1d lookback)."""
        date = datetime(2024, 1, 15)
        return TreemapVisualizer("UFO", (date, date))
    
    @pytest.fixture
    def multi_day_visualizer(self):
        """Create visualizer for multi-day period."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 15)
        return TreemapVisualizer("SPY", (start_date, end_date))
    
    def test_init(self):
        """Test TreemapVisualizer initialization."""
        etf_symbol = "UFO"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 15)
        
        visualizer = TreemapVisualizer(etf_symbol, (start_date, end_date))
        
        assert visualizer.etf_symbol == etf_symbol
        assert visualizer.date_range == (start_date, end_date)
    
    def test_format_title_single_day(self, single_day_visualizer):
        """Test title formatting for single day (1d lookback)."""
        title = single_day_visualizer._format_title(is_single_day=True)
        
        assert title == "UFO Holdings Performance 2024-01-15"
        assert "UFO" in title
        assert "2024-01-15" in title
    
    def test_format_title_multi_day(self, multi_day_visualizer):
        """Test title formatting for multi-day period."""
        title = multi_day_visualizer._format_title(is_single_day=False)
        
        assert title == "SPY Holdings Performance 2024-01-01-2024-01-15"
        assert "SPY" in title
        assert "2024-01-01" in title
        assert "2024-01-15" in title
        assert "-" in title
    
    def test_format_label_up(self):
        """Test label formatting for 'up' direction."""
        visualizer = TreemapVisualizer("UFO", (datetime.now(), datetime.now()))
        block = TreemapBlock(
            symbol="AAPL",
            weight=0.30,
            price_change=5.5,
            contribution=1.65,
            direction="up"
        )
        
        label = visualizer._format_label(block)
        
        assert "AAPL" in label
        assert "⬆" in label
        assert "5.50%" in label
    
    def test_format_label_down(self):
        """Test label formatting for 'down' direction."""
        visualizer = TreemapVisualizer("UFO", (datetime.now(), datetime.now()))
        block = TreemapBlock(
            symbol="GOOGL",
            weight=0.25,
            price_change=-3.2,
            contribution=0.80,
            direction="down"
        )
        
        label = visualizer._format_label(block)
        
        assert "GOOGL" in label
        assert "⬇" in label
        assert "3.20%" in label
    
    def test_format_label_flat(self):
        """Test label formatting for 'flat' direction."""
        visualizer = TreemapVisualizer("UFO", (datetime.now(), datetime.now()))
        block = TreemapBlock(
            symbol="MSFT",
            weight=0.20,
            price_change=0.0,
            contribution=0.0,
            direction="flat"
        )
        
        label = visualizer._format_label(block)
        
        assert "MSFT" in label
        assert "⬆" not in label
        assert "⬇" not in label
        assert "0.00%" in label
    
    def test_get_color_up(self):
        """Test color mapping for 'up' direction."""
        visualizer = TreemapVisualizer("UFO", (datetime.now(), datetime.now()))
        
        color = visualizer._get_color("up")
        
        assert color == '#2ecc71'  # Green
    
    def test_get_color_down(self):
        """Test color mapping for 'down' direction."""
        visualizer = TreemapVisualizer("UFO", (datetime.now(), datetime.now()))
        
        color = visualizer._get_color("down")
        
        assert color == '#e74c3c'  # Red
    
    def test_get_color_flat(self):
        """Test color mapping for 'flat' direction."""
        visualizer = TreemapVisualizer("UFO", (datetime.now(), datetime.now()))
        
        color = visualizer._get_color("flat")
        
        assert color == '#95a5a6'  # Grey
    
    def test_get_color_invalid(self):
        """Test color mapping for invalid direction defaults to grey."""
        visualizer = TreemapVisualizer("UFO", (datetime.now(), datetime.now()))
        
        color = visualizer._get_color("invalid")
        
        assert color == '#95a5a6'  # Default to grey
    
    def test_get_text_color_dark_background(self):
        """Test text color for dark background (should be white)."""
        visualizer = TreemapVisualizer("UFO", (datetime.now(), datetime.now()))
        
        # Red is relatively dark
        text_color = visualizer._get_text_color('#e74c3c')
        
        assert text_color == 'white'
    
    def test_get_text_color_light_background(self):
        """Test text color for light background (should be black)."""
        visualizer = TreemapVisualizer("UFO", (datetime.now(), datetime.now()))
        
        # Light yellow
        text_color = visualizer._get_text_color('#ffff99')
        
        assert text_color == 'black'
    
    def test_get_text_color_invalid(self):
        """Test text color for invalid color defaults to black."""
        visualizer = TreemapVisualizer("UFO", (datetime.now(), datetime.now()))
        
        text_color = visualizer._get_text_color('invalid_color')
        
        assert text_color == 'black'
    
    def test_generate_treemap_creates_file(self, single_day_visualizer, sample_blocks):
        """Test that generate_treemap creates a PNG file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_treemap.png")
            
            single_day_visualizer.generate_treemap(sample_blocks, output_path)
            
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
    
    def test_generate_treemap_empty_blocks_raises_error(self, single_day_visualizer):
        """Test that generate_treemap raises error for empty blocks list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_treemap.png")
            
            with pytest.raises(ValueError, match="Cannot generate treemap: no blocks provided"):
                single_day_visualizer.generate_treemap([], output_path)
    
    def test_generate_treemap_all_zero_contribution_raises_error(self, single_day_visualizer):
        """Test that generate_treemap raises error when all blocks have zero contribution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_treemap.png")
            
            zero_blocks = [
                TreemapBlock(
                    symbol="MSFT",
                    weight=0.50,
                    price_change=0.0,
                    contribution=0.0,
                    direction="flat"
                ),
                TreemapBlock(
                    symbol="AAPL",
                    weight=0.50,
                    price_change=0.0,
                    contribution=0.0,
                    direction="flat"
                )
            ]
            
            with pytest.raises(ValueError, match="Cannot generate treemap: all blocks have zero contribution"):
                single_day_visualizer.generate_treemap(zero_blocks, output_path)
    
    def test_generate_treemap_single_block(self, single_day_visualizer):
        """Test treemap generation with single block."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_treemap.png")
            
            single_block = [
                TreemapBlock(
                    symbol="AAPL",
                    weight=1.0,
                    price_change=5.5,
                    contribution=5.5,
                    direction="up"
                )
            ]
            
            single_day_visualizer.generate_treemap(single_block, output_path)
            
            assert os.path.exists(output_path)
    
    def test_generate_treemap_multi_day_title(self, multi_day_visualizer, sample_blocks):
        """Test treemap generation with multi-day date range."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_treemap.png")
            
            multi_day_visualizer.generate_treemap(sample_blocks, output_path)
            
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
