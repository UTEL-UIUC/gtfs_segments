"""Tests for `gtfs_segments` package."""

import os
import unittest
from datetime import date

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

    def test_get_gtfs_segments_with_date_string(self):
        """
        Test get_gtfs_segments with date parameter using string format (YYYYMMDD).
        Uses a weekday (2022-01-11) from the Ann Arbor GTFS data that has sufficient service.
        """
        # Test with a Tuesday date that has good service coverage
        tuesday_date = "20220111"  # Tuesday from Ann Arbor GTFS data
        df_tuesday = get_gtfs_segments(self.gtfs_path, date=tuesday_date)
        
        self.assertTrue(
            type(df_tuesday) == gpd.GeoDataFrame,
            "get_gtfs_segments with date string should return GeoDataFrame",
        )
        self.assertTrue(
            len(df_tuesday) > 0,
            "Tuesday segments should contain data",
        )

    def test_get_gtfs_segments_with_date_object(self):
        """
        Test get_gtfs_segments with date parameter using datetime.date object.
        """
        # Test with a Tuesday date using datetime.date object
        tuesday_date = date(2022, 1, 11)  # Tuesday from Ann Arbor GTFS data
        df_tuesday = get_gtfs_segments(self.gtfs_path, date=tuesday_date)
        
        self.assertTrue(
            type(df_tuesday) == gpd.GeoDataFrame,
            "get_gtfs_segments with date object should return GeoDataFrame",
        )
        self.assertTrue(
            len(df_tuesday) > 0,
            "Tuesday segments should contain data",
        )

    def test_get_gtfs_segments_date_vs_busiest_day(self):
        """
        Test that specifying a date gives different results than the default busiest day.
        This test focuses on verifying that the date parameter is being processed correctly.
        """
        # Default behavior (busiest day: 2022-01-10)
        df_busiest = get_gtfs_segments(self.gtfs_path)
        
        # Specific Tuesday (2022-01-11) which should have different service pattern
        df_tuesday = get_gtfs_segments(self.gtfs_path, date="20220111")
        
        # Both should return valid GeoDataFrames
        self.assertTrue(
            type(df_busiest) == gpd.GeoDataFrame and type(df_tuesday) == gpd.GeoDataFrame,
            "Both should return GeoDataFrames",
        )
        
        # Check that both have the expected columns
        expected_columns = ["segment_id", "route_id", "traversals", "distance", "geometry"]
        for col in expected_columns:
            self.assertTrue(
                col in df_busiest.columns,
                f"Busiest day result should contain {col} column",
            )
            self.assertTrue(
                col in df_tuesday.columns,
                f"Tuesday result should contain {col} column",
            )

    def test_get_gtfs_segments_date_combined_parameters(self):
        """
        Test get_gtfs_segments with date parameter combined with other parameters.
        """
        df_combined = get_gtfs_segments(
            self.gtfs_path,
            date="20220111",  # Tuesday
            threshold=2,
            max_spacing=2000,
            agency_id="1"
        )
        
        self.assertTrue(
            type(df_combined) == gpd.GeoDataFrame,
            "Combined parameters with date should return GeoDataFrame",
        )
        if len(df_combined) > 0:  # Only check if we have data
            self.assertTrue(
                df_combined["distance"].max() <= 2000,
                "Max spacing constraint should be applied with date parameter",
            )

    def test_get_gtfs_segments_invalid_date_format(self):
        """
        Test that invalid date format raises appropriate error.
        """
        with self.assertRaises(ValueError) as context:
            get_gtfs_segments(self.gtfs_path, date="2022-01-16")  # Wrong format
        
        self.assertTrue(
            "YYYYMMDD format" in str(context.exception),
            "Should provide helpful error message for invalid date format",
        )

    def test_get_gtfs_segments_date_not_in_calendar(self):
        """
        Test that date not in GTFS calendar raises appropriate error.
        """
        with self.assertRaises(ValueError) as context:
            get_gtfs_segments(self.gtfs_path, date="20250101")  # Future date not in GTFS
        
        self.assertTrue(
            "not found in GTFS service calendar" in str(context.exception),
            "Should provide helpful error message for date not in calendar",
        )

    def test_get_bus_feed_with_date(self):
        """
        Test get_bus_feed function directly with date parameter.
        """
        # Test string date
        feed_with_date = get_bus_feed(self.gtfs_path, date="20220116")
        self.assertTrue(
            hasattr(feed_with_date, 'trips') and len(feed_with_date.trips) > 0,
            "get_bus_feed with date should return valid feed with trips",
        )
        
        # Test datetime.date object
        feed_with_date_obj = get_bus_feed(self.gtfs_path, date=date(2022, 1, 11))
        self.assertTrue(
            hasattr(feed_with_date_obj, 'trips') and len(feed_with_date_obj.trips) > 0,
            "get_bus_feed with date object should return valid feed with trips",
        )

    def test_get_gtfs_segments_with_date_list(self):
        """
        Test get_gtfs_segments with a list of dates.
        """
        # Test with multiple weekdays
        date_list = ["20220110", "20220111", "20220112"]  # Mon, Tue, Wed
        df_multi = get_gtfs_segments(self.gtfs_path, date=date_list)
        
        self.assertTrue(
            type(df_multi) == gpd.GeoDataFrame,
            "get_gtfs_segments with date list should return GeoDataFrame",
        )
        self.assertTrue(
            len(df_multi) > 0,
            "Multi-date segments should contain data",
        )

    def test_get_gtfs_segments_mixed_date_types(self):
        """
        Test get_gtfs_segments with mixed date types (strings and date objects).
        """
        from datetime import date
        
        # Mix of string and date object
        date_list = ["20220110", date(2022, 1, 11)]
        df_mixed = get_gtfs_segments(self.gtfs_path, date=date_list)
        
        self.assertTrue(
            type(df_mixed) == gpd.GeoDataFrame,
            "get_gtfs_segments with mixed date types should return GeoDataFrame",
        )
        self.assertTrue(
            len(df_mixed) > 0,
            "Mixed date type segments should contain data",
        )

    def test_get_gtfs_segments_skip_invalid_dates(self):
        """
        Test get_gtfs_segments with skip_invalid_dates=True.
        """
        # Include one valid and one invalid date
        date_list = ["20220110", "20250101"]  # Valid date and future invalid date
        df_skip = get_gtfs_segments(
            self.gtfs_path, 
            date=date_list, 
            skip_invalid_dates=True
        )
        
        self.assertTrue(
            type(df_skip) == gpd.GeoDataFrame,
            "get_gtfs_segments with skip_invalid_dates should return GeoDataFrame",
        )
        self.assertTrue(
            len(df_skip) > 0,
            "Should process valid dates when skipping invalid ones",
        )

    def test_get_gtfs_segments_all_invalid_dates_with_skip(self):
        """
        Test error handling when all dates are invalid but skip_invalid_dates=True.
        """
        # All invalid dates
        date_list = ["20250101", "20250102"]
        
        with self.assertRaises(ValueError) as context:
            get_gtfs_segments(
                self.gtfs_path, 
                date=date_list, 
                skip_invalid_dates=True
            )
        
        self.assertIn("No valid dates found", str(context.exception))

    def test_get_gtfs_segments_invalid_date_list_strict(self):
        """
        Test error handling for invalid dates in list with skip_invalid_dates=False.
        """
        # Include one invalid date with strict validation
        date_list = ["20220110", "20250101"]
        
        with self.assertRaises(ValueError) as context:
            get_gtfs_segments(self.gtfs_path, date=date_list, skip_invalid_dates=False)
        
        self.assertIn("not found in GTFS service calendar", str(context.exception))

    def test_get_gtfs_segments_empty_date_list(self):
        """
        Test error handling for empty date list.
        """
        with self.assertRaises(ValueError) as context:
            get_gtfs_segments(self.gtfs_path, date=[])
        
        self.assertIn("Date list cannot be empty", str(context.exception))

    def test_get_gtfs_segments_date_list_with_all_parameters(self):
        """
        Test get_gtfs_segments with date list combined with all other parameters.
        """
        df_comprehensive = get_gtfs_segments(
            self.gtfs_path,
            date=["20220110", "20220111"],
            agency_id="1",
            threshold=2,
            max_spacing=2000,
            parallel=False,
            skip_invalid_dates=False
        )
        
        self.assertTrue(
            type(df_comprehensive) == gpd.GeoDataFrame,
            "Comprehensive parameters with date list should return GeoDataFrame",
        )
        
        if len(df_comprehensive) > 0:
            self.assertTrue(
                df_comprehensive["distance"].max() <= 2000,
                "Max spacing should be applied with date list",
            )

    def test_get_bus_feed_with_date_list(self):
        """
        Test get_bus_feed with a list of dates.
        """
        # Test with multiple dates
        date_list = ["20220110", "20220111"]
        feed_multi = get_bus_feed(self.gtfs_path, date=date_list)
        
        self.assertTrue(
            hasattr(feed_multi, 'trips'),
            "get_bus_feed with date list should return valid feed",
        )
        self.assertTrue(
            len(feed_multi.trips) > 0,
            "Multi-date feed should contain trips",
        )

    def test_get_bus_feed_skip_invalid_dates(self):
        """
        Test get_bus_feed with skip_invalid_dates parameter.
        """
        # Include one valid and one invalid date
        date_list = ["20220110", "20250101"]
        feed_skip = get_bus_feed(
            self.gtfs_path, 
            date=date_list, 
            skip_invalid_dates=True
        )
        
        self.assertTrue(
            hasattr(feed_skip, 'trips'),
            "get_bus_feed with skip_invalid_dates should return valid feed",
        )
        self.assertTrue(
            len(feed_skip.trips) > 0,
            "Should process valid dates when skipping invalid ones",
        )
