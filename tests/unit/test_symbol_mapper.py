"""Unit tests for symbol mapper module."""

import pytest
from etf_treemap.symbol_mapper import normalize_symbol, get_display_symbol


class TestNormalizeSymbol:
    """Test cases for symbol normalization."""
    
    def test_normalize_canadian_symbol(self):
        """Test normalization of Canadian symbols."""
        assert normalize_symbol("MDA CN") == "MDA.TO"
        assert normalize_symbol("SHOP CN") == "SHOP.TO"
    
    def test_normalize_french_symbol(self):
        """Test normalization of French symbols."""
        assert normalize_symbol("AIR FP") == "AIR.PA"
        assert normalize_symbol("SESG FP") == "SESG.PA"
    
    def test_normalize_japanese_symbol(self):
        """Test normalization of Japanese symbols."""
        assert normalize_symbol("9412 JP") == "9412.T"
        assert normalize_symbol("4825 JP") == "4825.T"
    
    def test_normalize_italian_symbol(self):
        """Test normalization of Italian symbols."""
        assert normalize_symbol("AVIO IM") == "AVIO.MI"
        assert normalize_symbol("LDO IM") == "LDO.MI"
        assert normalize_symbol("SCC IT") == "SCC.MI"
    
    def test_normalize_korean_symbol(self):
        """Test normalization of Korean symbols."""
        assert normalize_symbol("189300 KS") == "189300.KS"
        assert normalize_symbol("474170 KS") == "474170.KS"
    
    def test_normalize_swedish_symbol(self):
        """Test normalization of Swedish symbols."""
        assert normalize_symbol("OVZON SS") == "OVZON.ST"
        assert normalize_symbol("GOMX SS") == "GOMX.ST"
    
    def test_normalize_dutch_symbol(self):
        """Test normalization of Dutch symbols."""
        assert normalize_symbol("TOM2 NA") == "TOM2.AS"
    
    def test_normalize_us_symbol_unchanged(self):
        """Test that US symbols without country codes remain unchanged."""
        assert normalize_symbol("AAPL") == "AAPL"
        assert normalize_symbol("MSFT") == "MSFT"
        assert normalize_symbol("TSLA") == "TSLA"
    
    def test_normalize_already_normalized_symbol(self):
        """Test that already normalized symbols remain unchanged."""
        assert normalize_symbol("MDA.TO") == "MDA.TO"
        assert normalize_symbol("AIR.PA") == "AIR.PA"
    
    def test_normalize_unknown_country_code(self):
        """Test that unknown country codes return original symbol."""
        assert normalize_symbol("XYZ ZZ") == "XYZ ZZ"
    
    def test_normalize_empty_string(self):
        """Test normalization of empty string."""
        assert normalize_symbol("") == ""
    
    def test_normalize_whitespace_handling(self):
        """Test that extra whitespace is handled correctly."""
        assert normalize_symbol("  MDA CN  ") == "MDA.TO"
        assert normalize_symbol("MDA  CN") == "MDA.TO"  # Multiple spaces are normalized


class TestGetDisplaySymbol:
    """Test cases for display symbol extraction."""
    
    def test_display_symbol_with_suffix(self):
        """Test extracting display symbol from Yahoo Finance format."""
        assert get_display_symbol("MDA.TO") == "MDA"
        assert get_display_symbol("AIR.PA") == "AIR"
        assert get_display_symbol("9412.T") == "9412"
    
    def test_display_symbol_without_suffix(self):
        """Test display symbol for symbols without suffixes."""
        assert get_display_symbol("AAPL") == "AAPL"
        assert get_display_symbol("MSFT") == "MSFT"
    
    def test_display_symbol_empty_string(self):
        """Test display symbol for empty string."""
        assert get_display_symbol("") == ""


class TestCompanyNameHeuristic:
    """Whole-word legal-suffix matching on company names."""

    @pytest.mark.parametrize("name,expected", [
        ("GomSpace Group AB", ".ST"),
        ("Ovzon AB", ".ST"),
        ("TomTom NV", ".AS"),
        ("TomTom N.V.", ".AS"),
        ("Leonardo SpA", ".MI"),
        ("Leonardo S.p.A.", ".MI"),
        ("Thales SA", ".PA"),
        ("Thales S.A.", ".PA"),
        ("  Eutelsat Communications SA  ", ".PA"),
    ])
    def test_legal_suffix_matches(self, name: str, expected: str) -> None:
        assert normalize_symbol("XYZ", name) == "XYZ" + expected

    @pytest.mark.parametrize("name", [
        "NASA", "Kebab", "Nova", "Visa", "Panasonic SAB", "ABB", "ARCA", "Hospitalab",
        "Canal+ SAS", "Foo.SA", "Apple Inc.", "",
    ])
    def test_names_merely_ending_in_letters_do_not_match(self, name: str) -> None:
        assert normalize_symbol("XYZ", name) == "XYZ"

    def test_lowercase_suffix_does_not_match(self) -> None:
        assert normalize_symbol("XYZ", "Something ab") == "XYZ"
        assert normalize_symbol("XYZ", "Something sa") == "XYZ"

    def test_override_wins_over_heuristic(self) -> None:
        assert normalize_symbol("SESG", "SES SA") == "SESG.PA"


class TestOverrides:
    def test_290a_is_tokyo_synspective(self) -> None:
        """290A is Synspective Inc. (Tokyo); example-holdings lists it without a country."""
        assert normalize_symbol("290A") == "290A.T"

    def test_korean_overrides(self) -> None:
        assert normalize_symbol("189300") == "189300.KS"
        assert normalize_symbol("474170") == "474170.KQ"

    def test_unknown_country_code_warns_and_returns_original(self, caplog: pytest.LogCaptureFixture) -> None:
        assert normalize_symbol("FOO ZZ") == "FOO ZZ"
        assert "Unknown country/exchange code 'ZZ'" in caplog.text

    def test_share_class_with_long_suffix_is_unchanged(self) -> None:
        assert normalize_symbol("ABC.XY") == "ABC.XY"

    def test_get_display_symbol(self) -> None:
        assert get_display_symbol("MDA.TO") == "MDA"
        assert get_display_symbol("AAPL") == "AAPL"
