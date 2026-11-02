"""Main application entry point and orchestration."""

import sys
import logging
import os
from typing import Dict

from etf_treemap.cli import parse_arguments
from etf_treemap.holdings import HoldingsFetcher, HoldingsFormatError
from etf_treemap.prices import PriceFetcher
from etf_treemap.calculator import PerformanceCalculator
from etf_treemap.visualizer import TreemapVisualizer

logger = logging.getLogger(__name__)


def main() -> int:
    """Main application entry point that orchestrates the ETF treemap pipeline.
    
    Executes the complete workflow:
    1. Parse command-line arguments (ETF symbol, lookback period, holdings file)
    2. Load holdings from the user-provided holdings file
    3. Fetch price data for all holdings
    4. Calculate performance contributions
    5. Generate treemap visualization
    6. Save PNG file with standardized naming
    
    The function handles all errors gracefully with descriptive messages and
    appropriate exit codes.
    
    Returns:
        int: Exit code - 0 for success, non-zero for errors:
            - 1: General errors (data fetching, visualization)
            - 130: User cancelled operation (Ctrl+C)
    
    Examples:
        Command line usage:
        
        $ python -m etf_treemap.main UFO 1d --csv UFO-holdings.csv
        INFO: Parsing command-line arguments...
        INFO: ETF Symbol: UFO, Lookback Period: 1d
        INFO: Holdings file: UFO-holdings.csv
        ...
        ✓ Success! Treemap visualization saved to: /path/to/UFO-1d-treemap.png
        
        $ python -m etf_treemap.main SPY 3m --csv SPY-holdings.csv
        ...
        ✓ Success! Treemap visualization saved to: /path/to/SPY-3m-treemap.png
    """
    # Configure logging here (not at import) so importing the module has no side effects
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    try:
        # Step 1: Parse CLI arguments
        logger.info("Parsing command-line arguments...")
        etf_symbol, lookback_period, csv_file = parse_arguments()
        logger.info(f"ETF Symbol: {etf_symbol}, Lookback Period: {lookback_period}")
        logger.info(f"Holdings file: {csv_file}")

        # Step 2: Load holdings from the user-provided file
        fetcher = HoldingsFetcher()
        try:
            holdings = fetcher.get_holdings(etf_symbol, csv_file=csv_file)
            logger.info(f"Loaded {len(holdings)} holdings")
        except FileNotFoundError as e:
            print("ERROR: Holdings file not found")
            print(f"Details: {e}")
            print("Suggestion: Download the holdings file from the ETF issuer and pass its path with --csv")
            return 1
        except HoldingsFormatError as e:
            print("ERROR: Unsupported or empty holdings file")
            print(f"Details: {e}")
            return 1
        except OSError as e:
            print("ERROR: Could not read holdings file")
            print(f"Details: {e}")
            print("Suggestion: Check the file path and permissions")
            return 1

        if not holdings:
            print(f"ERROR: No holdings data available for {etf_symbol}")
            print("Details: The holdings list is empty")
            print("Suggestion: The ETF may not have any holdings or data is unavailable")
            return 1
        
        # Step 3: Fetch price data for all holdings
        logger.info(f"Fetching price data for {len(holdings)} holdings...")
        price_fetcher = PriceFetcher(lookback_period)
        price_changes: Dict[str, float] = {}
        
        for holding in holdings:
            price_change = price_fetcher.get_price_change(holding.symbol, company_name=holding.name)
            if price_change is not None:
                price_changes[holding.symbol] = price_change
            else:
                logger.warning(f"Could not retrieve price data for {holding.symbol}, excluding from visualization")
        
        logger.info(f"Successfully retrieved price data for {len(price_changes)} holdings")
        
        if not price_changes:
            print("ERROR: No valid price data available")
            print("Details: Could not retrieve price data for any holdings")
            print("Suggestion: The holdings may have invalid symbols or price data is unavailable")
            return 1
        
        # Step 4: Calculate performance contributions
        logger.info("Calculating performance contributions...")
        calculator = PerformanceCalculator()
        blocks = calculator.prepare_treemap_data(holdings, price_changes)
        logger.info(f"Prepared {len(blocks)} blocks for visualization")
        
        if not blocks:
            print("ERROR: No valid data for visualization")
            print("Details: No blocks could be prepared from the holdings and price data")
            print("Suggestion: Check that holdings have valid price data")
            return 1
        
        # Step 5: Generate treemap visualization
        logger.info("Generating treemap visualization...")
        date_range = price_fetcher.date_range
        visualizer = TreemapVisualizer(etf_symbol, date_range)
        
        # Step 6: Save PNG file with correct filename pattern
        output_filename = f"{etf_symbol}-{lookback_period}-treemap.png"
        output_path = os.path.join(os.getcwd(), output_filename)
        
        try:
            visualizer.generate_treemap(blocks, output_path)
            logger.info("Treemap saved successfully")
        except ValueError as e:
            print("ERROR: Could not generate treemap")
            print(f"Details: {e}")
            print("Suggestion: Check that there is valid data to visualize")
            return 1
        except PermissionError as e:
            print("ERROR: Could not save file")
            print(f"Details: {e}")
            print("Suggestion: Check file permissions in the current directory")
            return 1
        except OSError as e:
            logger.exception("Could not write treemap to %s", output_path)
            print("ERROR: Could not save file")
            print(f"Details: {e}")
            print("Suggestion: Check that the output path is writable and the disk is not full")
            return 1
        except (RuntimeError, ArithmeticError, LookupError, TypeError) as e:
            logger.exception("Treemap rendering failed")
            print("ERROR: Visualization error")
            print(f"Details: {type(e).__name__}: {e}")
            print("Suggestion: Check that matplotlib and squarify are properly installed; the traceback is in the log above")
            return 1
        
        # Step 7: Display confirmation message with file path
        print(f"\n✓ Success! Treemap visualization saved to: {output_path}")
        
        # Return success exit code
        return 0
        
    except KeyboardInterrupt:
        print("\n\nERROR: Operation cancelled by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        print("ERROR: Unexpected error occurred")
        print(f"Details: {e}")
        print("Suggestion: Please report this issue with the full error message")
        logger.exception("Unexpected error in main()")
        return 1


if __name__ == "__main__":
    sys.exit(main())
