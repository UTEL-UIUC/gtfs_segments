import datetime
from functools import lru_cache
from typing import Any, Dict, List
import numpy as np
import pandas as pd

try:
    import geopandas as gpd
    from shapely.geometry import LineString
except ImportError as impexc:
    print(impexc)
    print("You must install GeoPandas to use this module.")
    raise

DATE_FORMAT = "%Y%m%d"


# Why 2^17? See https://git.io/vxB2P.
@lru_cache(maxsize=2**17)
def parse_time(val: str) -> np.float64:
    """
    The function `parse_time` takes a string representing a time value in the format "hh:mm:ss" and
    returns the equivalent time in seconds as a numpy float64, or returns the input value if it is
    already a numpy float64 or float.
    
    Args:
      val (str): The parameter `val` is a string representing a time value in the format "hh:mm:ss".
    
    Returns:
      a value of type np.float64.
    """
    if val is np.nan or type(val) == np.float64 or type(val) == float:
        return val
    val = val.strip()
    h, m, s = val.split(":")
    ssm = int(h) * 3600 + int(m) * 60 + int(s)
    if val == "":
        return np.nan

    # pandas doesn't have a NaN int, use floats
    return np.float64(ssm)


def parse_date(val: str) -> datetime.date:
    """
    The function `parse_date` takes a string or a `datetime.date` object as input and returns a
    `datetime.date` object.
    
    Args:
      val (str): The `val` parameter is a string representing a date.
    
    Returns:
      a `datetime.date` object.
    """
    if type(val) == datetime.date:
        return val
    return datetime.datetime.strptime(val, DATE_FORMAT).date()


vparse_date = np.vectorize(parse_date)
vparse_time = np.vectorize(parse_time)


DEFAULT_CRS = "EPSG:4326"


def build_shapes(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    The function takes a pandas DataFrame containing shape points and returns a GeoDataFrame with shape
    IDs and corresponding geometries.
    
    Args:
      df (pd.DataFrame): The parameter `df` is a pandas DataFrame that contains information about
    shapes. It is expected to have the following columns:
    
    Returns:
      a GeoDataFrame object.
    """
    if df.empty:
        return gpd.GeoDataFrame({"shape_id": [], "geometry": []})

    data: Dict[str, List] = {"shape_id": [], "geometry": []}
    for shape_id, shape in df.sort_values("shape_pt_sequence").groupby("shape_id"):
        data["shape_id"].append(shape_id)
        data["geometry"].append(
            LineString(list(zip(shape.shape_pt_lon, shape.shape_pt_lat)))
        )

    return gpd.GeoDataFrame(data, crs=DEFAULT_CRS)


def build_stops(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    The function `build_stops` takes a pandas DataFrame `df` and returns a GeoDataFrame with the same
    data but with a new geometry column created from the `stop_lon` and `stop_lat` columns.
    
    Args:
      df (pd.DataFrame): The parameter `df` is a pandas DataFrame that contains information about stops.
    It is expected to have columns named "stop_lon" and "stop_lat" which represent the longitude and
    latitude coordinates of each stop, respectively. The DataFrame may also contain other columns with
    additional information about the stops.
    
    Returns:
      a GeoDataFrame with the geometry column containing points created from the stop_lon and stop_lat
    columns of the input DataFrame. The stop_lon and stop_lat columns are then dropped from the
    DataFrame before returning the final GeoDataFrame.
    """
    if df.empty:
        return gpd.GeoDataFrame(df, geometry=[], crs=DEFAULT_CRS)

    df = gpd.GeoDataFrame(
        df, crs=DEFAULT_CRS, geometry=gpd.points_from_xy(df.stop_lon, df.stop_lat)
    )

    df.drop(["stop_lon", "stop_lat"], axis=1, inplace=True)

    return gpd.GeoDataFrame(df, crs=DEFAULT_CRS)


def transforms_dict() -> Dict[str, Dict[str, Any]]:
    """
    The function `transforms_dict` returns a dictionary that specifies the required columns and
    converters for each file in a transit data feed.
    
    Returns:
      a dictionary containing information about various text files and their required columns and
    converters.
    """
    return_dict = {
        "agency.txt": {
            "required_columns": ("agency_name", "agency_url", "agency_timezone")
        },
        "calendar.txt": {
            "converters": {
                "start_date": vparse_date,
                "end_date": vparse_date,
                "monday": pd.to_numeric,
                "tuesday": pd.to_numeric,
                "wednesday": pd.to_numeric,
                "thursday": pd.to_numeric,
                "friday": pd.to_numeric,
                "saturday": pd.to_numeric,
                "sunday": pd.to_numeric,
            },
            "required_columns": (
                "service_id",
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
                "start_date",
                "end_date",
            ),
        },
        "calendar_dates.txt": {
            "converters": {
                "date": vparse_date,
                "exception_type": pd.to_numeric,
            },
            "required_columns": ("service_id", "date", "exception_type"),
        },
        "fare_attributes.txt": {
            "converters": {
                "price": pd.to_numeric,
                "payment_method": pd.to_numeric,
                "transfer_duration": pd.to_numeric,
            },
            "required_columns": (
                "fare_id",
                "price",
                "currency_type",
                "payment_method",
                "transfers",
            ),
        },
        "fare_rules.txt": {"required_columns": ("fare_id",)},
        "feed_info.txt": {
            "converters": {
                "feed_start_date": vparse_date,
                "feed_end_date": vparse_date,
            },
            "required_columns": (
                "feed_publisher_name",
                "feed_publisher_url",
                "feed_lang",
            ),
        },
        "frequencies.txt": {
            "converters": {
                "headway_secs": pd.to_numeric,
                "exact_times": pd.to_numeric,
                "start_time": vparse_time,
                "end_time": vparse_time,
            },
            "required_columns": (
                "trip_id",
                "start_time",
                "end_time",
                "headway_secs",
            ),
        },
        "routes.txt": {
            "converters": {"route_type": pd.to_numeric},
            "required_columns": (
                "route_id",
                "route_short_name",
                "route_long_name",
                "route_type",
            ),
        },
        "shapes.txt": {
            "converters": {
                "shape_pt_lat": pd.to_numeric,
                "shape_pt_lon": pd.to_numeric,
                "shape_pt_sequence": pd.to_numeric,
                "shape_dist_traveled": pd.to_numeric,
            },
            "required_columns": (
                "shape_id",
                "shape_pt_lat",
                "shape_pt_lon",
                "shape_pt_sequence",
            ),
            "transformations": [build_shapes],
        },
        "stops.txt": {
            "converters": {
                "stop_lat": pd.to_numeric,
                "stop_lon": pd.to_numeric,
                "location_type": pd.to_numeric,
                "wheelchair_boarding": pd.to_numeric,
                "pickup_type": pd.to_numeric,
                "drop_off_type": pd.to_numeric,
                "shape_dist_traveled": pd.to_numeric,
                "timepoint": pd.to_numeric,
            },
            "required_columns": (
                "stop_id",
                "stop_name",
                "stop_lat",
                "stop_lon",
            ),
            "transformations": [build_stops],
        },
        "stop_times.txt": {
            "converters": {
                "arrival_time": vparse_time,
                "departure_time": vparse_time,
                "pickup_type": pd.to_numeric,
                "shape_dist_traveled": pd.to_numeric,
                "stop_sequence": pd.to_numeric,
                "timepoint": pd.to_numeric,
            },
            "required_columns": (
                "trip_id",
                "arrival_time",
                "departure_time",
                "stop_id",
                "stop_sequence",
            ),
        },
        "transfers.txt": {
            "converters": {
                "transfer_type": pd.to_numeric,
                "min_transfer_time": pd.to_numeric,
            },
            "required_columns": ("from_stop_id", "to_stop_id", "transfer_type"),
        },
        "trips.txt": {
            "converters": {
                "direction_id": pd.to_numeric,
                "wheelchair_accessible": pd.to_numeric,
                "bikes_allowed": pd.to_numeric,
            },
            "required_columns": ("route_id", "service_id", "trip_id"),
        },
    }
    return return_dict
