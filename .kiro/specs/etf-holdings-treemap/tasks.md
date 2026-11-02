# Implementation Plan: ETF Holdings Performance Treemap

## Overview

The tool takes a user-supplied holdings file (`--csv`), fetches price changes with yfinance and renders a treemap PNG. It does not log in to, scrape or download from any website. Items marked `[x]` are implemented and covered by unit tests. Items marked `[ ]` are still open.

## Tasks

- [x] 1. Project structure and dependencies
  - Package `etf_treemap` (cli, holdings, symbol_mapper, prices, calculator, visualizer, main), `uv`-managed dependencies, tests under `tests/{unit,property,integration,fixtures}`
  - _Requirements: All_
- [x] 2. CLI and lookback parsing (`cli.py`)
  - `validate_lookback_period`, `parse_lookback_period`, `validate_etf_symbol`, `parse_arguments` with required `--csv` (alias `--holdings`)
  - Unit tests in `tests/unit/test_cli.py`
  - _Requirements: 1.1-1.5, 2.3-2.6, 3.1, 3.4_
- [x] 3. Holdings file parsing (`holdings.py`)
  - `Holding` dataclass, `HoldingsFetcher.get_holdings(symbol, csv_file)`, header detection by symbol and weight columns, ETF Database, Invesco monthly and fund-administrator layouts, percent weights, malformed-row warnings
  - `HoldingsFormatError` for unsupported or empty files; `FileNotFoundError` for missing files
  - Unit tests in `tests/unit/test_holdings.py`
  - _Requirements: 3.1-3.4, 4.1-4.5_
- [x] 4. Symbol normalization (`symbol_mapper.py`)
  - Issuer symbols mapped to Yahoo Finance symbols, display symbols
  - _Requirements: 5.1, 5.2_
- [x] 5. Price retrieval (`prices.py`)
  - `PriceFetcher` with date range, market-open detection for `1d`, retries, `None` for missing or non-finite prices
  - _Requirements: 2.1, 2.2, 5.1-5.5_
- [x] 6. Performance calculator (`calculator.py`)
  - `TreemapBlock`, `calculate_contribution`, `classify_direction`, `prepare_treemap_data`
  - _Requirements: 6.1-6.5_
- [x] 7. Treemap visualizer (`visualizer.py`)
  - Gain and loss sections, colors, labels with arrows, title formats, text contrast
  - _Requirements: 7.1-7.9, 8.1-8.3_
- [x] 8. Orchestration, exit codes and logging (`main.py`)
  - Pipeline wiring, `{SYMBOL}-{PERIOD}-treemap.png` output, confirmation message, exit codes (0, 1, 130), ERROR/Details/Suggestion messages
  - Unit tests in `test_main.py` and `test_logging.py`
  - _Requirements: 9.1-9.5, 10.1-10.5_
- [x] 9. Documentation
  - README (usage, supported formats, troubleshooting), CHANGELOG, LICENSE, docstrings
- [ ] 10. Property-based tests (Hypothesis)
  - Files in `tests/property/` currently hold placeholders only
  - [ ] 10.1 Lookback validation and parsing (Properties 1, 2)
  - [ ] 10.2 Holdings file required, symbol validation, unsupported format rejection (Properties 4, 5, 6)
  - [ ] 10.3 CSV parsing and symbol extraction (Properties 7, 8)
  - [ ] 10.4 Contribution, direction and absolute block size (Properties 11, 12, 13)
  - [ ] 10.5 Price date range and price change (Properties 9, 10)
  - [ ] 10.6 Block proportionality, colors, labels, arrows, text contrast (Properties 14-18)
  - [ ] 10.7 Title format and date range (Properties 19-21)
  - [ ] 10.8 PNG creation, filename pattern, confirmation message, exit codes (Properties 22-25)
- [ ] 11. End-to-end integration test
  - `tests/integration/test_end_to_end.py` is a placeholder; replace it with a run on `tests/fixtures/UFO-holdings.csv` with yfinance mocked, asserting the PNG is created
  - _Requirements: All_
- [ ] 12. Coverage check
  - Confirm coverage target (>90%) once tasks 10 and 11 are done

## Notes

- Property tests validate the properties in `design.md`; unit tests cover examples and error cases.
- External services (yfinance) are mocked in tests.
