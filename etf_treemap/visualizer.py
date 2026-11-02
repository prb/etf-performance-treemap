"""Treemap visualization generation module."""

import logging
from typing import Dict, List, Tuple
from datetime import datetime
import matplotlib.colors as mcolors
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import squarify
from etf_treemap.calculator import TreemapBlock

logger = logging.getLogger(__name__)


class TreemapVisualizer:
    """Generates treemap visualizations using matplotlib and squarify.
    
    This class creates treemap charts where each rectangle represents a holding,
    sized by its performance contribution and colored by direction (green for up,
    red for down, grey for flat).
    
    Attributes:
        etf_symbol (str): ETF ticker symbol for the title.
        date_range (Tuple[datetime, datetime]): Start and end dates for the title.
    
    Examples:
        >>> from datetime import datetime
        >>> visualizer = TreemapVisualizer(
        ...     "UFO",
        ...     (datetime(2024, 1, 1), datetime(2024, 1, 31))
        ... )
        >>> # Create some sample blocks
        >>> from etf_treemap.calculator import TreemapBlock
        >>> blocks = [
        ...     TreemapBlock("AAPL", 0.05, 5.0, 0.25, "up"),
        ...     TreemapBlock("TSLA", 0.03, -2.0, 0.06, "down")
        ... ]
        >>> visualizer.generate_treemap(blocks, "output.png")
    """
    
    def __init__(self, etf_symbol: str, date_range: Tuple[datetime, datetime]):
        """Initialize visualizer with ETF symbol and date range for title.
        
        Args:
            etf_symbol (str): ETF ticker symbol (e.g., "UFO", "SPY").
            date_range (Tuple[datetime, datetime]): Tuple of (start_date, end_date)
                for the lookback period, used in the chart title.
        
        Examples:
            >>> from datetime import datetime
            >>> visualizer = TreemapVisualizer(
            ...     "SPY",
            ...     (datetime(2024, 1, 1), datetime(2024, 1, 31))
            ... )
            >>> print(visualizer.etf_symbol)
            SPY
        """
        self.etf_symbol = etf_symbol
        self.date_range = date_range
    
    def generate_treemap(self, blocks: List[TreemapBlock], output_path: str) -> None:
        """Generate hierarchical treemap visualization and save as PNG.
        
        Creates a hierarchical treemap chart with two main sections:
        - Gains (green section) containing all positive performers
        - Losses (red section) containing all negative performers
        
        Within each section, individual holdings are sized by their contribution.
        
        Args:
            blocks (List[TreemapBlock]): List of treemap blocks to visualize.
                Each block must have a positive contribution value.
            output_path (str): File path where the PNG image should be saved.
        
        Raises:
            ValueError: If blocks list is empty or all blocks have zero contribution.
        
        Examples:
            >>> from etf_treemap.calculator import TreemapBlock
            >>> visualizer = TreemapVisualizer("UFO", (start_date, end_date))
            >>> blocks = [
            ...     TreemapBlock("AAPL", 0.05, 5.0, 0.25, "up"),
            ...     TreemapBlock("MSFT", 0.04, 3.0, 0.12, "up"),
            ...     TreemapBlock("TSLA", 0.03, -2.0, 0.06, "down")
            ... ]
            >>> visualizer.generate_treemap(blocks, "UFO-1d-treemap.png")
        """
        logger.info(f"Generating treemap with {len(blocks)} blocks")
        
        if not blocks:
            logger.error("Cannot generate treemap: no blocks provided")
            raise ValueError("Cannot generate treemap: no blocks provided")
        
        # Filter out blocks with zero contribution
        non_zero_blocks = [block for block in blocks if block.contribution > 0]
        
        if not non_zero_blocks:
            logger.error("Cannot generate treemap: all blocks have zero contribution")
            raise ValueError("Cannot generate treemap: all blocks have zero contribution")
        
        if len(non_zero_blocks) < len(blocks):
            logger.warning(f"Filtered out {len(blocks) - len(non_zero_blocks)} blocks with zero contribution")
        
        # Separate blocks into gains and losses
        gains = [block for block in non_zero_blocks if block.direction == 'up']
        losses = [block for block in non_zero_blocks if block.direction == 'down']
        flat = [block for block in non_zero_blocks if block.direction == 'flat']
        
        # Add flat blocks to the smaller group to balance the layout
        gains_total = sum(b.contribution for b in gains)
        losses_total = sum(b.contribution for b in losses)
        flat_total = sum(b.contribution for b in flat)
        
        if flat:
            if gains_total < losses_total:
                gains.extend(flat)
                gains_total += flat_total
            else:
                losses.extend(flat)
                losses_total += flat_total
        
        # Determine if single day for title formatting
        is_single_day = self.date_range[0].date() == self.date_range[1].date()
        title = self._format_title(is_single_day)
        
        logger.info(f"Creating hierarchical treemap with title: {title}")
        logger.info(f"Gains: {len(gains)} blocks, Losses: {len(losses)} blocks")
        
        # Create figure and axis
        # Object-oriented API with an explicit Agg canvas: no pyplot, no GUI
        # backend, so this works on headless machines.
        fig = Figure(figsize=(16, 10))
        FigureCanvasAgg(fig)
        ax = fig.subplots()
        
        # Calculate the split between gains and losses
        total = gains_total + losses_total
        gains_width = gains_total / total if total > 0 else 0.5
        losses_width = losses_total / total if total > 0 else 0.5
        
        # Create two main rectangles side by side
        # Gains on the left, losses on the right
        gains_rect = {'x': 0, 'y': 0, 'dx': gains_width, 'dy': 1}
        losses_rect = {'x': gains_width, 'y': 0, 'dx': losses_width, 'dy': 1}
        
        # Plot gains section
        if gains:
            self._plot_section(
                ax, gains, gains_rect,
                section_color='#2ecc71',  # Green
                section_label='GAINS'
            )
        
        # Plot losses section
        if losses:
            self._plot_section(
                ax, losses, losses_rect,
                section_color='#e74c3c',  # Red
                section_label='LOSSES'
            )
        
        # Set title and remove axes
        ax.set_title(title, fontsize=16, weight='bold', pad=20)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # Save figure
        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        
        logger.info(f"Treemap saved successfully to: {output_path}")
    
    def _plot_section(self, ax: Axes, blocks: List[TreemapBlock], rect: Dict[str, float],
                      section_color: str, section_label: str) -> None:
        """Plot a hierarchical section (gains or losses) within a rectangle.
        
        Args:
            ax: Matplotlib axis
            blocks: List of blocks to plot in this section
            rect: Dictionary with 'x', 'y', 'dx', 'dy' defining the section bounds
            section_color: Base color for the section
            section_label: Label for the section (e.g., 'GAINS' or 'LOSSES')
        """
        logger.debug(f"Plotting section: {section_label}")
        for block in blocks:
            logger.debug(
                f"  {block.symbol}: contribution={block.contribution:.6f}, "
                f"change={block.price_change:+.2f}%"
            )
        
        # Extract rectangle bounds
        x, y, dx, dy = rect['x'], rect['y'], rect['dx'], rect['dy']
        logger.debug(f"Section rectangle: x={x:.4f}, y={y:.4f}, dx={dx:.4f}, dy={dy:.4f}")
        
        # Draw section border with darker shade
        border_color = self._darken_color(section_color, 0.3)
        section_rect = Rectangle(
            (x, y), dx, dy,
            fill=False,
            edgecolor=border_color,
            linewidth=3
        )
        ax.add_patch(section_rect)
        
        # Add section label at the top
        label_y = y + dy - 0.02
        ax.text(
            x + dx/2, label_y,
            section_label,
            ha='center', va='top',
            fontsize=14, weight='bold',
            color=border_color,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                     edgecolor=border_color, linewidth=2)
        )
        
        # Calculate sizes for blocks within this section
        # IMPORTANT: Use raw contribution values to maintain global proportionality
        sizes = [block.contribution for block in blocks]
        
        # Normalize blocks to fit within the section rectangle
        # Leave some padding for the label
        label_height = 0.05
        # Use proportional padding to maintain exact proportionality
        # Padding is a fixed percentage of section dimensions
        padding_ratio = 0.002  # 0.2% padding
        padding_x = dx * padding_ratio
        padding_y = dy * padding_ratio
        
        # Use squarify to layout blocks within this section
        inner_width = dx - 2 * padding_x
        inner_height = dy - 2 * padding_y - label_height
        
        # Calculate available area for blocks
        inner_area = inner_width * inner_height
        
        logger.debug(
            f"Inner dimensions: width={inner_width:.4f}, height={inner_height:.4f}, "
            f"area={inner_area:.4f}"
        )
        
        # Calculate total contribution for this section
        total_contribution = sum(sizes)
        
        logger.debug(f"Total contribution in section: {total_contribution:.6f}")
        
        # Scale sizes to fit the available area while maintaining proportions
        # Each block gets: (its_contribution / total_contribution) * available_area
        scaled_sizes = [(size / total_contribution) * inner_area for size in sizes]
        
        logger.debug(f"Scaled sizes for squarify: {scaled_sizes}")
        
        # Use squarify to layout blocks with the scaled sizes
        rects = squarify.squarify(scaled_sizes, x + padding_x, y + padding_y, inner_width, inner_height)
        
        for block, rect_out in zip(blocks, rects):
            area = rect_out['dx'] * rect_out['dy']
            logger.debug(
                f"  {block.symbol}: x={rect_out['x']:.4f}, y={rect_out['y']:.4f}, "
                f"dx={rect_out['dx']:.4f}, dy={rect_out['dy']:.4f}, area={area:.6f}"
            )
        
        # Plot each block
        for block, block_rect in zip(blocks, rects):
            bx, by, bdx, bdy = block_rect['x'], block_rect['y'], block_rect['dx'], block_rect['dy']
            
            # Get block color
            block_color = self._get_color(block.direction)
            
            # Draw block rectangle
            rect_patch = Rectangle(
                (bx, by), bdx, bdy,
                facecolor=block_color,
                edgecolor='white',
                linewidth=2,
                alpha=0.8
            )
            ax.add_patch(rect_patch)
            
            # Add block label
            label = self._format_label(block)
            text_color = self._get_text_color(block_color)
            
            # Only show label if block is large enough
            if bdx * bdy > 0.002:  # Minimum size threshold
                ax.text(
                    bx + bdx/2, by + bdy/2,
                    label,
                    ha='center', va='center',
                    fontsize=10, weight='bold',
                    color=text_color,
                    wrap=True
                )
    
    def _darken_color(self, color: str, factor: float) -> str:
        """Darken a color by a given factor.
        
        Args:
            color: Hex color code
            factor: Darkening factor (0-1, where 1 is black)
            
        Returns:
            Darkened hex color code
        """
        rgb = mcolors.to_rgb(color)
        darkened = tuple(max(0, c * (1 - factor)) for c in rgb)
        return mcolors.to_hex(darkened)
    
    def _format_title(self, is_single_day: bool) -> str:
        """Format chart title based on date range.
        
        Creates a title string that includes the ETF symbol and date range.
        For single-day lookbacks, shows only one date; for multi-day periods,
        shows start and end dates.
        
        Args:
            is_single_day (bool): True if the lookback period is a single day.
            
        Returns:
            str: Formatted title string.
        
        Examples:
            >>> from datetime import datetime
            >>> visualizer = TreemapVisualizer(
            ...     "UFO",
            ...     (datetime(2024, 1, 15), datetime(2024, 1, 15))
            ... )
            >>> visualizer._format_title(True)
            'UFO Holdings Performance 2024-01-15'
            
            >>> visualizer = TreemapVisualizer(
            ...     "SPY",
            ...     (datetime(2024, 1, 1), datetime(2024, 1, 31))
            ... )
            >>> visualizer._format_title(False)
            'SPY Holdings Performance 2024-01-01-2024-01-31'
        """
        start_date = self.date_range[0]
        end_date = self.date_range[1]
        
        if is_single_day:
            # Format: "{ETF_Symbol} Holdings Performance {Date as YYYY-MM-DD}"
            date_str = end_date.strftime("%Y-%m-%d")
            return f"{self.etf_symbol} Holdings Performance {date_str}"
        else:
            # Format: "{ETF_Symbol} Holdings Performance {Start Date as YYYY-MM-DD}-{End Date as YYYY-MM-DD}"
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            return f"{self.etf_symbol} Holdings Performance {start_str}-{end_str}"
    
    def _format_label(self, block: TreemapBlock) -> str:
        """Format block label with symbol, arrow, and percentage.
        
        Delegates to the TreemapBlock's get_label() method to create a
        consistent label format.
        
        Args:
            block (TreemapBlock): TreemapBlock to format.
            
        Returns:
            str: Formatted label string.
        
        Examples:
            >>> from etf_treemap.calculator import TreemapBlock
            >>> visualizer = TreemapVisualizer("UFO", (start, end))
            >>> block = TreemapBlock("AAPL", 0.05, 5.23, 0.26, "up")
            >>> visualizer._format_label(block)
            'AAPL ⬆5.23%'
        """
        # Use the get_label method from TreemapBlock
        return block.get_label()
    
    def _get_color(self, direction: str) -> str:
        """Map direction classification to color code.
        
        Returns the appropriate color for visualizing price direction:
        green for up, red for down, grey for flat.
        
        Args:
            direction (str): Direction classification ('up', 'down', or 'flat').
            
        Returns:
            str: Hex color code for the direction.
        
        Examples:
            >>> visualizer = TreemapVisualizer("UFO", (start, end))
            >>> visualizer._get_color("up")
            '#2ecc71'
            >>> visualizer._get_color("down")
            '#e74c3c'
            >>> visualizer._get_color("flat")
            '#95a5a6'
        """
        color_map = {
            'up': '#2ecc71',      # Green
            'down': '#e74c3c',    # Red
            'flat': '#95a5a6'     # Grey
        }
        return color_map.get(direction, '#95a5a6')  # Default to grey
    
    def _get_text_color(self, background_color: str) -> str:
        """Return contrasting text color for readability.
        
        Calculates the relative luminance of the background color and returns
        white text for dark backgrounds or black text for light backgrounds.
        
        Args:
            background_color (str): Background color code or name.
            
        Returns:
            str: Text color ('white' or 'black') that provides good contrast.
        
        Examples:
            >>> visualizer = TreemapVisualizer("UFO", (start, end))
            >>> visualizer._get_text_color("#2ecc71")  # Green background
            'black'
            >>> visualizer._get_text_color("#e74c3c")  # Red background
            'white'
            >>> visualizer._get_text_color("#000000")  # Black background
            'white'
        """
        # Convert color to RGB
        try:
            rgb = mcolors.to_rgb(background_color)
        except ValueError:
            # If color conversion fails, default to black text
            return 'black'
        
        # Calculate relative luminance using the formula:
        # L = 0.2126 * R + 0.7152 * G + 0.0722 * B
        luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
        
        # Use white text for dark backgrounds, black text for light backgrounds
        # Threshold of 0.5 provides good contrast
        return 'white' if luminance < 0.5 else 'black'
