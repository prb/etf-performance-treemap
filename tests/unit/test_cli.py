"""Unit tests for CLI module."""

import os
import pytest
from unittest.mock import patch
import re

from hypothesis import given, strategies as st

from etf_treemap.cli import validate_lookback_period, parse_lookback_period, parse_arguments, validate_etf_symbol


class TestValidateLookbackPeriod:
    """Test cases for lookback period validation."""
    
    def test_valid_days(self):
        """Test valid day periods."""
        assert validate_lookback_period("1d") is True
        assert validate_lookback_period("7d") is True
        assert validate_lookback_period("30d") is True
        assert validate_lookback_period("365d") is True
    
    def test_valid_weeks(self):
        """Test valid week periods."""
        assert validate_lookback_period("1w") is True
        assert validate_lookback_period("4w") is True
        assert validate_lookback_period("52w") is True
    
    def test_valid_months(self):
        """Test valid month periods."""
        assert validate_lookback_period("1m") is True
        assert validate_lookback_period("3m") is True
        assert validate_lookback_period("12m") is True
    
    def test_valid_years(self):
        """Test valid year periods."""
        assert validate_lookback_period("1y") is True
        assert validate_lookback_period("5y") is True
        assert validate_lookback_period("10y") is True
    
    def test_invalid_zero(self):
        """Test that zero is invalid (must be positive)."""
        assert validate_lookback_period("0d") is False
        assert validate_lookback_period("0w") is False
        assert validate_lookback_period("0m") is False
        assert validate_lookback_period("0y") is False
    
    def test_invalid_negative(self):
        """Test that negative numbers are invalid."""
        assert validate_lookback_period("-1d") is False
        assert validate_lookback_period("-5m") is False
    
    def test_invalid_missing_unit(self):
        """Test that numbers without units are invalid."""
        assert validate_lookback_period("1") is False
        assert validate_lookback_period("30") is False
    
    def test_invalid_unit(self):
        """Test that invalid units are rejected."""
        assert validate_lookback_period("1h") is False  # hours not supported
        assert validate_lookback_period("1s") is False  # seconds not supported
        assert validate_lookback_period("1x") is False  # invalid unit
    
    def test_invalid_multiple_units(self):
        """Test that multiple units are invalid."""
        assert validate_lookback_period("1d2w") is False
        assert validate_lookback_period("1dm") is False
    
    def test_invalid_decimal(self):
        """Test that decimal numbers are invalid."""
        assert validate_lookback_period("1.5d") is False
        assert validate_lookback_period("2.0m") is False
    
    def test_invalid_empty_string(self):
        """Test that empty string is invalid."""
        assert validate_lookback_period("") is False
    
    def test_invalid_none(self):
        """Test that None is invalid."""
        assert validate_lookback_period(None) is False
    
    def test_invalid_spaces(self):
        """Test that periods with spaces are invalid."""
        assert validate_lookback_period("1 d") is False
        assert validate_lookback_period(" 1d") is False
        assert validate_lookback_period("1d ") is False
    
    def test_invalid_leading_zeros(self):
        """Test that leading zeros are invalid (not standard format)."""
        # Leading zeros should be rejected as they're not standard format
        assert validate_lookback_period("01d") is False
        assert validate_lookback_period("007d") is False


class TestParseLookbackPeriod:
    """Test cases for lookback period parsing."""
    
    def test_parse_single_digit_days(self):
        """Test parsing single digit day periods."""
        assert parse_lookback_period("1d") == (1, "d")
        assert parse_lookback_period("7d") == (7, "d")
    
    def test_parse_multi_digit_days(self):
        """Test parsing multi-digit day periods."""
        assert parse_lookback_period("30d") == (30, "d")
        assert parse_lookback_period("365d") == (365, "d")
    
    def test_parse_weeks(self):
        """Test parsing week periods."""
        assert parse_lookback_period("1w") == (1, "w")
        assert parse_lookback_period("4w") == (4, "w")
        assert parse_lookback_period("52w") == (52, "w")
    
    def test_parse_months(self):
        """Test parsing month periods."""
        assert parse_lookback_period("1m") == (1, "m")
        assert parse_lookback_period("3m") == (3, "m")
        assert parse_lookback_period("12m") == (12, "m")
    
    def test_parse_years(self):
        """Test parsing year periods."""
        assert parse_lookback_period("1y") == (1, "y")
        assert parse_lookback_period("5y") == (5, "y")
        assert parse_lookback_period("10y") == (10, "y")
    
    def test_parse_large_numbers(self):
        """Test parsing large numbers."""
        assert parse_lookback_period("999d") == (999, "d")
        assert parse_lookback_period("100y") == (100, "y")
    
    def test_parse_invalid_format_raises_error(self):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError, match="Invalid lookback period format"):
            parse_lookback_period("0d")
        
        with pytest.raises(ValueError, match="Invalid lookback period format"):
            parse_lookback_period("-1d")
        
        with pytest.raises(ValueError, match="Invalid lookback period format"):
            parse_lookback_period("1")
        
        with pytest.raises(ValueError, match="Invalid lookback period format"):
            parse_lookback_period("1h")
        
        with pytest.raises(ValueError, match="Invalid lookback period format"):
            parse_lookback_period("")
    
    def test_parse_invalid_none_raises_error(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError, match="Invalid lookback period format"):
            parse_lookback_period(None)
    
    def test_parse_invalid_leading_zeros_raises_error(self):
        """Test that periods with leading zeros raise ValueError."""
        with pytest.raises(ValueError, match="Invalid lookback period format"):
            parse_lookback_period("01d")
        
        with pytest.raises(ValueError, match="Invalid lookback period format"):
            parse_lookback_period("007d")
        
        with pytest.raises(ValueError, match="Invalid lookback period format"):
            parse_lookback_period("030m")


class TestCLI:
    """Test cases for command-line interface functions."""

    def test_parse_arguments_basic(self):
        """Test parsing with required arguments only."""
        test_args = ['prog', 'UFO', '1d', '--csv', 'tests/fixtures/UFO-holdings.csv']
        with patch('sys.argv', test_args):
            etf_symbol, lookback_period, csv_file = parse_arguments()
            assert etf_symbol == 'UFO'
            assert lookback_period == '1d'
            assert csv_file == 'tests/fixtures/UFO-holdings.csv'

    def test_parse_arguments_with_csv(self):
        """Test parsing with --csv flag."""
        test_args = ['prog', 'QQQM', '1w', '--csv', 'tests/fixtures/UFO-holdings.csv']
        with patch('sys.argv', test_args):
            etf_symbol, lookback_period, csv_file = parse_arguments()
            assert etf_symbol == 'QQQM'
            assert lookback_period == '1w'
            assert csv_file == 'tests/fixtures/UFO-holdings.csv'

    def test_parse_arguments_missing_etf_symbol(self):
        """Test that missing ETF symbol displays usage and exits."""
        test_args = ['prog']
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code != 0

    def test_parse_arguments_missing_lookback_period(self):
        """Test that missing lookback period displays usage and exits."""
        test_args = ['prog', 'UFO']
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code != 0

    def test_parse_arguments_invalid_lookback_period(self):
        """Test that invalid lookback period displays error and exits."""
        test_args = ['prog', 'UFO', 'invalid', '--csv', 'tests/fixtures/UFO-holdings.csv']
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code != 0

    def test_parse_arguments_zero_lookback_period(self):
        """Test that zero lookback period displays error and exits."""
        test_args = ['prog', 'UFO', '0d', '--csv', 'tests/fixtures/UFO-holdings.csv']
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code != 0

    def test_parse_arguments_negative_lookback_period(self):
        """Test that negative lookback period displays error and exits."""
        test_args = ['prog', 'UFO', '-1d', '--csv', 'tests/fixtures/UFO-holdings.csv']
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code != 0

    def test_parse_arguments_various_valid_periods(self):
        """Test parsing with various valid lookback periods."""
        valid_periods = ['1d', '7d', '30d', '1w', '4w', '1m', '3m', '12m', '1y', '5y']
        for period in valid_periods:
            test_args = ['prog', 'TEST', period, '--csv', 'tests/fixtures/UFO-holdings.csv']
            with patch('sys.argv', test_args):
                etf_symbol, lookback_period, csv_file = parse_arguments()
                assert lookback_period == period

    def test_parse_arguments_help_flag(self):
        """Test that --help flag displays usage and exits."""
        test_args = ['prog', '--help']
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 0

    def test_parse_arguments_requires_holdings_file(self, capsys):
        """The holdings file is mandatory; the tool does not download holdings."""
        with patch('sys.argv', ['prog', 'UFO', '1d']):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
        assert exc_info.value.code != 0
        assert '--csv' in capsys.readouterr().err

    def test_parse_arguments_holdings_alias(self):
        """--holdings is an alias for --csv."""
        test_args = ['prog', 'UFO', '1d', '--holdings', 'tests/fixtures/UFO-holdings.csv']
        with patch('sys.argv', test_args):
            _, _, csv_file = parse_arguments()
        assert csv_file == 'tests/fixtures/UFO-holdings.csv'

    def test_parse_arguments_missing_file(self, capsys):
        """A nonexistent holdings file gives a helpful error."""
        with patch('sys.argv', ['prog', 'UFO', '1d', '--csv', 'does-not-exist.csv']):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
        assert exc_info.value.code != 0
        assert 'Holdings file not found' in capsys.readouterr().err

    def test_parse_arguments_invalid_symbol(self, capsys):
        """Symbols with path characters are rejected."""
        with patch('sys.argv', ['prog', '../evil', '1d', '--csv', 'tests/fixtures/UFO-holdings.csv']):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
        assert exc_info.value.code != 0
        assert 'Invalid ETF symbol' in capsys.readouterr().err


class TestValidateEtfSymbol:
    """Tests for ETF symbol validation."""

    @pytest.mark.parametrize('symbol', ['UFO', 'qqqm', 'BRK.B', 'BF-B', 'A1', 'X' * 15])
    def test_valid_symbols(self, symbol):
        assert validate_etf_symbol(symbol)

    @pytest.mark.parametrize('symbol', ['', '../x', 'a/b', 'a\\b', '.hidden', '-x', 'A B', 'X' * 16, 'UFO\n', 'U$'])
    def test_invalid_symbols(self, symbol):
        assert not validate_etf_symbol(symbol)

    @given(st.text(alphabet=st.characters(blacklist_characters='.-'), min_size=1).filter(
        lambda t: not re.fullmatch(r'[A-Za-z0-9]+', t)))
    def test_symbols_with_other_characters_rejected(self, symbol):
        assert not validate_etf_symbol(symbol)

    @given(st.from_regex(r'[A-Za-z0-9][A-Za-z0-9.\-]{0,14}', fullmatch=True))
    def test_pattern_symbols_accepted(self, symbol):
        assert validate_etf_symbol(symbol)
