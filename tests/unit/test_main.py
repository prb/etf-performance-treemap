"""Unit tests for main application orchestration."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

from etf_treemap.main import main
from etf_treemap.holdings import HoldingsFormatError, Holding
from etf_treemap.calculator import TreemapBlock


class TestMain:
    """Tests for main application orchestration."""
    
    @patch('etf_treemap.main.parse_arguments')
    @patch('etf_treemap.main.HoldingsFetcher')
    @patch('etf_treemap.main.PriceFetcher')
    @patch('etf_treemap.main.PerformanceCalculator')
    @patch('etf_treemap.main.TreemapVisualizer')
    @patch('os.getcwd')
    def test_successful_execution(self, mock_getcwd, mock_visualizer_class, 
                                  mock_calculator_class, mock_price_fetcher_class,
                                  mock_holdings_fetcher_class, mock_parse_args):
        """Test successful execution of the complete pipeline."""
        # Setup mocks
        mock_parse_args.return_value = ('UFO', '1d', 'holdings.csv')
        mock_getcwd.return_value = '/tmp'
        
        # Mock holdings fetcher
        mock_holdings_fetcher = Mock()
        mock_holdings = [
            Holding(symbol='AAPL', name='Apple Inc.', weight=0.1),
            Holding(symbol='GOOGL', name='Alphabet Inc.', weight=0.2)
        ]
        mock_holdings_fetcher.get_holdings.return_value = mock_holdings
        mock_holdings_fetcher_class.return_value = mock_holdings_fetcher
        
        # Mock price fetcher
        mock_price_fetcher = Mock()
        mock_price_fetcher.get_price_change.side_effect = [5.0, -3.0]
        mock_price_fetcher.date_range = (Mock(), Mock())
        mock_price_fetcher_class.return_value = mock_price_fetcher
        
        # Mock calculator
        mock_calculator = Mock()
        mock_blocks = [
            TreemapBlock(symbol='AAPL', weight=0.1, price_change=5.0, 
                        contribution=0.5, direction='up'),
            TreemapBlock(symbol='GOOGL', weight=0.2, price_change=-3.0,
                        contribution=0.6, direction='down')
        ]
        mock_calculator.prepare_treemap_data.return_value = mock_blocks
        mock_calculator_class.return_value = mock_calculator
        
        # Mock visualizer
        mock_visualizer = Mock()
        mock_visualizer_class.return_value = mock_visualizer
        
        # Execute main
        exit_code = main()
        
        # Verify exit code
        assert exit_code == 0
        
        # Verify pipeline steps were called
        mock_parse_args.assert_called_once()
        mock_holdings_fetcher_class.assert_called_once()
        mock_holdings_fetcher.get_holdings.assert_called_once_with('UFO', csv_file='holdings.csv')
        assert mock_price_fetcher.get_price_change.call_count == 2
        mock_calculator.prepare_treemap_data.assert_called_once()
        mock_visualizer.generate_treemap.assert_called_once()
    
    @patch('etf_treemap.main.parse_arguments')
    @patch('etf_treemap.main.HoldingsFetcher')
    def test_holdings_file_not_found(self, mock_holdings_fetcher_class, mock_parse_args, capsys):
        """Test handling of missing holdings file errors."""
        mock_parse_args.return_value = ('INVALID', '1d', 'holdings.csv')
        
        mock_holdings_fetcher = Mock()
        mock_holdings_fetcher.get_holdings.side_effect = FileNotFoundError("Holdings file not found: 'x.csv'")
        mock_holdings_fetcher_class.return_value = mock_holdings_fetcher
        
        exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "ERROR: Holdings file not found" in captured.out
    
    @patch('etf_treemap.main.parse_arguments')
    @patch('etf_treemap.main.HoldingsFetcher')
    @patch('etf_treemap.main.PriceFetcher')
    def test_no_price_data_error(self, mock_price_fetcher_class,
                                 mock_holdings_fetcher_class,
                                 mock_parse_args, capsys):
        """Test handling when no price data is available."""
        mock_parse_args.return_value = ('UFO', '1d', 'holdings.csv')
        
        mock_holdings_fetcher = Mock()
        mock_holdings = [Holding(symbol='AAPL', name='Apple Inc.', weight=0.1)]
        mock_holdings_fetcher.get_holdings.return_value = mock_holdings
        mock_holdings_fetcher_class.return_value = mock_holdings_fetcher
        
        mock_price_fetcher = Mock()
        mock_price_fetcher.get_price_change.return_value = None  # No price data
        mock_price_fetcher_class.return_value = mock_price_fetcher
        
        exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "ERROR: No valid price data available" in captured.out
    
    @patch('etf_treemap.main.parse_arguments')
    @patch('etf_treemap.main.HoldingsFetcher')
    def test_empty_holdings_error(self, mock_holdings_fetcher_class,
                                  mock_parse_args, capsys):
        """Test handling when holdings list is empty."""
        mock_parse_args.return_value = ('UFO', '1d', 'holdings.csv')
        
        mock_holdings_fetcher = Mock()
        mock_holdings_fetcher.get_holdings.return_value = []  # Empty list
        mock_holdings_fetcher_class.return_value = mock_holdings_fetcher
        
        exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "ERROR: No holdings data available" in captured.out
    
    @patch('etf_treemap.main.parse_arguments')
    @patch('etf_treemap.main.HoldingsFetcher')
    @patch('etf_treemap.main.PriceFetcher')
    @patch('etf_treemap.main.PerformanceCalculator')
    @patch('etf_treemap.main.TreemapVisualizer')
    @patch('os.getcwd')
    def test_file_permission_error(self, mock_getcwd, mock_visualizer_class,
                                   mock_calculator_class, mock_price_fetcher_class,
                                   mock_holdings_fetcher_class,
                                   mock_parse_args, capsys):
        """Test handling of file permission errors."""
        mock_parse_args.return_value = ('UFO', '1d', 'holdings.csv')
        mock_getcwd.return_value = '/tmp'
        
        mock_holdings_fetcher = Mock()
        mock_holdings = [Holding(symbol='AAPL', name='Apple Inc.', weight=0.1)]
        mock_holdings_fetcher.get_holdings.return_value = mock_holdings
        mock_holdings_fetcher_class.return_value = mock_holdings_fetcher
        
        mock_price_fetcher = Mock()
        mock_price_fetcher.get_price_change.return_value = 5.0
        mock_price_fetcher.date_range = (Mock(), Mock())
        mock_price_fetcher_class.return_value = mock_price_fetcher
        
        mock_calculator = Mock()
        mock_blocks = [TreemapBlock(symbol='AAPL', weight=0.1, price_change=5.0,
                                    contribution=0.5, direction='up')]
        mock_calculator.prepare_treemap_data.return_value = mock_blocks
        mock_calculator_class.return_value = mock_calculator
        
        mock_visualizer = Mock()
        mock_visualizer.generate_treemap.side_effect = PermissionError("Permission denied")
        mock_visualizer_class.return_value = mock_visualizer
        
        exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "ERROR: Could not save file" in captured.out
        assert "Permission denied" in captured.out
    
    @patch('etf_treemap.main.parse_arguments')
    @patch('etf_treemap.main.HoldingsFetcher')
    @patch('etf_treemap.main.PriceFetcher')
    @patch('etf_treemap.main.PerformanceCalculator')
    @patch('etf_treemap.main.TreemapVisualizer')
    @patch('os.getcwd')
    def test_output_filename_pattern(self, mock_getcwd, mock_visualizer_class,
                                     mock_calculator_class, mock_price_fetcher_class,
                                     mock_holdings_fetcher_class,
                                     mock_parse_args):
        """Test that output filename follows the correct pattern."""
        mock_parse_args.return_value = ('SPY', '3m', 'holdings.csv')
        mock_getcwd.return_value = '/tmp'
        
        mock_holdings_fetcher = Mock()
        mock_holdings = [Holding(symbol='AAPL', name='Apple Inc.', weight=0.1)]
        mock_holdings_fetcher.get_holdings.return_value = mock_holdings
        mock_holdings_fetcher_class.return_value = mock_holdings_fetcher
        
        mock_price_fetcher = Mock()
        mock_price_fetcher.get_price_change.return_value = 5.0
        mock_price_fetcher.date_range = (Mock(), Mock())
        mock_price_fetcher_class.return_value = mock_price_fetcher
        
        mock_calculator = Mock()
        mock_blocks = [TreemapBlock(symbol='AAPL', weight=0.1, price_change=5.0,
                                    contribution=0.5, direction='up')]
        mock_calculator.prepare_treemap_data.return_value = mock_blocks
        mock_calculator_class.return_value = mock_calculator
        
        mock_visualizer = Mock()
        mock_visualizer_class.return_value = mock_visualizer
        
        exit_code = main()
        
        # Verify the filename pattern
        expected_path = '/tmp/SPY-3m-treemap.png'
        mock_visualizer.generate_treemap.assert_called_once()
        actual_path = mock_visualizer.generate_treemap.call_args[0][1]
        assert actual_path == expected_path

    @patch('etf_treemap.main.parse_arguments')
    @patch('etf_treemap.main.HoldingsFetcher')
    def test_unsupported_format_error(self, mock_holdings_fetcher_class, mock_parse_args, capsys):
        """An unrecognised holdings file reports the error and exits 1."""
        mock_parse_args.return_value = ('UFO', '1d', 'holdings.csv')
        mock_holdings_fetcher = Mock()
        mock_holdings_fetcher.get_holdings.side_effect = HoldingsFormatError("Unrecognised holdings format")
        mock_holdings_fetcher_class.return_value = mock_holdings_fetcher

        assert main() == 1
        captured = capsys.readouterr()
        assert "ERROR: Unsupported or empty holdings file" in captured.out
        assert "Unrecognised holdings format" in captured.out
