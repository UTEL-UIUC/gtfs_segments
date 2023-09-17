"""Tests for `gtfs_segments` package."""

import os
import requests
import unittest
import partridge as ptg
from gtfs_segments import *


class TestBasic(unittest.TestCase):
    """Tests for some basic prerequisites for the package to work."""

    def setUp(self):
        """Set up test fixtures, if any."""
        self.gtfs_path = "data/San Francisco-San Francisco Municipal Transportation Agency (SFMTA, Muni)-CA/gtfs.zip"
        

    def tearDown(self):
        """Tear down test fixtures, if any."""
        
    def test_state_abbreviations(self):
        """
        The function tests if a given URL exists and is live.
        """
        url = "https://github.com/UTEL-UIUC/gtfs_segments/blob/main/state_abbreviations.json"
        
        try:
            response = requests.get(url)
            # Additional check to ensure the URL not only exists but is also live
            self.assertTrue(response.status_code == 200)
        except requests.RequestException as E:
            self.fail(f"URL {url} doesn't exist or couldn't be reached")
    
    def test_gtfs_exists(self):
        """
        The function tests if a given GTFS file exists.
        """
        self.assertTrue(os.path.exists(self.gtfs_path), 'The SFMTA example gtfs file does not exist')
    
    def test_partridge(self):
        """
        The function tests if partridge is installed and specifically the version is from https://github.com/praneethd7/partridge.git@fix_geopandas_projection
        """
        self.assertTrue(ptg.__version__ == '1.1.1a0', "Please use the version of partridge from https://github.com/praneethd7/partridge.git@fix_geopandas_projection")
        _date, feed = get_bus_feed(self.gtfs_path)
        self.assertTrue(type(feed) == ptg.gtfs.Feed, "Error with feed type. Make sure the partridge library is installed correctly")
        self.assertGreaterEqual(len(feed.agency), 1, "Some error with feed processing")
    
        
        
        
        
        