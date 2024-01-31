"""Tests for `gtfs_segments` package."""

import os
import unittest

import geopandas as gpd
import matplotlib
import pandas as pd

from gtfs_segments import export_segments, get_gtfs_segments, plot_hist, summary_stats

test_dir = os.path.dirname(__file__)
test_folder = os.path.join(test_dir, "output")
if not os.path.exists(test_folder):
    os.mkdir(test_folder)


class TestUtils(unittest.TestCase):
    """Tests for utils.py module in the package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        # Using UMich Ann Arbor as a test feed to save time
        self.gtfs_path = os.path.join(
            test_dir,
            "data",
            "Ann Arbor-University of Michigan Transit Services-MI",
            "gtfs.zip",
        )
        self.df = get_gtfs_segments(self.gtfs_path)

    def test_plot_histogram(self):
        fig = plot_hist(self.df)
        self.assertTrue(
            type(fig) == matplotlib.figure.Figure,
            "Error with plot_hist. Should work for the SFMTA example feed",
        )
        fig = plot_hist(self.df, show_mean=True)
        self.assertTrue(
            type(fig) == matplotlib.figure.Figure,
            "Error with plot_hist. Should work for the SFMTA example feed",
        )
        fig = plot_hist(
            self.df,
            show_mean=True,
            save_fig=True,
            file_path=os.path.join(test_dir, "output", "test_hist.png"),
        )
        self.assertTrue(
            type(fig) == matplotlib.figure.Figure,
            "Error with plot_hist. Should work for the SFMTA example feed",
        )
        self.assertTrue(
            os.path.exists(os.path.join(test_dir, "output", "test_hist.png")),
            "Check if the test_hist.png file exists",
        )

    def test_summary_stats(self):
        summ_df = summary_stats(self.df)
        self.assertTrue(
            type(summ_df) == pd.DataFrame,
            "Error with summary_stats. Result should be a DataFrame",
        )
        summ_df = summary_stats(
            self.df,
            export=True,
            file_path=os.path.join(test_dir, "output", "test_summary_stats.csv"),
        )
        self.assertTrue(
            isinstance(summ_df, pd.DataFrame),
            "Error with summary_stats. Result should be a DataFrame",
        )
        self.assertTrue(
            os.path.exists(os.path.join(test_dir, "output", "test_summary_stats.csv")),
            "Check if the test_summary_stats.csv file exists",
        )
        self.assertTrue(
            sum(summ_df[summ_df.columns[0]] < 0) == 0,
            "Summary stats should be positive",
        )

    def test_export_segments(self):
        # Test export_segments for .csv and with geometry
        export_segments(
            self.df,
            os.path.join(test_dir, "output", "test_export_segments.csv"),
            output_format="csv",
        )
        self.assertTrue(
            os.path.exists(os.path.join(test_dir, "output", "test_export_segments.csv")),
            "Check if the test_export_segments.csv file exists",
        )
        df = pd.read_csv(os.path.join(test_dir, "output", "test_export_segments.csv"))
        self.assertTrue(
            type(df) == pd.DataFrame,
            "Import again to see if the file is valid and has the same data",
        )
        self.assertTrue(
            len(df) == len(self.df),
            "Error with export_segments. Should work for the SFMTA example feed",
        )

        # Test export_segments for .csv and without geometry
        export_segments(
            self.df,
            os.path.join(test_dir, "output", "test_export_segments.csv"),
            output_format="csv",
            geometry=False,
        )
        self.assertTrue(
            os.path.exists(os.path.join(test_dir, "output", "test_export_segments.csv")),
            "Check if the test_export_segments.csv file exists",
        )
        df = pd.read_csv(os.path.join(test_dir, "output", "test_export_segments.csv"))
        self.assertTrue(
            type(df) == pd.DataFrame,
            "Import again to see if the file is valid and has the same data",
        )
        self.assertTrue("geometry" not in df.columns, "Check if the geometry column is not present")

        # Test export_segments for .geojson and with geometry
        export_segments(
            self.df,
            os.path.join(test_dir, "output", "test_export_segments.geojson"),
            output_format="geojson",
        )
        self.assertTrue(
            os.path.exists(os.path.join(test_dir, "output", "test_export_segments.geojson")),
            "Check if the test_export_segments.geojson file exists",
        )
        gdf = gpd.read_file(os.path.join(test_dir, "output", "test_export_segments.geojson"))
        self.assertTrue(
            type(gdf) == gpd.GeoDataFrame,
            "Import again to see if the file is valid and has the same data",
        )
        self.assertTrue(
            len(gdf) == len(self.df),
            "Error with export_segments. Should work for the SFMTA example feed",
        )
