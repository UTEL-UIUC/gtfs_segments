import os
from typing import Optional

import pandas as pd

import gtfs_segments.partridge_mod as ptg

from .partridge_mod.gtfs import Feed, parallel_read


def get_bus_feed(
    path: str, agency_id: Optional[str] = None, threshold: Optional[int] = 1, parallel: bool = False
) -> Feed:
    """
    The `get_bus_feed` function retrieves bus feed data from a specified path, with the option to filter
    by agency name, and returns the busiest date and a GTFS feed object.

    Args:
      path (str): The `path` parameter is a string that represents the path to the GTFS file. This file
    contains the bus feed data.
      agency_id (All): The `agency_id` parameter is an optional parameter that allows you to filter the
    bus feed data by the agency name. It is used to specify the ID of the transit agency for which you
    want to retrieve the bus feed data. If you provide an `agency_id`, the function will only return
    data
      threshold (int): The `threshold` parameter is used to filter out service IDs that have a low
    frequency. It is set to a default value of 1, but you can adjust it to a different value if needed.
    Service IDs with a sum of stop times greater than the threshold will be included in the returned
    bus. Defaults to 1

    Returns:
      A tuple containing the busiest date and a GTFS feed object. The GTFS feed object contains
    information about routes, stops, stop times, trips, and shapes for a transit agency's schedule.
    """
    b_day, bday_service_ids = ptg.read_busiest_date(path)
    print("Using the busiest day:", b_day)
    all_days_s_ids_df = get_all_days_s_ids(path)
    series = all_days_s_ids_df[bday_service_ids].sum(axis=0) > threshold
    service_ids = series[series].index.values
    route_types = [3, 700, 702, 703, 704, 705]  # 701 is regional
    # set of service IDs eliminated due to low frequency
    removed_service_ids = set(bday_service_ids) - set(service_ids)
    if len(removed_service_ids) > 0:
        print("Service IDs eliminated due to low frequency:", removed_service_ids)
    if agency_id is not None:
        view = {
            "routes.txt": {"route_type": route_types},  # Only bus routes
            "trips.txt": {"service_id": service_ids},  # Busiest day only
            "agency.txt": {"agency_id": agency_id},  # Eg: 'Société de transport de Montréal
        }
    else:
        view = {
            "routes.txt": {"route_type": route_types},  # Only bus routes
            "trips.txt": {"service_id": service_ids},  # Busiest day only
        }
    feed = ptg.load_geo_feed(path, view=view)
    if parallel:
        num_cores = os.cpu_count()
        print(":: Processing Feed in Parallel :: Number of cores:", num_cores)
        parallel_read(feed)
    return feed


def get_all_days_s_ids(path: str) -> pd.DataFrame:
    """
    Read dates by service IDs from a given path, create a DataFrame, populate it with the dates and
    service IDs, and fill missing values with False.

    Args:
      path: The path to the GTFS file

    Returns:
      A DataFrame containing dates and service IDs.
    """
    dates_by_service_ids = ptg.read_dates_by_service_ids(path)
    data = dates_by_service_ids
    # Create a DataFrame
    data_frame = pd.DataFrame(columns=sorted(list({col for row in data.keys() for col in row})))

    # Iterate through the data and populate the DataFrame
    for service_ids, dates in data.items():
        for date_value in dates:
            data_frame.loc[date_value, list(service_ids)] = True

    # Fill missing values with False
    data_frame.fillna(False, inplace=True)
    return data_frame
