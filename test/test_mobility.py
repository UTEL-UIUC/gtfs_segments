"""Tests for `gtfs_segments` package."""

import os
import glob
import unittest
from gtfs_segments import *
import pandas as pd

dir = os.path.dirname(__file__)
class TestMobiliy(unittest.TestCase):
    """Tests for the mobility.py module."""

    def setUp(self):
        """Set up test fixtures, if any."""
        self.gtfs_path = "data/San Francisco-San Francisco Municipal Transportation Agency (SFMTA, Muni)-CA/gtfs.zip"
        

    def tearDown(self):
        """Tear down test fixtures, if any."""
    
    
    def test_check_fetch_all(self):
        """
        The function "check_fetch_all" checks if the output of the "fetch_gtfs_source" function is a
        dataframe and if the number of all feeds is greater than or equal to the number of active feeds.
        """
        df_all_active = fetch_gtfs_source('ALL', active = True)
        df_all = fetch_gtfs_source('ALL', active = False)
        
        self.assertEqual(type(df_all_active), pd.DataFrame, "The output of fetch_gtfs_source should be a dataframe")
        self.assertGreaterEqual(len(df_all), len(df_all_active), "The number of all feeds should be greater than or equal to the number of active feeds")
    
    def test_download_gtfs(self):
        sources_df = fetch_gtfs_source('SFMTA', active = True)
        download_latest_data(sources_df, os.path.join(dir,'data'))
        self.assertTrue(os.path.exists(os.path.join(dir,'data')), 'Check if the data_test folder exists')
        folders = glob.glob(os.path.join(dir,'data/*'))
        self.assertTrue(len(folders) > 0, 'Check if the data_test folder is not empty')
        sub_folder = glob.glob(os.path.join(dir,'data/*'))
        file = os.listdir(sub_folder[0])[0]
        self.assertTrue(file.endswith('.zip'), 'Check if the data folder contains a zip file')