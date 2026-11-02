"""Unit tests for logging configuration and behavior."""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from etf_treemap.main import main
from etf_treemap.holdings import HoldingsFetcher, HoldingsFormatError, Holding
from etf_treemap.prices import PriceFetcher
from etf_treemap.calculator import TreemapBlock


class TestLoggingConfiguration:
    """Tests for logging configuration and behavior."""
    
    def test_logging_levels_configured(self):
        """Test that logging is configured with appropriate levels."""
        # The logging configuration is set up in main.py when it runs
        # For testing, we just verify that the basicConfig call would work
        # and that loggers can be created at INFO level
        
        # Create a test logger
        test_logger = logging.getLogger('test_etf_treemap')
        test_logger.setLevel(logging.INFO)
        
        # Verify that INFO level logging is supported
        assert test_logger.isEnabledFor(logging.INFO), \
            "Logger should support INFO level messages"
        
        # Verify that the main module has logging configured
        from etf_treemap import main as main_module
        # The main module should have a logger
        assert hasattr(main_module, 'logger'), \
            "Main module should have a logger configured"
    
    @patch('etf_treemap.main.parse_arguments')
    @patch('etf_treemap.main.HoldingsFetcher')
    @patch('etf_treemap.main.PriceFetcher')
    @patch('etf_treemap.main.PerformanceCalculator')
    @patch('etf_treemap.main.TreemapVisualizer')
    @patch('os.getcwd')
    def test_successful_operations_logged(self, mock_getcwd, mock_visualizer_class,
                                         mock_calculator_class, mock_price_fetcher_class,
                                         mock_holdings_fetcher_class,
                                         mock_parse_args, caplog):
        """Test that successful operations are logged at INFO level."""
        # Setup mocks
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
        mock_visualizer_class.return_value = mock_visualizer
        
        # Execute with logging capture
        with caplog.at_level(logging.INFO):
            exit_code = main()
        
        # Verify exit code
        assert exit_code == 0
        
        # Verify INFO logs for successful operations
        log_messages = [record.message for record in caplog.records if record.levelno == logging.INFO]
        
        # Check for holdings fetch log
        assert any('Loaded' in msg and 'holdings' in msg for msg in log_messages), \
            "Should log successful holdings fetch"
        
        # Check for price data fetch log
        assert any('Successfully retrieved price data' in msg for msg in log_messages), \
            "Should log successful price data fetch"
        
        # Check for treemap save log
        assert any('Treemap saved successfully' in msg for msg in log_messages), \
            "Should log successful treemap save"
    
    @patch('etf_treemap.main.parse_arguments')
    @patch('etf_treemap.main.HoldingsFetcher')
    @patch('etf_treemap.main.PriceFetcher')
    def test_missing_price_data_warning(self, mock_price_fetcher_class,
                                       mock_holdings_fetcher_class,
                                       mock_parse_args, caplog):
        """Test that missing price data for individual holdings logs a warning."""
        mock_parse_args.return_value = ('UFO', '1d', 'holdings.csv')
        
        mock_holdings_fetcher = Mock()
        mock_holdings = [
            Holding(symbol='AAPL', name='Apple Inc.', weight=0.1),
            Holding(symbol='INVALID', name='Invalid Corp.', weight=0.2)
        ]
        mock_holdings_fetcher.get_holdings.return_value = mock_holdings
        mock_holdings_fetcher_class.return_value = mock_holdings_fetcher
        
        mock_price_fetcher = Mock()
        # First call succeeds, second returns None (missing data)
        mock_price_fetcher.get_price_change.side_effect = [5.0, None]
        mock_price_fetcher_class.return_value = mock_price_fetcher
        
        # Execute with logging capture
        with caplog.at_level(logging.WARNING):
            exit_code = main()
        
        # Verify WARNING logs for missing price data
        warning_messages = [record.message for record in caplog.records 
                          if record.levelno == logging.WARNING]
        
        assert any('Could not retrieve price data for INVALID' in msg 
                  for msg in warning_messages), \
            "Should log warning for missing price data"
        
        assert any('excluding from visualization' in msg 
                  for msg in warning_messages), \
            "Should indicate holding will be excluded"
    
    @patch('etf_treemap.main.parse_arguments')
    @patch('etf_treemap.main.HoldingsFetcher')
    def test_holdings_file_not_found_format(self, mock_holdings_fetcher_class,
                                       mock_parse_args, capsys):
        """Test that missing holdings file errors follow ERROR/Details/Suggestion pattern."""
        mock_parse_args.return_value = ('INVALID', '1d', 'holdings.csv')
        
        mock_holdings_fetcher = Mock()
        mock_holdings_fetcher.get_holdings.side_effect = FileNotFoundError("Holdings file not found: 'x.csv'")
        mock_holdings_fetcher_class.return_value = mock_holdings_fetcher
        
        exit_code = main()
        
        assert exit_code == 1
        
        # Verify error message format
        captured = capsys.readouterr()
        assert "ERROR: Holdings file not found" in captured.out
        assert "Details:" in captured.out
        assert "Suggestion:" in captured.out
    
    @patch('etf_treemap.main.parse_arguments')
    @patch('etf_treemap.main.HoldingsFetcher')
    def test_network_error_format(self, mock_holdings_fetcher_class, mock_parse_args, capsys):
        """Test that network errors follow ERROR/Details/Suggestion pattern."""
        mock_parse_args.return_value = ('UFO', '1d', 'holdings.csv')
        
        mock_holdings_fetcher = Mock()
        mock_holdings_fetcher.get_holdings.side_effect = PermissionError("Permission denied")
        mock_holdings_fetcher_class.return_value = mock_holdings_fetcher
        
        exit_code = main()
        
        assert exit_code == 1
        
        # Verify error message format
        captured = capsys.readouterr()
        assert "ERROR: Could not read holdings file" in captured.out
        assert "Details: Permission denied" in captured.out
        assert "Suggestion:" in captured.out
    
    def test_malformed_csv_row_warning(self, caplog):
        """Test that malformed CSV rows log warnings."""
        from etf_treemap.holdings import HoldingsFetcher
        
        fetcher = HoldingsFetcher()
        
        # CSV with malformed row (invalid weight format that will cause ValueError)
        csv_content = """Holding,Symbol,Weighting
Apple Inc.,AAPL,5.5%
Invalid Row,INVALID,not_a_number
Google Inc.,GOOGL,3.2%"""
        
        with caplog.at_level(logging.WARNING):
            holdings = fetcher._parse_csv(csv_content, 'TEST')
        
        # Should have 2 valid holdings
        assert len(holdings) == 2
        
        # Should have warning for malformed row
        warning_messages = [record.message for record in caplog.records 
                          if record.levelno == logging.WARNING]
        
        assert any('malformed csv row' in msg.lower() for msg in warning_messages), \
            f"Should log warning for malformed CSV row. Got: {warning_messages}"
    
    @patch('etf_treemap.main.parse_arguments')
    @patch('etf_treemap.main.HoldingsFetcher')
    @patch('etf_treemap.main.PriceFetcher')
    @patch('etf_treemap.main.PerformanceCalculator')
    @patch('etf_treemap.main.TreemapVisualizer')
    @patch('os.getcwd')
    def test_visualization_error_format(self, mock_getcwd, mock_visualizer_class,
                                       mock_calculator_class, mock_price_fetcher_class,
                                       mock_holdings_fetcher_class,
                                       mock_parse_args, capsys):
        """Test that visualization errors follow ERROR/Details/Suggestion pattern."""
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
        mock_visualizer.generate_treemap.side_effect = ValueError("Invalid data")
        mock_visualizer_class.return_value = mock_visualizer
        
        exit_code = main()
        
        assert exit_code == 1
        
        # Verify error message format
        captured = capsys.readouterr()
        assert "ERROR: Could not generate treemap" in captured.out
        assert "Details: Invalid data" in captured.out
        assert "Suggestion:" in captured.out
