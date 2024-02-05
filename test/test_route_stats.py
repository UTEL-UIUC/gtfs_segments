import os
import unittest

import pandas as pd

from gtfs_segments import get_bus_feed, get_route_stats

test_dir = os.path.dirname(__file__)


class TestRouteStats(unittest.TestCase):
    """Tests for utils.py module in the package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        self.gtfs_path = os.path.join(
            test_dir,
            "data",
            "Ann Arbor-University of Michigan Transit Services-MI",
            "gtfs.zip",
        )

    def test_route_stats(self):
        feed = get_bus_feed(self.gtfs_path)
        route_stats_df = get_route_stats(feed)
        self.assertTrue(
            isinstance(route_stats_df, pd.DataFrame),
            "Error with summary_stats. Result should be a DataFrame",
        )
