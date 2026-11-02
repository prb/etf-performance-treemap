# Requirements Document

## Introduction

This document specifies the requirements for an ETF Holdings Performance Treemap Visualization Tool. The system is a Python command-line application that loads ETF holdings from a file the user provides, retrieves price performance information, and generates a treemap visualization showing the performance contribution of each holding to the overall ETF.

## Glossary

- **CLI_Tool**: The command-line interface application that orchestrates data fetching and visualization
- **ETF_Symbol**: A ticker symbol representing an Exchange-Traded Fund (e.g., "UFO", "SPY")
- **Lookback_Period**: A time duration specification in the format of a positive integer followed by 'd' (days), 'w' (weeks), 'm' (months), or 'y' (years)
- **Holdings_File**: A CSV file, obtained by the user (for example downloaded from the ETF issuer), containing ETF constituent securities and their portfolio weights, in one of the supported formats
- **Holdings_Data**: The constituent securities and weights parsed from the Holdings_File
- **Supported_Format**: A CSV layout with a header row containing a symbol column (Symbol, Ticker or StockTicker) and a weight column (Weighting, Weightings, Weight, % of Net Assets or % TNA), optionally preceded by metadata lines
- **Price_Data**: Historical or intraday price information for securities
- **Treemap**: A visualization where nested rectangles represent hierarchical data with size and color encoding
- **Weight**: The percentage allocation of a holding within an ETF portfolio
- **Performance_Contribution**: The product of a holding's weight and its price change percentage
- **Trading_Day**: A day when financial markets are open for trading

## Requirements

### Requirement 1: Command-Line Interface

**User Story:** As a user, I want to invoke the tool from the command line with an ETF symbol, a lookback period and a holdings file, so that I can quickly generate performance visualizations.

#### Acceptance Criteria

1. WHEN the user invokes the CLI_Tool with an ETF_Symbol, a Lookback_Period and a Holdings_File path, THE CLI_Tool SHALL accept all three arguments
2. WHEN the user provides a Lookback_Period, THE CLI_Tool SHALL validate it matches the pattern: positive integer followed by 'd', 'w', 'm', or 'y'
3. IF the Lookback_Period format is invalid, THEN THE CLI_Tool SHALL display an error message and exit with a non-zero status code
4. WHEN the user invokes the CLI_Tool without required arguments (including the Holdings_File path), THE CLI_Tool SHALL display usage information
5. WHEN the ETF_Symbol contains characters other than letters, digits, '.' or '-', or is longer than 15 characters, THE CLI_Tool SHALL display an error message and exit with a non-zero status code

### Requirement 2: Lookback Period Parsing

**User Story:** As a user, I want to specify flexible time periods, so that I can analyze performance over different timeframes.

#### Acceptance Criteria

1. WHEN a Lookback_Period is "1d", THE CLI_Tool SHALL interpret it as the most recent Trading_Day
2. WHEN the market is currently open and Lookback_Period is "1d", THE CLI_Tool SHALL compute intraday performance
3. WHEN a Lookback_Period contains 'd', THE CLI_Tool SHALL interpret the integer as calendar days
4. WHEN a Lookback_Period contains 'w', THE CLI_Tool SHALL interpret the integer as weeks
5. WHEN a Lookback_Period contains 'm', THE CLI_Tool SHALL interpret the integer as months
6. WHEN a Lookback_Period contains 'y', THE CLI_Tool SHALL interpret the integer as years

### Requirement 3: Holdings File Input

**User Story:** As a user, I want to supply the ETF holdings file myself, so that the tool works with whatever holdings data I have obtained from the issuer.

#### Acceptance Criteria

1. THE CLI_Tool SHALL require the path to a Holdings_File and SHALL NOT download holdings data from the web
2. IF the Holdings_File does not exist or cannot be read, THEN THE CLI_Tool SHALL display an error message and exit with a non-zero status code
3. IF the Holdings_File is not in a Supported_Format or contains no holdings rows, THEN THE CLI_Tool SHALL display an error message listing the Supported_Formats and exit with a non-zero status code
4. THE CLI_Tool SHALL keep accepting the Holdings_File path through the `--csv` option (alias `--holdings`)

### Requirement 4: Holdings Data Parsing

**User Story:** As a user, I want the tool to read holdings from the common issuer file layouts, so that I do not have to reformat files.

#### Acceptance Criteria

1. WHEN a Holdings_File is provided, THE CLI_Tool SHALL skip any metadata lines before the header row and detect the header row by its symbol and weight columns
2. THE CLI_Tool SHALL support at least the ETF Database export layout, the Invesco monthly holdings layout and the fund-administrator layout (StockTicker, SecurityName, Weightings)
3. WHEN a weight is written with a trailing '%', THE CLI_Tool SHALL interpret it as a percentage and convert it to a decimal fraction
4. IF a data row is malformed, THEN THE CLI_Tool SHALL log a warning and continue with the remaining rows
5. WHEN the Holdings_File is parsed, THE CLI_Tool SHALL extract symbol, name (when present) and weight for each holding

### Requirement 5: Price Data Retrieval

**User Story:** As a user, I want the tool to fetch accurate price data for all holdings, so that performance calculations are correct.

#### Acceptance Criteria

1. WHEN Holdings_Data is parsed, THE CLI_Tool SHALL extract all holding symbols from the data
2. FOR each holding symbol, THE CLI_Tool SHALL fetch Price_Data using the yfinance library
3. WHEN fetching Price_Data, THE CLI_Tool SHALL request data for the specified Lookback_Period
4. IF Price_Data for a holding is unavailable, THEN THE CLI_Tool SHALL exclude that holding from the visualization and log a warning
5. WHEN Price_Data is retrieved, THE CLI_Tool SHALL calculate the percentage price change for the Lookback_Period

### Requirement 6: Performance Contribution Calculation

**User Story:** As a user, I want each holding's contribution to be accurately calculated, so that the treemap reflects true portfolio impact.

#### Acceptance Criteria

1. FOR each holding, THE CLI_Tool SHALL calculate Performance_Contribution as Weight multiplied by price change percentage
2. WHEN a holding has positive price change, THE CLI_Tool SHALL classify it as "up"
3. WHEN a holding has negative price change, THE CLI_Tool SHALL classify it as "down"
4. WHEN a holding has zero price change, THE CLI_Tool SHALL classify it as "flat"
5. WHEN Performance_Contribution is calculated, THE CLI_Tool SHALL use the absolute value for determining block size

### Requirement 7: Treemap Visualization Generation

**User Story:** As a user, I want a clear treemap visualization, so that I can quickly understand which holdings drove ETF performance.

#### Acceptance Criteria

1. WHEN generating the treemap, THE CLI_Tool SHALL size each block proportionally to the absolute Performance_Contribution
2. WHEN a holding is classified as "up", THE CLI_Tool SHALL color the block green
3. WHEN a holding is classified as "down", THE CLI_Tool SHALL color the block red
4. WHEN a holding is classified as "flat", THE CLI_Tool SHALL color the block grey
5. FOR each block, THE CLI_Tool SHALL display a label with the holding symbol, direction arrow, and percentage change
6. WHEN a holding is "up", THE CLI_Tool SHALL use an up arrow character ("⬆") in the label
7. WHEN a holding is "down", THE CLI_Tool SHALL use a down arrow character ("⬇") in the label
8. WHEN a holding is "flat", THE CLI_Tool SHALL omit the direction arrow from the label
9. WHEN rendering block labels, THE CLI_Tool SHALL use contrasting text color for readability

### Requirement 8: Treemap Title and Metadata

**User Story:** As a user, I want the visualization to show the ETF symbol and date range, so that I can identify what the chart represents.

#### Acceptance Criteria

1. WHEN Lookback_Period is "1d", THE CLI_Tool SHALL format the title as "{ETF_Symbol} Holdings Performance {Date as YYYY-MM-DD}"
2. WHEN Lookback_Period is not "1d", THE CLI_Tool SHALL format the title as "{ETF_Symbol} Holdings Performance {Start Date as YYYY-MM-DD}-{End Date as YYYY-MM-DD}"
3. WHEN generating the title, THE CLI_Tool SHALL calculate the start and end dates based on the Lookback_Period
4. WHEN the treemap is generated, THE CLI_Tool SHALL display the formatted title at the top of the visualization

### Requirement 9: Output File Generation

**User Story:** As a user, I want the visualization saved as a PNG file, so that I can share or archive the results.

#### Acceptance Criteria

1. WHEN the treemap is generated, THE CLI_Tool SHALL save it as a PNG file in the current working directory
2. WHEN saving the PNG file, THE CLI_Tool SHALL name it using the pattern "{ETF_Symbol}-{Lookback_Period}-treemap.png"
3. IF a file with the same name exists, THEN THE CLI_Tool SHALL overwrite it
4. WHEN the file is saved successfully, THE CLI_Tool SHALL display a confirmation message with the file path
5. WHEN the file is saved successfully, THE CLI_Tool SHALL exit with a zero status code

### Requirement 10: Error Handling and Logging

**User Story:** As a user, I want clear error messages when something goes wrong, so that I can troubleshoot issues.

#### Acceptance Criteria

1. IF the Holdings_File is missing, unreadable or in an unsupported format, THEN THE CLI_Tool SHALL display a descriptive error message
2. IF Price_Data cannot be fetched because of network errors, THEN THE CLI_Tool SHALL log a warning for the affected holding
3. IF no holding has valid Price_Data, THEN THE CLI_Tool SHALL display an error message
4. IF Price_Data cannot be retrieved for a holding, THEN THE CLI_Tool SHALL log a warning and continue processing other holdings
5. WHEN errors occur, THE CLI_Tool SHALL exit with a non-zero status code
