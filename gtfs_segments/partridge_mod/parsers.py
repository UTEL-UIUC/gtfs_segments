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


# Why 2^18? See https://git.io/vxB2P.
@lru_cache(maxsize=2**18)
def parse_time(val: str) -> np.float32:
    """
    The function `parse_time` takes a string representing a time value in the format "hh:mm:ss" and
    returns the equivalent time in seconds as a numpy int, or returns the input value if it is
    already a numpy int or int.

    Args:
      val (str): The parameter `val` is a string representing a time value in the format "hh:mm:ss".

    Returns:
      a value of type np.float32.
    """
    if isinstance(val, float) or (isinstance(val, float) and np.isnan(val)):  # Corrected handling for np.nan
        return val
    if str(val) == "":
        return np.nan
    val = str(val).strip()

    h, m, s = map(int, val.split(":"))
    return np.float32(h * 3600 + m * 60 + s)


@lru_cache(maxsize=2**18)
def parse_date(val: str) -> datetime.date:
    """
    The function `parse_date` takes a string or a `datetime.date` object as input and returns a
    `datetime.date` object.

    Args:
      val (str): The `val` parameter is a string representing a date.

    Returns:
      a `datetime.date` object.
    """
    if isinstance(val, datetime.date):
        return val
    return datetime.datetime.strptime(val, DATE_FORMAT).date()


@lru_cache(maxsize=2**18)
def parse_float(val: Any) -> float:
    try:
        return float(val)
    except ValueError:
        return np.nan
    
@lru_cache(maxsize=2**18)
def parse_integer(val: Any) -> float:
    try:
        return int(val)
    except ValueError:
        return np.nan


vparse_float = np.vectorize(parse_float)
vparse_int = np.vectorize(parse_integer)
vparse_time = np.vectorize(parse_time)
vparse_date = np.vectorize(parse_date)

DEFAULT_CRS = "EPSG:4326"


def build_shapes(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    The function takes a pandas DataFrame containing shape points and returns a GeoDataFrame with
    shape IDs and corresponding geometries.

    Args:
      df (pd.DataFrame): The parameter `df` is a pandas DataFrame that contains information
    about shapes. It is expected to have the following columns:

    Returns:
      a GeoDataFrame object.
    """
    if df.empty:
        return gpd.GeoDataFrame({"shape_id": [], "geometry": []})

    data: Dict[str, List] = {"shape_id": [], "geometry": []}
    for shape_id, shape in df.sort_values("shape_pt_sequence").groupby("shape_id"):
        data["shape_id"].append(shape_id)
        data["geometry"].append(LineString(list(zip(shape.shape_pt_lon, shape.shape_pt_lat))))

    return gpd.GeoDataFrame(data, crs=DEFAULT_CRS)


def build_stops(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    The function `build_stops` takes a pandas DataFrame `df` and returns a GeoDataFrame with the
    same data but with a new geometry column created from the `stop_lon` and `stop_lat` columns.

    Args:
      df (pd.DataFrame): Pandas DataFrame that contains information about stops. It is expected to
      have columns named "stop_lon" and "stop_lat" which represent the longitude and
      latitude coordinates of each stop, respectively. The DataFrame may also contain other columns
      with additional information about the stops.

    Returns:
    GeoDataFrame with the geometry column containing points created from the stop_lon and stop_lat
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
            "usecols": {
                "agency_name": "str",
                "agency_url": "str",
                "agency_timezone": "str",
                "agency_lang": "str",
                "agency_phone": "int",
                "agency_fare_url": "str",
                "agency_email": "str",
            },
            "required_columns": ("agency_name", "agency_url", "agency_timezone"),
        },
        "calendar.txt": {
            "usecols": {
                "service_id": "str",
                "start_date": "str",
                "end_date": "str",
                "monday": "bool",
                "tuesday": "bool",
                "wednesday": "bool",
                "thursday": "bool",
                "friday": "bool",
                "saturday": "bool",
                "sunday": "bool",
            },
            "converters": {
                "start_date": vparse_date,
                "end_date": vparse_date,
                "monday": vparse_float,
                "tuesday": vparse_float,
                "wednesday": vparse_float,
                "thursday": vparse_float,
                "friday": vparse_float,
                "saturday": vparse_float,
                "sunday": vparse_float,
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
            "usecols": {"service_id": "str", "date": "str", "exception_type": "int8"},
            "converters": {
                "date": vparse_date,
                "exception_type": vparse_float,
            },
            "required_columns": ("service_id", "date", "exception_type"),
        },
        "fare_attributes.txt": {
            "usecols": {
                "fare_id": "str",
                "price": "float",
                "currency_type": "str",
                "payment_method": "str",
                "transfers": "str",
                "transfer_duration": "float16",
            },
            "converters": {
                "price": vparse_float,
                "payment_method": vparse_float,
                "transfer_duration": vparse_float,
            },
            "required_columns": (
                "fare_id",
                "price",
                "currency_type",
                "payment_method",
                "transfers",
            ),
        },
        "fare_rules.txt": {
            "usecols": {
                "fare_id": "str",
                "route_id": "str",
                "origin_id": "str",
                "destination_id": "str",
                "contains_id": "str",
            },
            "required_columns": ("fare_id",),
        },
        "feed_info.txt": {
            "usecols": {
                "feed_publisher_name": "str",
                "feed_publisher_url": "str",
                "feed_lang": "str",
                "feed_start_date": "str",
                "feed_end_date": "str",
            },
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
            "usecols": {
                "trip_id": "str",
                "start_time": "float32",
                "end_time": "float32",
                "headway_secs": "float32",
                "exact_times": "bool",
            },
            "converters": {
                "headway_secs": vparse_float,
                "exact_times": vparse_float,
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
            "usecols": {
                "route_id": "str",
                "route_short_name": "str",
                "route_long_name": "str",
                "route_type": "int8",
                # "route_color": "str",
                # "route_text_color": "str",
            },
            "converters": {
                "route_type": vparse_float,
            },
            "required_columns": (
                "route_id",
                "route_short_name",
                "route_long_name",
                "route_type",
            ),
        },
        "shapes.txt": {
            "usecols": {
                "shape_id": "str",
                "shape_pt_lat": "float32",
                "shape_pt_lon": "float32",
                "shape_pt_sequence": "int16",
                # "shape_dist_traveled":"float32",
            },
            "converters": {
                "shape_pt_lat": vparse_float,
                "shape_pt_lon": vparse_float,
                "shape_pt_sequence": vparse_float,
                # "shape_dist_traveled": vparse_float,
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
            "usecols": {
                "stop_id": "str",
                "stop_name": "str",
                "stop_lat": "float32",
                "stop_lon": "float32",
                # "location_type": "int8",
                # "wheelchair_boarding":"int8",
                # "timepoint":"bool",
            },
            "converters": {
                "stop_lat": vparse_float,
                "stop_lon": vparse_float,
                # "location_type": vparse_float,
                "wheelchair_boarding": vparse_float,
                "timepoint": vparse_float,
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
            "usecols": {
                "trip_id": "str",
                "arrival_time": "float32",
                # "departure_time",
                "stop_id": "str",
                "stop_sequence": vparse_int,
                "pickup_type": vparse_int,
                "drop_off_type": vparse_int,
                # "shape_dist_traveled",
                # "timepoint",
            },
            "converters": {
                "arrival_time": vparse_time,
                "departure_time": vparse_time,
                "pickup_type": vparse_int,
                "drop_off_type": vparse_int,
                # "shape_dist_traveled": vparse_float,
                "stop_sequence": vparse_int,
                # "timepoint": vparse_float,
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
            "usecols": ["from_stop_id", "to_stop_id", "transfer_type", "min_transfer_time"],
            "converters": {
                "transfer_type": vparse_float,
                "min_transfer_time": vparse_float,
            },
            "required_columns": ("from_stop_id", "to_stop_id", "transfer_type"),
        },
        "trips.txt": {
            "usecols": {
                "route_id": "str",
                "shape_id": "str",
                "service_id": "str",
                "trip_id": "str",
                "direction_id": "bool",
                # "wheelchair_accessible": "int8",
                # "bikes_allowed":"int8",
            },
            "converters": {
                "direction_id": vparse_float,
                # "wheelchair_accessible": vparse_float,
                "bikes_allowed": vparse_float,
            },
            "required_columns": ("route_id", "service_id", "trip_id"),
        },
    }
    return return_dict
