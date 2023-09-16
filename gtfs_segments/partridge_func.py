import partridge as ptg
import pandas as pd


def get_bus_feed(path, agency_id=None, threshold=1):
    """
    The `get_bus_feed` function retrieves bus feed data from a specified path, with the option to filter
    by agency name, and returns the busiest date and a GTFS feed object.
    
    Args:
      path: The path parameter is the path to the directory containing the GTFS files. GTFS (General
    Transit Feed Specification) is a standard format for public transportation schedules and related
    geographic data.
      [Optional] agency_id: The `agency_id` parameter is an optional parameter that allows you to filter the bus
    feed data by the agency name. If you provide an `agency_id`, the function will retrieve the bus feed
    for that specific transit agency. If you do not provide an `agency_id`, the function will retrieve
    the
      [Optional] threshold: The threshold parameter is used to filter out service IDs that have a low frequency. It
    is set to a default value of 1, but you can adjust it to a different value if needed. Service IDs
    with a sum of stop times greater than the threshold will be included in the returned bus feed data.
    Defaults to 1
    
    Returns:
      a tuple containing the busiest date and a GTFS feed object. The GTFS feed object contains
    information about routes, stops, stop times, trips, and shapes for a transit agency's schedule.
    """
    _date, bday_service_ids = ptg.read_busiest_date(path)
    all_days_s_ids_df = get_all_days_s_ids(path)
    series = all_days_s_ids_df[bday_service_ids].sum(axis=0) > threshold
    service_ids = series[series].index.values
    route_types = [3, 700, 702, 703, 704, 705]  ##701 is regional
    removed_service_ids = set(bday_service_ids) - set(service_ids)  # set of service IDs eliminated due to low frequency
    if len(removed_service_ids) > 0:
        print("Service IDs eliminated due to low frequency: ", removed_service_ids)
    if agency_id is not None:
        view = {
            "routes.txt": {"route_type": route_types},  # Only bus routes
            "trips.txt": {"service_id": service_ids},  # Busiest day only
            "agency.txt": {
                "agency_id": agency_id
            },  # Eg: 'Société de transport de Montréal
        }
    else:
        view = {
            "routes.txt": {"route_type": route_types},  # Only bus routes
            "trips.txt": {"service_id": service_ids},  # Busiest day only
        }
    feed = ptg.load_geo_feed(path, view=view)
    #     return feed.routes, feed.stops, feed.stop_times, feed.trips, feed.shapes
    return _date, feed


def get_all_days_s_ids(path):
    """
    The function `get_all_days_s_ids` reads dates by service IDs from a given path, creates a DataFrame,
    populates it with the dates and service IDs, and fills missing values with False.

    Args:
      path: The path to the directory containing the GTFS files. GTFS (General Transit Feed
    Specification) is a standard format for public transportation schedules and related geographic data.
    """
    dates_by_service_ids = ptg.read_dates_by_service_ids(path)
    data = dates_by_service_ids
    # Create a DataFrame
    df = pd.DataFrame(columns=sorted(list({col for row in data.keys() for col in row})))

    # Iterate through the data and populate the DataFrame
    for service_ids, dates in data.items():
        for dt in dates:
            df.loc[dt, service_ids] = True

    # Fill missing values with False
    df.fillna(False, inplace=True)
    return df
