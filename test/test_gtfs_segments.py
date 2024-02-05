"""Tests for `gtfs_segments` package."""

import os
import unittest

import geopandas as gpd

from gtfs_segments.gtfs_segments import get_gtfs_segments, inspect_feed
from gtfs_segments.partridge_func import get_bus_feed

test_dir = os.path.dirname(__file__)


class TestGTFSSegments(unittest.TestCase):
    """Tests for gtfs_segments.py module in the package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        self.gtfs_path = os.path.join(
            test_dir,
            "data",
            "Ann Arbor-University of Michigan Transit Services-MI",
            "gtfs.zip",
        )

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_feed_inspect(self):
        """
        The function `test_feed_inspect` tests the `inspect_feed` function on a specific feed.
        """
        feed = get_bus_feed(self.gtfs_path)
        self.assertTrue(
            inspect_feed(feed),
            "Error with feed inspection. Should work for the Ann Arbor example feed",
        )

    def test_get_gtfs_segments(self):
        """
        The function `test_get_gtfs_segments` tests various parameters of the `get_gtfs_segments`
        function.
        """
        df = get_gtfs_segments(self.gtfs_path)
        self.assertTrue(
            type(df) == gpd.GeoDataFrame,
            "Error with get_gtfs_segments. Should work for the Ann Arbor example feed",
        )
        df_threshold = get_gtfs_segments(self.gtfs_path, threshold=5)
        self.assertTrue(
            len(df_threshold) <= len(df),
            "Higher threshold should result in fewer segments",
        )
        df_agency = get_gtfs_segments(self.gtfs_path, agency_id="1")
        self.assertTrue(
            len(df_agency) == len(df),
            "Should lead to same number of segments as the original feed has only one agency",
        )
        df_max_spacing = get_gtfs_segments(self.gtfs_path, max_spacing=3000)
        self.assertTrue(
            len(df_max_spacing) <= len(df),
            "Higher max_spacing should result in fewer segments",
        )
        self.assertTrue(
            df_max_spacing["distance"].max() <= 3000,
            "Max spacing should be less than or equal to 3000",
        )
        self.assertTrue(
            df_max_spacing["distance"].min() >= 0,
            "Min spacing should be greater than or equal to 0",
        )
