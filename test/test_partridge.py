import datetime
import os
import unittest

import geopandas as gpd

import gtfs_segments.partridge_mod as ptg

test_dir = os.path.dirname(__file__)


class TestPartridge(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures, if any."""
        self.gtfs_path = os.path.join(
            test_dir,
            "data",
            "Ann Arbor-University of Michigan Transit Services-MI",
            "gtfs.zip",
        )

    def test_load_geo_feed(self):
        feed = ptg.load_geo_feed(self.gtfs_path)
        assert isinstance(feed.shapes, gpd.GeoDataFrame)
        assert isinstance(feed.stops, gpd.GeoDataFrame)
        assert {"LineString"} == set(feed.shapes.geom_type)
        assert {"Point"} == set(feed.stops.geom_type)
        assert feed.shapes.crs == "epsg:4326"
        assert feed.stops.crs == "epsg:4326"
        assert ["shape_id", "geometry"] == list(feed.shapes.columns)
        # assert [
        #     "stop_id",
        #     "stop_code",
        #     "stop_name",
        #     "stop_desc",
        #     "zone_id",
        #     "stop_url",
        #     "location_type",
        #     "parent_station",
        #     "stop_timezone",
        #     "wheelchair_boarding",
        #     "geometry",
        # ] == list(feed.stops.columns)

    def test_service_ids_by_date(self):
        service_ids_by_date = ptg.read_service_ids_by_date(self.gtfs_path)

        assert len(service_ids_by_date) == 133
        assert datetime.date(2022, 2, 17) in service_ids_by_date

    def test_dates_by_service_ids(self):
        dates_by_service_ids = ptg.read_dates_by_service_ids(self.gtfs_path)
        assert len(dates_by_service_ids) == 16
        assert frozenset({"2"}) in dates_by_service_ids

    def test_trip_counts_by_date(self):
        trip_counts_by_date = ptg.read_trip_counts_by_date(self.gtfs_path)
        assert len(trip_counts_by_date) == 133
        assert datetime.date(2022, 4, 12) in trip_counts_by_date

    def test_busiest_date(self):
        date, service_ids = ptg.read_busiest_date(self.gtfs_path)
        assert date == datetime.date(2022, 1, 10)
        assert service_ids == frozenset({"7"})

    def test_busiest_week(self):
        service_ids_by_date = ptg.read_busiest_week(self.gtfs_path)
        assert service_ids_by_date == {
            datetime.date(2022, 1, 10): frozenset({"7"}),
            datetime.date(2022, 1, 11): frozenset({"10"}),
            datetime.date(2022, 1, 12): frozenset({"10"}),
            datetime.date(2022, 1, 13): frozenset({"10"}),
            datetime.date(2022, 1, 14): frozenset({"4"}),
            datetime.date(2022, 1, 15): frozenset({"11"}),
            datetime.date(2022, 1, 16): frozenset({"9"}),
        }
