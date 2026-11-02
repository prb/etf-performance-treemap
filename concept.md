# Purpose
The purpose of this application is to present a treemap visualization of the performance of an ETF based on the performance of its holdings.  The application will be built in Python as a commandline tool that accepts an ETF symbol and a period in the form of a lookback duration, and outputs a treemap as a PNG in the current directory.

## Lookback Durations
Lookback period are specified as a positive integer followed by one of `d` (days), `w` (weeks), `m` (months), or `y` (years).

The period specification `1d` means the most recent trading day, so it is an intraday computation if the market is currently open.

## Data Sources
The tool does not fetch ETF holdings from the web. The user locates the ETF's holdings file (typically downloaded from the issuer's website) in one of the supported CSV formats and provides its path with `--csv` (alias `--holdings`). The option is required.

Supported formats (the parser skips metadata lines, finds the header row and reads the symbol, name and weight columns):
- ETF Database style export: `Holding,Symbol,Weighting`, weights as percentages
- Invesco monthly holdings: `Ticker`, `Company`, `% TNA`
- Fund-administrator export: `StockTicker`, `SecurityName`, `Weightings`
- Any CSV with a symbol column (`Symbol`, `Ticker`, `StockTicker`) and a weight column (`Weighting`, `Weightings`, `Weight`, `% of Net Assets`, `% TNA`)

If the file is missing, unreadable, empty or in an unrecognised format, the tool reports a clear error that lists the supported formats and exits with a non-zero status. Samples are in `example-holdings/`.

Stock price data for the holdings of the ETF will be obtained via the [`yfinance`](https://ranaroussi.github.io/yfinance/#) library.

## Visualization
The tool will present a treemap visualization of the holdings of the ETF, as follows:

- The overall plot is labeled as "{SYMBOL} Holdings Performance {Period Start Date as YYYY-MM-DD}-{Period End Date as YYYY-MM-DD}" unless the period is `1d`, in which case it is labeled as "{SYMBOL} Holdings Performance {Period Start Date as YYYY-MM-DD}"
- The block is labeled with the abbreviation for the symbol, e.g., "PL" for "Planet Labs" and the current percent price change for the day with either an up arrow character ("⬆") for increase or a down arrow character ("⬇") for decrease, e.g., "PL ⬆1.75%" if Planet Labs is up 1.75% in the trading period under consideration.
- The size of the block for a given holding is weighted by the total change in value for the period.  The total change in value is obtained from the weight of the holding (e.g., `5.9589%` for `PL` within `UFO` holfings) by the change in price for the holding over the period.
- The color for a block is green if the holding is up within the current period and red if it is down.  If it is neither up nor down, the block is grey.  The block labels will be in contrasting color, e.g., white.

### Hierarchical Layout (Implemented)

The visualization uses a hierarchical layout that separates gains from losses, providing clearer visual insight into portfolio performance:

**Layout Structure:**
- The treemap is divided into two main sections: **Gains** (left) and **Losses** (right)
- Each section is proportionally sized based on the total absolute contribution of holdings within it
- Within each section, individual holdings are sized by their absolute performance contribution
- A neutral holdings section appears if any holdings have zero price change

**Key Features:**
- **Proportional padding**: Section sizes accurately reflect the relative magnitude of gains vs. losses
- **Clear separation**: Immediate visual understanding of whether gains or losses dominate
- **Accurate sizing**: Holdings within each section are sized by their contribution magnitude
- **Color coding**: Green for gains, red for losses, grey for neutral

**Example:**
For an ETF with 60% of contribution from gains and 40% from losses:
- The Gains section occupies ~60% of the treemap area
- The Losses section occupies ~40% of the treemap area
- Individual holdings within each section are sized by their specific contribution

This hierarchical approach proved superior to the original flat treemap concept by:
1. Making it immediately clear whether the ETF is net positive or negative
2. Showing the relative balance between winning and losing positions
3. Maintaining accurate proportional representation at both the section and holding levels