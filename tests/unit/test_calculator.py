"""Unit tests for calculator module."""

import pytest
from etf_treemap.calculator import PerformanceCalculator, TreemapBlock
from etf_treemap.holdings import Holding


class TestPerformanceCalculator:
    """Test cases for performance contribution calculations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = PerformanceCalculator()
    
    def test_calculate_contribution_positive(self):
        """Test contribution calculation with positive price change."""
        holding = Holding(symbol="AAPL", name="Apple Inc.", weight=0.05)
        price_change = 10.0  # 10% increase
        
        contribution = self.calculator.calculate_contribution(holding, price_change)
        
        assert contribution == 0.5  # 0.05 * 10.0
    
    def test_calculate_contribution_negative(self):
        """Test contribution calculation with negative price change."""
        holding = Holding(symbol="TSLA", name="Tesla Inc.", weight=0.03)
        price_change = -5.0  # 5% decrease
        
        contribution = self.calculator.calculate_contribution(holding, price_change)
        
        assert contribution == -0.15  # 0.03 * -5.0
    
    def test_calculate_contribution_zero(self):
        """Test contribution calculation with zero price change."""
        holding = Holding(symbol="MSFT", name="Microsoft Corp.", weight=0.04)
        price_change = 0.0
        
        contribution = self.calculator.calculate_contribution(holding, price_change)
        
        assert contribution == 0.0
    
    def test_classify_direction_positive(self):
        """Test direction classification for positive price change."""
        direction = self.calculator.classify_direction(5.5)
        assert direction == "up"
    
    def test_classify_direction_negative(self):
        """Test direction classification for negative price change."""
        direction = self.calculator.classify_direction(-3.2)
        assert direction == "down"
    
    def test_classify_direction_zero(self):
        """Test direction classification for zero price change."""
        direction = self.calculator.classify_direction(0.0)
        assert direction == "flat"
    
    def test_classify_direction_very_small_positive(self):
        """Test direction classification for very small positive change."""
        direction = self.calculator.classify_direction(0.001)
        assert direction == "up"
    
    def test_classify_direction_very_small_negative(self):
        """Test direction classification for very small negative change."""
        direction = self.calculator.classify_direction(-0.001)
        assert direction == "down"
    
    def test_prepare_treemap_data_basic(self):
        """Test preparing treemap data with basic holdings."""
        holdings = [
            Holding(symbol="AAPL", name="Apple Inc.", weight=0.05),
            Holding(symbol="TSLA", name="Tesla Inc.", weight=0.03),
            Holding(symbol="MSFT", name="Microsoft Corp.", weight=0.04),
        ]
        price_changes = {
            "AAPL": 10.0,
            "TSLA": -5.0,
            "MSFT": 0.0,
        }
        
        blocks = self.calculator.prepare_treemap_data(holdings, price_changes)
        
        assert len(blocks) == 3
        
        # Check AAPL block
        aapl_block = next(b for b in blocks if b.symbol == "AAPL")
        assert aapl_block.weight == 0.05
        assert aapl_block.price_change == 10.0
        assert aapl_block.contribution == 0.5  # abs(0.05 * 10.0)
        assert aapl_block.direction == "up"
        
        # Check TSLA block
        tsla_block = next(b for b in blocks if b.symbol == "TSLA")
        assert tsla_block.weight == 0.03
        assert tsla_block.price_change == -5.0
        assert tsla_block.contribution == 0.15  # abs(0.03 * -5.0)
        assert tsla_block.direction == "down"
        
        # Check MSFT block
        msft_block = next(b for b in blocks if b.symbol == "MSFT")
        assert msft_block.weight == 0.04
        assert msft_block.price_change == 0.0
        assert msft_block.contribution == 0.0  # abs(0.04 * 0.0)
        assert msft_block.direction == "flat"
    
    def test_prepare_treemap_data_missing_price_data(self):
        """Test that holdings without price data are skipped."""
        holdings = [
            Holding(symbol="AAPL", name="Apple Inc.", weight=0.05),
            Holding(symbol="UNKNOWN", name="Unknown Corp.", weight=0.02),
            Holding(symbol="TSLA", name="Tesla Inc.", weight=0.03),
        ]
        price_changes = {
            "AAPL": 10.0,
            "TSLA": -5.0,
            # UNKNOWN is missing
        }
        
        blocks = self.calculator.prepare_treemap_data(holdings, price_changes)
        
        # Should only have 2 blocks (UNKNOWN skipped)
        assert len(blocks) == 2
        assert all(b.symbol != "UNKNOWN" for b in blocks)
    
    def test_prepare_treemap_data_empty_holdings(self):
        """Test preparing treemap data with empty holdings list."""
        holdings = []
        price_changes = {}
        
        blocks = self.calculator.prepare_treemap_data(holdings, price_changes)
        
        assert len(blocks) == 0
    
    def test_prepare_treemap_data_uses_absolute_value(self):
        """Test that contribution uses absolute value for block size (Requirement 6.5)."""
        holdings = [
            Holding(symbol="UP", name="Up Stock", weight=0.05),
            Holding(symbol="DOWN", name="Down Stock", weight=0.05),
        ]
        price_changes = {
            "UP": 10.0,
            "DOWN": -10.0,
        }
        
        blocks = self.calculator.prepare_treemap_data(holdings, price_changes)
        
        up_block = next(b for b in blocks if b.symbol == "UP")
        down_block = next(b for b in blocks if b.symbol == "DOWN")
        
        # Both should have same contribution (absolute value)
        assert up_block.contribution == 0.5
        assert down_block.contribution == 0.5


class TestTreemapBlock:
    """Test cases for TreemapBlock data class."""
    
    def test_get_label_up(self):
        """Test label formatting for upward movement."""
        block = TreemapBlock(
            symbol="AAPL",
            weight=0.05,
            price_change=5.23,
            contribution=0.2615,
            direction="up"
        )
        
        label = block.get_label()
        
        assert label == "AAPL ⬆5.23%"
    
    def test_get_label_down(self):
        """Test label formatting for downward movement."""
        block = TreemapBlock(
            symbol="TSLA",
            weight=0.03,
            price_change=-3.45,
            contribution=0.1035,
            direction="down"
        )
        
        label = block.get_label()
        
        assert label == "TSLA ⬇3.45%"
    
    def test_get_label_flat(self):
        """Test label formatting for flat movement (no arrow)."""
        block = TreemapBlock(
            symbol="MSFT",
            weight=0.04,
            price_change=0.0,
            contribution=0.0,
            direction="flat"
        )
        
        label = block.get_label()
        
        assert label == "MSFT 0.00%"
        assert "⬆" not in label
        assert "⬇" not in label
    
    def test_get_label_negative_uses_absolute_value(self):
        """Test that label shows absolute value of price change."""
        block = TreemapBlock(
            symbol="TEST",
            weight=0.02,
            price_change=-7.89,
            contribution=0.1578,
            direction="down"
        )
        
        label = block.get_label()
        
        # Should show 7.89%, not -7.89%
        assert "7.89%" in label
        assert "-" not in label
    
    def test_get_label_formatting_precision(self):
        """Test that label formats percentage to 2 decimal places."""
        block = TreemapBlock(
            symbol="TEST",
            weight=0.01,
            price_change=1.23456789,
            contribution=0.0123456789,
            direction="up"
        )
        
        label = block.get_label()
        
        assert "1.23%" in label  # Should be rounded to 2 decimal places

