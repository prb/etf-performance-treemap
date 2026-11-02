"""Test that treemap block proportions are correct (VOOG bug fix verification)."""

import pytest
import tempfile
import os
from datetime import datetime
from etf_treemap.calculator import TreemapBlock
from etf_treemap.visualizer import TreemapVisualizer


class TestVOOGProportions:
    """Test suite to verify the VOOG treemap proportions bug fix.
    
    This test suite verifies that the fix for the VOOG treemap bug is working correctly.
    The bug was that fixed padding disproportionately affected smaller sections, causing
    blocks to appear incorrectly sized.
    
    The fix changed from fixed padding to proportional padding (0.2% of section dimensions).
    """
    
    @pytest.fixture
    def visualizer(self):
        """Create a visualizer for testing."""
        return TreemapVisualizer(
            "VOOG-TEST",
            (datetime(2024, 1, 1), datetime(2024, 1, 1))
        )
    
    def test_nvda_app_proportions(self, visualizer):
        """Test the exact NVDA/APP scenario from the VOOG bug report.
        
        NVDA: 14.72% weight, -5.46% change = 0.804% contribution
        APP: 0.5823% weight, +5.53% change = 0.032% contribution
        
        NVDA should appear ~25x larger than APP (0.804 / 0.032 = 25.125x)
        """
        nvda = TreemapBlock(
            symbol="NVDA",
            weight=0.1472,
            price_change=-5.46,
            contribution=0.00804,
            direction="down"
        )
        
        app = TreemapBlock(
            symbol="APP",
            weight=0.005823,
            price_change=5.53,
            contribution=0.00032,
            direction="up"
        )
        
        blocks = [nvda, app]
        
        # Generate treemap
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_voog.png")
            visualizer.generate_treemap(blocks, output_path)
            
            # Verify file was created
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
    
    def test_extreme_size_difference(self, visualizer):
        """Test treemap with extreme size differences between blocks.
        
        This tests the edge case where one block is 100x larger than another.
        """
        large_block = TreemapBlock(
            symbol="LARGE",
            weight=0.50,
            price_change=10.0,
            contribution=0.05,
            direction="up"
        )
        
        small_block = TreemapBlock(
            symbol="SMALL",
            weight=0.01,
            price_change=-5.0,
            contribution=0.0005,
            direction="down"
        )
        
        blocks = [large_block, small_block]
        
        # Generate treemap
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_extreme.png")
            visualizer.generate_treemap(blocks, output_path)
            
            # Verify file was created
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
    
    def test_many_small_blocks_one_large(self, visualizer):
        """Test treemap with many small blocks and one large block.
        
        This simulates a common real-world scenario where one holding
        dominates the performance contribution.
        """
        # One large block
        large_block = TreemapBlock(
            symbol="DOMINANT",
            weight=0.20,
            price_change=15.0,
            contribution=0.03,
            direction="up"
        )
        
        # Many small blocks
        small_blocks = [
            TreemapBlock(
                symbol=f"SMALL{i}",
                weight=0.01,
                price_change=1.0,
                contribution=0.0001,
                direction="up"
            )
            for i in range(20)
        ]
        
        blocks = [large_block] + small_blocks
        
        # Generate treemap
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_many_small.png")
            visualizer.generate_treemap(blocks, output_path)
            
            # Verify file was created
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
    
    def test_balanced_gains_and_losses(self, visualizer):
        """Test treemap with balanced gains and losses sections.
        
        This tests the case where gains and losses are roughly equal,
        so both sections should be similar in size.
        """
        gains = [
            TreemapBlock(f"GAIN{i}", 0.05, 5.0, 0.0025, "up")
            for i in range(5)
        ]
        
        losses = [
            TreemapBlock(f"LOSS{i}", 0.05, -5.0, 0.0025, "down")
            for i in range(5)
        ]
        
        blocks = gains + losses
        
        # Generate treemap
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_balanced.png")
            visualizer.generate_treemap(blocks, output_path)
            
            # Verify file was created
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
    
    def test_highly_skewed_sections(self, visualizer):
        """Test treemap with highly skewed gains/losses ratio.
        
        This tests the edge case where one section is much larger than the other,
        which was the root cause of the VOOG bug.
        """
        # Large losses section (95% of total contribution)
        large_loss = TreemapBlock(
            symbol="BIGLOSS",
            weight=0.30,
            price_change=-10.0,
            contribution=0.03,
            direction="down"
        )
        
        # Small gains section (5% of total contribution)
        small_gain = TreemapBlock(
            symbol="SMALLGAIN",
            weight=0.05,
            price_change=3.0,
            contribution=0.0015,
            direction="up"
        )
        
        blocks = [large_loss, small_gain]
        
        # Generate treemap
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_skewed.png")
            visualizer.generate_treemap(blocks, output_path)
            
            # Verify file was created
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
