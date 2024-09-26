"""
The gtfs_segments package main init file.
"""
import importlib.metadata
from .geom_utils import view_heatmap, view_spacings, view_spacings_interactive
from .gtfs_segments import get_gtfs_segments, get_gtfs_segments_with_elevations, pipeline_gtfs, process_feed
from .mobility import (
    download_latest_data,
    fetch_gtfs_source,
    summary_stats_mobility,
)
from .partridge_func import get_bus_feed
from .route_stats import get_route_stats
from .utils import export_segments, plot_hist, process, summary_stats
from .elevations import view_spacings_with_grade

__version__ = importlib.metadata.version("gtfs_segments")
__all__ = [
    "__version__",
    "get_gtfs_segments",
    "get_gtfs_segments_with_elevations",
    "pipeline_gtfs",
    "process_feed",
    "export_segments",
    "plot_hist",
    "fetch_gtfs_source",
    "summary_stats",
    "process",
    "view_spacings",
    "view_spacings_interactive",
    "view_spacings_with_grade",
    "view_heatmap",
    "summary_stats_mobility",
    "download_latest_data",
    "get_route_stats",
    "get_bus_feed",
]
