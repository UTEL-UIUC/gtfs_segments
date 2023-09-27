import os
import datetime
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
            "San Francisco-San Francisco Municipal Transportation Agency (SFMTA, Muni)-CA",
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
        assert [
            "stop_code",
            "stop_url",
            "stop_id",
            "stop_desc",
            "stop_name",
            "location_type",
            "zone_id",
            "geometry",
        ] == list(feed.stops.columns)

    def test_service_ids_by_date(self):
        service_ids_by_date = ptg.read_service_ids_by_date(self.gtfs_path)

        assert len(service_ids_by_date) == 161
        assert datetime.date(2022, 7, 30) in service_ids_by_date

    def test_dates_by_service_ids(self):
        dates_by_service_ids = ptg.read_dates_by_service_ids(self.gtfs_path)
        assert len(dates_by_service_ids) == 6
        assert frozenset({"2_merged_11239965"}) in dates_by_service_ids

    def test_trip_counts_by_date(self):
        trip_counts_by_date = ptg.read_trip_counts_by_date(self.gtfs_path)
        assert len(trip_counts_by_date) == 161
        assert datetime.date(2022, 8, 20) in trip_counts_by_date

    def test_busiest_date(self):
        date, service_ids = ptg.read_busiest_date(self.gtfs_path)
        assert date == datetime.date(2022, 10, 3)
        assert service_ids == frozenset({"1_merged_11239966"})

    def test_busiest_week(self):
        service_ids_by_date = ptg.read_busiest_week(self.gtfs_path)
        assert service_ids_by_date == {
            datetime.date(2022, 10, 3): frozenset({"1_merged_11239966"}),
            datetime.date(2022, 10, 4): frozenset({"1_merged_11239966"}),
            datetime.date(2022, 10, 5): frozenset({"1_merged_11239966"}),
            datetime.date(2022, 10, 6): frozenset({"1_merged_11239966"}),
            datetime.date(2022, 10, 7): frozenset({"1_merged_11239966"}),
            datetime.date(2022, 10, 8): frozenset({"2_merged_11239968"}),
            datetime.date(2022, 10, 9): frozenset({"3_merged_11239967"}),
        }
