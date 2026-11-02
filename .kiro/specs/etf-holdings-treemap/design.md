# Design Document: ETF Holdings Performance Treemap

## Overview

The ETF Holdings Performance Treemap is a Python command-line application that visualizes the performance contribution of individual holdings within an ETF. The user supplies a holdings file (downloaded from the ETF issuer) in one of the supported CSV formats; the tool parses it, retrieves price data via yfinance, calculates performance contributions, and generates a treemap visualization saved as a PNG file.

The application follows a pipeline architecture:
1. Parse command-line arguments (ETF symbol, lookback period, holdings file path)
2. Load and parse the holdings file
3. Fetch price data for all holdings
4. Calculate performance contributions
5. Generate and save treemap visualization

## Architecture

The system is organized into the following modules:

```
etf_treemap/
├── cli.py              # Command-line interface and argument parsing
├── holdings.py         # Holdings file format detection and parsing
├── prices.py           # Price data fetching via yfinance
├── calculator.py       # Performance contribution calculations
├── visualizer.py       # Treemap generation
└── main.py             # Application entry point
```

### Module Responsibilities

- **cli.py**: Parses command-line arguments, validates the ETF symbol, lookback period format and holdings file path
- **holdings.py**: Reads the user-provided holdings file, detects the header row and columns, parses holdings
- **prices.py**: Fetches historical/intraday price data using yfinance, calculates price changes
- **calculator.py**: Computes performance contributions, classifies holdings as up/down/flat
- **visualizer.py**: Generates treemap using matplotlib/squarify, applies colors and labels
- **main.py**: Orchestrates the pipeline, handles errors, manages output

## Components and Interfaces

### CLI Module

**Functions:**
- `parse_arguments() -> Tuple[str, str, str]`: Parses command-line arguments and returns (etf_symbol, lookback_period, holdings_file). The holdings file is passed with the required `--csv` option (alias `--holdings`).
- `validate_etf_symbol(symbol: str) -> bool`: Accepts 1-15 letters, digits, '.' and '-' (starting with a letter or digit)
- `validate_lookback_period(period: str) -> bool`: Validates lookback period format (positive integer + d/w/m/y)
- `parse_lookback_period(period: str) -> Tuple[int, str]`: Extracts numeric value and unit from period string

**Error Handling:**
- Raises `ValueError` for invalid lookback period format
- Exits via `SystemExit` for missing required arguments, an invalid ETF symbol, or a holdings file that does not exist or is not readable

### Holdings Module

**Class: HoldingsFetcher**

```python
class HoldingsFetcher:
    def get_holdings(self, etf_symbol: str, csv_file: str) -> List[Holding]:
        """Load and parse holdings from the user-provided file"""

    def _parse_csv(self, csv_content: str, etf_symbol: str, source: str = "<string>") -> List[Holding]:
        """Detect the header row and parse CSV content into Holding objects"""
```

The header row is the first row that contains both a symbol column (`StockTicker`, `Ticker` or `Symbol`) and a weight column (`Weightings`, `Weighting`, `Weight`, `% of Net Assets`, `% TNA`, ...). Rows before it are treated as metadata. The name column (`SecurityName`, `Name`, `Holding`, `Company`, ...) is optional. Weights with a trailing '%' are divided by 100.

**Error Handling:**
- Raises `FileNotFoundError` if the file does not exist; `OSError` subclasses (for example `PermissionError`) if it cannot be read
- Raises `HoldingsFormatError` (a `ValueError`) if the file is not UTF-8 text, no header row is recognised, or no data rows yield a holding. The message lists the supported formats.
- Logs warnings for malformed CSV rows

### Price Data Module

**Class: PriceFetcher**

```python
class PriceFetcher:
    def __init__(self, lookback_period: str):
        """Initialize with lookback period"""
        
    def get_price_change(self, symbol: str) -> Optional[float]:
        """Fetch price data and calculate percentage change for symbol"""
        
    def _calculate_date_range(self) -> Tuple[datetime, datetime]:
        """Calculate start and end dates from lookback period"""
        
    def _is_market_open(self) -> bool:
        """Check if market is currently open (for 1d intraday)"""
```

**Error Handling:**
- Returns `None` if price data unavailable for a symbol
- Logs warnings for failed price fetches
- Handles yfinance API errors gracefully

### Calculator Module

**Class: PerformanceCalculator**

```python
class PerformanceCalculator:
    def calculate_contribution(self, holding: Holding, price_change: float) -> float:
        """Calculate performance contribution (weight * price_change)"""
        
    def classify_direction(self, price_change: float) -> str:
        """Classify as 'up', 'down', or 'flat'"""
        
    def prepare_treemap_data(self, holdings: List[Holding], 
                            price_changes: Dict[str, float]) -> List[TreemapBlock]:
        """Prepare all data needed for treemap visualization"""
```

### Visualizer Module

**Class: TreemapVisualizer**

```python
class TreemapVisualizer:
    def __init__(self, etf_symbol: str, date_range: Tuple[datetime, datetime]):
        """Initialize with ETF symbol and date range for title"""
        
    def generate_treemap(self, blocks: List[TreemapBlock], output_path: str):
        """Generate treemap visualization and save as PNG"""
        
    def _format_title(self, is_single_day: bool) -> str:
        """Format title based on date range"""
        
    def _format_label(self, block: TreemapBlock) -> str:
        """Format block label with symbol, arrow, and percentage"""
        
    def _get_color(self, direction: str) -> str:
        """Map direction to color (green/red/grey)"""
        
    def _get_text_color(self, background_color: str) -> str:
        """Return contrasting text color for readability"""
```

**Dependencies:**
- matplotlib for plotting
- squarify for treemap layout algorithm

## Data Models

### Holding

```python
@dataclass
class Holding:
    symbol: str          # Ticker symbol (e.g., "PL")
    name: str           # Full name (e.g., "Planet Labs")
    weight: float       # Portfolio weight as decimal (e.g., 0.059589 for 5.9589%)
```

### TreemapBlock

```python
@dataclass
class TreemapBlock:
    symbol: str                    # Ticker symbol
    weight: float                  # Portfolio weight
    price_change: float           # Percentage price change
    contribution: float           # Absolute value of (weight * price_change)
    direction: str                # 'up', 'down', or 'flat'
    
    def get_label(self) -> str:
        """Format label with symbol, arrow, and percentage"""
        arrow = "⬆" if self.direction == "up" else "⬇" if self.direction == "down" else ""
        return f"{self.symbol} {arrow}{abs(self.price_change):.2f}%"
```

### Configuration

```python
@dataclass
class Config:
    etf_symbol: str
    lookback_period: str
    holdings_file: str         # Path to user-provided holdings CSV
    output_filename: str       # Generated from symbol and period
```

## Correctness Properties


*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Lookback Period Validation

*For any* input string, the validation function should return true if and only if the string matches the pattern of a positive integer followed by exactly one of 'd', 'w', 'm', or 'y'.

**Validates: Requirements 1.2**

### Property 2: Lookback Period Parsing

*For any* valid lookback period string, parsing should correctly extract the numeric value and time unit, such that re-formatting the parsed values produces an equivalent period specification.

**Validates: Requirements 2.3, 2.4, 2.5, 2.6**

### Property 3: CLI Argument Acceptance

*For any* valid ETF symbol and lookback period, the CLI parser should successfully extract both values without raising an error.

**Validates: Requirements 1.1**

### Property 4: Holdings File Required

*For any* invocation without a holdings file path, or with a path that is not an existing readable file, the CLI should exit with a non-zero status and an error message.

**Validates: Requirements 1.4, 3.1, 3.2**

### Property 5: ETF Symbol Validation

*For any* string, the symbol validator should return true if and only if it consists of 1-15 letters, digits, '.' or '-' and starts with a letter or digit.

**Validates: Requirements 1.5**

### Property 6: Unsupported Format Rejection

*For any* file content with no header row containing both a symbol column and a weight column, parsing should raise `HoldingsFormatError`.

**Validates: Requirements 3.3**

### Property 7: CSV Parsing Completeness

*For any* valid holdings CSV content, parsing should extract all rows containing symbol and weight information, and the number of parsed holdings should equal the number of valid data rows.

**Validates: Requirements 4.1, 4.3, 4.5**

### Property 8: Symbol Extraction Completeness

*For any* list of holdings, extracting symbols should produce a list where the length equals the number of holdings and each symbol appears exactly once.

**Validates: Requirements 5.1**

### Property 9: Price Data Request Date Range

*For any* lookback period, the date range passed to yfinance should span from (current_date - lookback_period) to current_date.

**Validates: Requirements 5.3**

### Property 10: Price Change Calculation

*For any* price data with start price P1 and end price P2, the calculated percentage change should equal ((P2 - P1) / P1) * 100.

**Validates: Requirements 5.5**

### Property 11: Performance Contribution Calculation

*For any* holding with weight W and price change percentage C, the performance contribution should equal W * C.

**Validates: Requirements 6.1**

### Property 12: Direction Classification

*For any* price change value, the classification should return 'up' if the value is positive, 'down' if negative, and 'flat' if zero.

**Validates: Requirements 6.2, 6.3, 6.4**

### Property 13: Block Size Uses Absolute Value

*For any* performance contribution value (positive or negative), the block size calculation should use the absolute value of the contribution.

**Validates: Requirements 6.5**

### Property 14: Block Size Proportionality

*For any* two holdings with contributions C1 and C2, the ratio of their block sizes should equal the ratio of their absolute contributions: size1/size2 = |C1|/|C2|.

**Validates: Requirements 7.1**

### Property 15: Color Mapping

*For any* direction classification, the color mapping should return green for 'up', red for 'down', and grey for 'flat'.

**Validates: Requirements 7.2, 7.3, 7.4**

### Property 16: Label Format Completeness

*For any* treemap block, the label should contain the symbol, the percentage change formatted to 2 decimal places, and a direction arrow (if not flat).

**Validates: Requirements 7.5**

### Property 17: Arrow Selection

*For any* direction classification, the label should include "⬆" for 'up', "⬇" for 'down', and no arrow for 'flat'.

**Validates: Requirements 7.6, 7.7, 7.8**

### Property 18: Text Color Contrast

*For any* background color, the selected text color should provide sufficient contrast for readability (e.g., white text on dark backgrounds, dark text on light backgrounds).

**Validates: Requirements 7.9**

### Property 19: Title Date Range Calculation

*For any* lookback period, the calculated start and end dates should span exactly the specified duration from the current date.

**Validates: Requirements 8.3**

### Property 20: Multi-Day Title Format

*For any* lookback period that is not "1d", the title should include both start and end dates in YYYY-MM-DD format separated by a hyphen.

**Validates: Requirements 8.2**

### Property 21: Title Presence in Visualization

*For any* generated treemap image, the title should appear at the top of the visualization.

**Validates: Requirements 8.4**

### Property 22: PNG File Creation

*For any* successful treemap generation, a PNG file should exist in the current working directory after execution.

**Validates: Requirements 9.1**

### Property 23: Filename Pattern

*For any* ETF symbol and lookback period, the output filename should match the pattern "{symbol}-{period}-treemap.png".

**Validates: Requirements 9.2**

### Property 24: Success Confirmation Message

*For any* successful file save, the output should include a confirmation message containing the full file path.

**Validates: Requirements 9.4**

### Property 25: Exit Code Correctness

*For any* execution, the exit code should be 0 if and only if the treemap was successfully generated and saved; otherwise it should be non-zero.

**Validates: Requirements 1.3, 3.2, 3.3, 9.5, 10.5**

## Error Handling

The application implements a layered error handling strategy:

### Input Validation Errors
- Invalid lookback period format → Display format requirements and exit
- Missing required arguments → Display usage information and exit
- Invalid ETF symbol format → Display error and exit
- Holdings file missing or unreadable → Display error with the path and exit

### Holdings File Errors
- File not found → Display "Holdings file not found" with a suggestion to download the file from the issuer and pass it with `--csv`
- File unreadable (permissions, not UTF-8) → Display the underlying error
- Unsupported or empty format → Display an error listing the supported formats
- CSV rows that cannot be parsed → Log warning, continue with valid rows

### Data Fetching Errors
- Price data unavailable for holding → Log warning, exclude holding from visualization

### Visualization Errors
- No holdings with valid price data → Display error that no valid data available
- File write permission errors → Display error with file path and permission issue
- Matplotlib/rendering errors → Display error with suggestion to check dependencies

### Error Message Format
All error messages follow the pattern:
```
ERROR: [Brief description]
Details: [Specific information]
Suggestion: [How to resolve]
```

### Logging Strategy
- INFO: Successful operations (holdings load, price fetch, file save)
- WARNING: Non-fatal issues (missing price data for individual holdings, malformed CSV rows)
- ERROR: Fatal issues that prevent completion

## Testing Strategy

The testing strategy employs both unit tests and property-based tests to ensure comprehensive coverage.

### Unit Testing

Unit tests focus on:
- **Specific examples**: Testing with known ETF symbols and expected outputs (e.g., UFO ETF with example CSV)
- **Edge cases**: Empty holdings lists, zero price changes, single holding ETFs
- **Error conditions**: Missing holdings file, unsupported format, invalid ETF symbol, missing price data
- **Integration points**: yfinance API calls

Example unit tests:
- Test parsing the example UFO holdings CSV
- Test "1d" lookback period during market hours vs. after hours
- Test each supported holdings format against the files in `example-holdings/`
- Test missing file and unsupported format errors
- Test handling of holdings with missing price data
- Test file overwrite behavior

### Property-Based Testing

Property-based tests validate universal properties across randomized inputs using a Python PBT library (e.g., Hypothesis).

**Configuration:**
- Minimum 100 iterations per property test
- Each test tagged with: `# Feature: etf-holdings-treemap, Property N: [property text]`

**Test Generators:**
- Random valid lookback periods (1-999 with d/w/m/y)
- Random invalid lookback period strings
- Random ETF symbols (valid and invalid ticker format)
- Random holdings data (symbols, weights that sum to ~100%)
- Random price changes (-100% to +1000%)
- Random dates and date ranges

**Property Test Coverage:**
Each correctness property (1-25) will be implemented as a property-based test. Key properties include:
- Lookback period validation and parsing (Properties 1-2)
- Performance contribution calculations (Properties 10-11)
- Direction classification and color mapping (Properties 12, 15)
- Label formatting (Properties 16-17)
- Filename and title formatting (Properties 19-20, 23)
- Exit code correctness (Property 25)

### Test Organization

```
tests/
├── unit/
│   ├── test_cli.py
│   ├── test_holdings.py
│   ├── test_prices.py
│   ├── test_calculator.py
│   └── test_visualizer.py
├── property/
│   ├── test_properties_parsing.py
│   ├── test_properties_calculation.py
│   ├── test_properties_formatting.py
│   └── test_properties_integration.py
├── integration/
│   └── test_end_to_end.py
└── fixtures/
    └── UFO-holdings.csv
```

### Mocking Strategy

- **Holdings files**: Use `example-holdings/` samples and temporary files; no network access is involved
- **yfinance calls**: Mock price data responses to avoid external API dependencies
- **File system**: Use temporary directories for output file tests
- **Date/time**: Mock current date for consistent date range calculations

### Continuous Integration

- Run all unit tests on every commit
- Run property tests (with reduced iterations for speed) on every commit
- Run full property test suite (100+ iterations) on pull requests
- Generate coverage reports (target: >90% coverage)
