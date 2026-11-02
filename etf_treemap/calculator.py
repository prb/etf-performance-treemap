"""Performance contribution calculation module."""

from typing import List, Dict
from dataclasses import dataclass
from etf_treemap.holdings import Holding


@dataclass
class TreemapBlock:
    """Represents a block in the treemap visualization.
    
    Each block corresponds to one holding in the ETF and contains all the
    information needed to render it in the treemap: size (contribution),
    color (direction), and label.
    
    Attributes:
        symbol (str): Ticker symbol of the holding.
        weight (float): Portfolio weight as a decimal.
        price_change (float): Percentage price change over the lookback period.
        contribution (float): Absolute value of (weight * price_change), used for block size.
        direction (str): Direction classification: 'up', 'down', or 'flat'.
    
    Examples:
        >>> block = TreemapBlock(
        ...     symbol="AAPL",
        ...     weight=0.05,
        ...     price_change=2.5,
        ...     contribution=0.125,
        ...     direction="up"
        ... )
        >>> print(block.get_label())
        AAPL ⬆2.50%
        
        >>> block = TreemapBlock(
        ...     symbol="TSLA",
        ...     weight=0.03,
        ...     price_change=-1.8,
        ...     contribution=0.054,
        ...     direction="down"
        ... )
        >>> print(block.get_label())
        TSLA ⬇1.80%
    """
    symbol: str                    # Ticker symbol
    weight: float                  # Portfolio weight
    price_change: float           # Percentage price change
    contribution: float           # Absolute value of (weight * price_change)
    direction: str                # 'up', 'down', or 'flat'
    
    def get_label(self) -> str:
        """Format label with symbol, direction arrow, and percentage.
        
        Creates a human-readable label for the treemap block that includes
        the ticker symbol, an arrow indicating direction (up/down), and the
        absolute percentage change.
        
        Returns:
            str: Formatted label string (e.g., "AAPL ⬆5.23%" or "TSLA ⬇2.10%").
        
        Examples:
            >>> block = TreemapBlock("AAPL", 0.05, 5.23, 0.26, "up")
            >>> block.get_label()
            'AAPL ⬆5.23%'
            
            >>> block = TreemapBlock("TSLA", 0.03, -2.10, 0.063, "down")
            >>> block.get_label()
            'TSLA ⬇2.10%'
            
            >>> block = TreemapBlock("CASH", 0.02, 0.0, 0.0, "flat")
            >>> block.get_label()
            'CASH 0.00%'
        """
        arrow = "⬆" if self.direction == "up" else "⬇" if self.direction == "down" else ""
        return f"{self.symbol} {arrow}{abs(self.price_change):.2f}%"


class PerformanceCalculator:
    """Calculates performance contributions for ETF holdings.
    
    This class handles the calculation of how much each holding contributes
    to the overall ETF performance, based on its weight and price change.
    
    Examples:
        >>> from etf_treemap.holdings import Holding
        >>> calc = PerformanceCalculator()
        >>> holding = Holding("AAPL", "Apple Inc.", 0.05)
        >>> contribution = calc.calculate_contribution(holding, 10.0)
        >>> print(f"Contribution: {contribution:.2f}%")
        Contribution: 0.50%
        
        >>> direction = calc.classify_direction(10.0)
        >>> print(direction)
        up
    """
    
    def calculate_contribution(self, holding: Holding, price_change: float) -> float:
        """Calculate performance contribution as weight multiplied by price change.
        
        The contribution represents how much a holding's price movement affects
        the overall ETF performance, weighted by its portfolio allocation.
        
        Args:
            holding (Holding): Holding object containing weight information.
            price_change (float): Percentage price change for the holding.
            
        Returns:
            float: Performance contribution (can be positive or negative).
        
        Examples:
            >>> from etf_treemap.holdings import Holding
            >>> calc = PerformanceCalculator()
            >>> holding = Holding("AAPL", "Apple Inc.", 0.05)  # 5% weight
            >>> calc.calculate_contribution(holding, 10.0)  # 10% price increase
            0.5
            
            >>> holding = Holding("TSLA", "Tesla Inc.", 0.03)  # 3% weight
            >>> calc.calculate_contribution(holding, -5.0)  # 5% price decrease
            -0.15
        """
        return holding.weight * price_change
    
    def classify_direction(self, price_change: float) -> str:
        """Classify price change as 'up', 'down', or 'flat'.
        
        Determines the direction of price movement for visualization purposes.
        
        Args:
            price_change (float): Percentage price change.
            
        Returns:
            str: Direction classification - 'up' for positive, 'down' for negative,
                'flat' for zero.
        
        Examples:
            >>> calc = PerformanceCalculator()
            >>> calc.classify_direction(5.5)
            'up'
            >>> calc.classify_direction(-2.3)
            'down'
            >>> calc.classify_direction(0.0)
            'flat'
        """
        if price_change > 0:
            return "up"
        elif price_change < 0:
            return "down"
        else:
            return "flat"
    
    def prepare_treemap_data(self, holdings: List[Holding], 
                            price_changes: Dict[str, float]) -> List[TreemapBlock]:
        """Prepare all data needed for treemap visualization.
        
        Combines holdings data with price changes to create TreemapBlock objects
        that contain all information needed for rendering. Holdings without
        price data are automatically excluded.
        
        Args:
            holdings (List[Holding]): List of holdings with weights.
            price_changes (Dict[str, float]): Dictionary mapping ticker symbols
                to their percentage price changes.
            
        Returns:
            List[TreemapBlock]: List of treemap blocks ready for visualization,
                with contributions calculated and directions classified.
        
        Examples:
            >>> from etf_treemap.holdings import Holding
            >>> calc = PerformanceCalculator()
            >>> holdings = [
            ...     Holding("AAPL", "Apple Inc.", 0.05),
            ...     Holding("MSFT", "Microsoft Corp.", 0.04)
            ... ]
            >>> price_changes = {"AAPL": 5.0, "MSFT": -2.0}
            >>> blocks = calc.prepare_treemap_data(holdings, price_changes)
            >>> len(blocks)
            2
            >>> blocks[0].symbol
            'AAPL'
            >>> blocks[0].direction
            'up'
        """
        blocks = []
        
        for holding in holdings:
            # Skip holdings without price data
            if holding.symbol not in price_changes:
                continue
            
            price_change = price_changes[holding.symbol]
            contribution = self.calculate_contribution(holding, price_change)
            direction = self.classify_direction(price_change)
            
            block = TreemapBlock(
                symbol=holding.symbol,
                weight=holding.weight,
                price_change=price_change,
                contribution=abs(contribution),  # Use absolute value for block size
                direction=direction
            )
            blocks.append(block)
        
        return blocks
