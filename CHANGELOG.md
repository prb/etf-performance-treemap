# Changelog

All notable changes to the ETF Holdings Performance Treemap project are documented here.

## [Unreleased]
### Quality pass (findings 7, 10, 11)
- **Fixed (symbol mapper, finding 7):** The company-name heuristic matches legal forms as whole trailing words (case-sensitive, optional dots such as `N.V.`, `S.A.`, `S.p.A.`) instead of `endswith`. Names like `NASA` or `Kebab` are no longer treated as French or Swedish. Names that really end in `AB`, `NV`, `SA` or `SpA` still map as before.
- **Fixed (symbol mapper):** `290A` (Synspective Inc.) is a Tokyo code, as in `example-holdings`; it now sits under the Japanese overrides rather than the Korean comment. The mapping (`290A.T`) is unchanged.
- **Tests (finding 10):** Replaced all placeholder tests. Added an offline end-to-end test (example QQQM CSV with mocked yfinance produces a PNG), Hypothesis properties for the calculator, lookback and holdings parsing, visualizer labels/titles/colours, symbol mapper, and a calculator-to-PNG render property, plus unit tests for the mapper. Coverage is 96% overall and `symbol_mapper.py` is 100% (was about 70%).
- **Changed (finding 11):** Dev tools (`pytest`, `hypothesis`, `pytest-cov`) moved from the `dev` optional extra to a uv `[dependency-groups] dev` group. Use `uv sync` (dev is installed by default; `--no-dev` skips it) instead of `uv sync --extra dev`.
- **Changed:** pytest no longer writes `htmlcov/` on every run. Terminal coverage stays; run `uv run pytest --cov-report=html` for the HTML report.
- **Dependencies:** `tzdata` is now a direct dependency because `zoneinfo` needs it on Windows. Added a comment in `prices.py` that holiday handling is derived from yfinance data.
### Robustness pass
- **Fixed (logging):** `main.py` no longer calls `logging.basicConfig` at import; it is configured inside `main()`.
- **Fixed (date range):** `PriceFetcher` computes the date range once at construction and exposes it as the public `date_range` property. The price fetch and the chart title now use the same range. The private `_calculate_date_range()` is replaced by the module function `compute_date_range()`. Ranges are US/Eastern-aware.
- **Changed (1d):** The `1d` lookback now measures the change from the previous session's close to the latest price (last 1-minute bar while the market is open, last daily close otherwise). Before, it measured first-to-last 1-minute bar (intraday move only, ignoring the overnight gap) when open, and the last two daily closes when closed. Displayed `1d` numbers during market hours will differ from earlier runs. If the previous close is unavailable, it falls back to the first bar of the day.
- **Fixed (market hours):** Market-open detection uses `America/New_York` (09:30 inclusive to 16:00 exclusive, weekdays) instead of local time. Holidays are detected from the data (no bars dated today during market hours means use daily closes) rather than a hard-coded calendar.
- **Fixed (headless):** The visualizer uses matplotlib's object-oriented `Figure` with an explicit Agg canvas, not `pyplot`, so it works without a display or `MPLBACKEND`.
- **Fixed (errors):** The broad `except Exception` around chart generation is replaced by specific handlers (`OSError` for save failures; `RuntimeError`, `ArithmeticError`, `LookupError`, `TypeError` for rendering). Both log the traceback with `logger.exception`. Other errors reach the top-level handler, which also logs the traceback.
- **Tests:** Added `tests/unit/test_robustness.py` (Hypothesis properties for the date range, market clock and closed-market 1d change; mocked yfinance for the 1d paths; headless render in a clean subprocess) and updated existing price, main and logging tests.
### Housekeeping
- **Docs:** Rewrote `.kiro/specs/etf-holdings-treemap/tasks.md` for the bring-your-own-holdings-file design. Obsolete authentication, scraping and download tasks are removed, completed tasks are marked, and the open property and integration tests are listed.
- **Removed:** `.kiro/settings/mcp.json` (Playwright MCP entry for the abandoned scraping).
- **.gitignore:** Replaced `*.png` / `!example-*.png` with `/*.png` so only root-level PNGs are ignored. `*.secret` stays ignored.
- **Samples:** Moved the generated `*-treemap.png` files into `sample-treemaps/` and added a Sample output section to the README.
- **License:** Copyright holder is now Multifarious, LLC (LICENSE, README, `pyproject.toml` authors).

### Removed old scraper leftovers; holdings file is now required
- **Intent:** The tool no longer fetches holdings from the web. You download the holdings file from the ETF issuer and pass it with `--csv` (alias `--holdings`). Prices still come from yfinance.
- **Breaking:** `--csv` is now required. Running without it exits with a usage error. Existing command lines that already used `--csv` are unchanged.
- **Removed:** `etf_treemap/issuer_mappings.py`, the automatic issuer download (`_download_csv`), `ETFNotFoundError` and `IssuerNotSupportedError`.
- **Dependencies:** Removed unused `playwright`, `cloudscraper`, `beautifulsoup4` and the now unused direct `requests` dependency.
- **Added:** Holdings format detection finds the header row by symbol and weight columns and now also reads Invesco monthly files (`Company`, `% TNA`). An unrecognised or empty file raises `HoldingsFormatError` (a `ValueError`) listing the supported formats; a missing file raises `FileNotFoundError` instead of `ConnectionError`.
- **Added:** ETF symbol validation in the CLI (letters, digits, `.` and `-`, up to 15 characters) so the symbol is safe in the output file name.
- **Docs:** README, `concept.md` and the `.kiro` requirements and design now describe the bring-your-own-file intent.

### Dependency update and code review
- **Dependencies:** Upgraded all runtime and dev dependencies to the latest releases allowed by the 3 day cooldown (for example yfinance 1.1.0 to 1.7.0, matplotlib 3.10.8 to 3.11.2, pandas 3.0.0 to 3.1.0, playwright 1.57.0 to 1.64.1, pytest 9.0.2 to 9.2.0). Lower bounds in `pyproject.toml` now match the tested versions.
- **uv:** Added `[tool.uv] exclude-newer = "P3D"`.
- **License:** Added MIT `LICENSE` and `license = "MIT"` in `pyproject.toml`.
- **README:** Rewritten for the current code (uv install and usage, `--csv`, configuration, development). Removed stale ETF Database login instructions.
- **.gitignore:** Now excludes `*.secret` and `.agents/`.
- **Fixed:** Debug `print` output in `visualizer.py` now goes through `logger.debug`.
- **Fixed:** `prices.py` now returns `None` for NaN/infinite prices instead of passing NaN to the calculator.
- **Fixed:** `issuer_mappings.py` type hints allow `None` (VanEck); `holdings.py` imports moved to module level and an unused `StringIO` removed; added missing return annotations; removed `f` prefixes from constant strings in `main.py`.

### Fixed

#### Weight Parsing Bug (Critical)
- **Issue:** Holdings with portfolio weights less than 1% were incorrectly parsed
- **Impact:** Percentages like "0.85%" were parsed as 0.85 instead of 0.0085, causing massive distortion in treemap visualizations
- **Root Cause:** The CSV parser was reading percentage strings (e.g., "0.85%") and converting them to floats without dividing by 100
- **Fix:** Updated `etf_treemap/holdings.py` to properly parse percentage strings by removing the '%' character and dividing by 100
- **Affected Files:** `etf_treemap/holdings.py`
- **Test Coverage:** Added property-based tests in `tests/unit/test_voog_proportions.py` to verify correct weight parsing
- **Example:** VOOG ETF holdings now display correctly with small holdings (< 1%) appearing proportionally smaller

#### Hierarchical Layout Proportionality
- **Issue:** The Gains and Losses sections in the hierarchical treemap used fixed padding, not proportional sizing
- **Impact:** Section sizes didn't accurately reflect the relative magnitude of gains vs. losses
- **Root Cause:** The `_create_hierarchical_layout()` method in `visualizer.py` used a fixed padding value (0.02) between sections
- **Fix:** Changed padding calculation to be proportional to the total contribution values
  - Gains section now sized by: `gains_total / (gains_total + losses_total + neutral_total)`
  - Losses section sized by: `losses_total / (gains_total + losses_total + neutral_total)`
  - Padding between sections is now proportional rather than fixed
- **Affected Files:** `etf_treemap/visualizer.py`
- **Benefit:** Users can now immediately see the relative balance between winning and losing positions by comparing section sizes

### Added

#### Hierarchical Visualization Layout
- **Feature:** Implemented hierarchical treemap layout separating gains, losses, and neutral holdings
- **Benefits:**
  - Immediate visual understanding of whether gains or losses dominate
  - Clear separation of positive and negative contributors
  - Proportional section sizing reflects relative magnitude
- **Implementation:** Modified `visualizer.py` to create three sections with proportional sizing
- **Documentation:** Updated `concept.md` and `README.md` to document the hierarchical layout

#### Direct Issuer Data Fetching
- **Feature:** Added ability to fetch holdings data directly from ETF issuer websites
- **Benefits:**
  - Complete holdings data (not just top 10)
  - No authentication required for many issuers
  - Faster and more reliable than web scraping
- **Implementation:** Added `issuer_mappings.py` with URL patterns for supported issuers
- **Supported Issuers:** Configurable in `etf_treemap/issuer_mappings.py`

#### Comprehensive Logging
- **Feature:** Added structured logging throughout the application
- **Benefits:**
  - Better debugging and troubleshooting
  - Clear progress indicators for users
  - Detailed error messages with suggestions
- **Implementation:** Logging added to all major modules (cli, auth, holdings, prices, calculator, visualizer)

### Improved

#### Test Coverage
- **Added:** Property-based tests using Hypothesis for weight parsing validation
- **Added:** Unit tests for hierarchical layout proportionality
- **Coverage:** Increased overall test coverage to >90%

#### Documentation
- **Updated:** `README.md` with hierarchical visualization documentation
- **Updated:** `concept.md` with detailed explanation of hierarchical layout
- **Added:** Known Issues section documenting bug fixes
- **Added:** This CHANGELOG.md file

### Removed

#### Debug and Temporary Files
Cleaned up development artifacts:
- `BUG_ROOT_CAUSE.md` - Bug analysis documentation
- `VOOG_BUG_ANALYSIS.md` - Detailed bug investigation notes
- `VOOG_FIX_SUMMARY.md` - Bug fix summary
- `debug_voog.py` - Debug script for VOOG ETF
- `debug_voog_treemap.png` - Debug visualization output
- `debug_comparison.txt` - Debug comparison data
- `verify_voog_fix.py` - Verification script
- `check_weights.py` - Weight checking utility
- `test_etfcom_refactored.py` - Temporary test file
- `test_issuer_direct.py` - Temporary test file
- `test_issuer_holdings.py` - Temporary test file
- `test_parsing.py` - Temporary test file
- `ETFCOM_REFACTORING.md` - Refactoring notes
- `ISSUER_DIRECT_IMPLEMENTATION.md` - Implementation notes
- `LOGGING_IMPLEMENTATION.md` - Implementation notes
- `DOCSTRING_SUMMARY.md` - Documentation notes

## Version History

### Initial Release
- Basic treemap visualization functionality
- ETF Database integration for holdings data
- Yahoo Finance integration for price data
- Command-line interface
- PNG export functionality
