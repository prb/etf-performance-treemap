"""Unit tests for price data module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd

from etf_treemap.prices import PriceFetcher


class TestPriceFetcher:
    """Test cases for PriceFetcher class."""
    
    def test_init(self):
        """Test PriceFetcher initialization."""
        fetcher = PriceFetcher("1d")
        assert fetcher.lookback_period == "1d"
        
        fetcher = PriceFetcher("3m")
        assert fetcher.lookback_period == "3m"
    
    @patch('etf_treemap.prices.yf.Ticker')
    def test_get_price_change_success(self, mock_ticker_class):
        """Test successful price change calculation."""
        # Create mock price data
        mock_hist = pd.DataFrame({
            'Close': [100.0, 110.0]
        })
        
        mock_ticker = Mock()
        mock_ticker.history.return_value = mock_hist
        mock_ticker_class.return_value = mock_ticker
        
        fetcher = PriceFetcher("5d")
        price_change = fetcher.get_price_change("AAPL")
        
        # Expected: ((110 - 100) / 100) * 100 = 10.0%
        assert price_change == 10.0
    
    @patch('etf_treemap.prices.yf.Ticker')
    def test_get_price_change_negative(self, mock_ticker_class):
        """Test price change calculation with negative change."""
        # Create mock price data
        mock_hist = pd.DataFrame({
            'Close': [100.0, 90.0]
        })
        
        mock_ticker = Mock()
        mock_ticker.history.return_value = mock_hist
        mock_ticker_class.return_value = mock_ticker
        
        fetcher = PriceFetcher("5d")
        price_change = fetcher.get_price_change("AAPL")
        
        # Expected: ((90 - 100) / 100) * 100 = -10.0%
        assert price_change == -10.0
    
    @patch('etf_treemap.prices.yf.Ticker')
    def test_get_price_change_empty_data(self, mock_ticker_class):
        """Test handling of empty price data."""
        # Create empty DataFrame
        mock_hist = pd.DataFrame()
        
        mock_ticker = Mock()
        mock_ticker.history.return_value = mock_hist
        mock_ticker_class.return_value = mock_ticker
        
        fetcher = PriceFetcher("5d")
        price_change = fetcher.get_price_change("INVALID")
        
        # Should return None for missing data
        assert price_change is None
    
    @patch('etf_treemap.prices.yf.Ticker')
    def test_get_price_change_insufficient_data(self, mock_ticker_class):
        """Test handling of insufficient price data."""
        # Create DataFrame with only one data point
        mock_hist = pd.DataFrame({
            'Close': [100.0]
        })
        
        mock_ticker = Mock()
        mock_ticker.history.return_value = mock_hist
        mock_ticker_class.return_value = mock_ticker
        
        fetcher = PriceFetcher("5d")
        price_change = fetcher.get_price_change("AAPL")
        
        # Should return None for insufficient data
        assert price_change is None
    
    @patch('etf_treemap.prices.yf.Ticker')
    def test_get_price_change_zero_start_price(self, mock_ticker_class):
        """Test handling of zero start price."""
        # Create mock price data with zero start price
        mock_hist = pd.DataFrame({
            'Close': [0.0, 110.0]
        })
        
        mock_ticker = Mock()
        mock_ticker.history.return_value = mock_hist
        mock_ticker_class.return_value = mock_ticker
        
        fetcher = PriceFetcher("5d")
        price_change = fetcher.get_price_change("AAPL")
        
        # Should return None to avoid division by zero
        assert price_change is None
    
    @patch('etf_treemap.prices.yf.Ticker')
    def test_get_price_change_api_error(self, mock_ticker_class):
        """Test handling of yfinance API errors."""
        mock_ticker = Mock()
        mock_ticker.history.side_effect = Exception("API Error")
        mock_ticker_class.return_value = mock_ticker
        
        fetcher = PriceFetcher("5d")
        price_change = fetcher.get_price_change("AAPL")
        
        # Should return None and log warning
        assert price_change is None
