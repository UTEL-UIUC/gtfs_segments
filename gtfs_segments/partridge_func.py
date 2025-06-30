import os
from datetime import datetime, date as date_type
from typing import Optional, Union, List

import pandas as pd

import gtfs_segments.partridge_mod as ptg

# Set pandas option to handle future behavior of fillna
pd.set_option('future.no_silent_downcasting', True)

from .partridge_mod.gtfs import Feed, parallel_read


def get_bus_feed(
    path: str, 
    agency_id: Optional[str] = None, 
    threshold: Optional[int] = 1, 
    parallel: bool = False,
    date: Optional[Union[str, date_type, List[Union[str, date_type]]]] = None,
    skip_invalid_dates: bool = False
) -> Feed:
    """
    The `get_bus_feed` function retrieves bus feed data from a specified path, with the option to filter
    by agency name and date(s), and returns a GTFS feed object.

    Args:
      path (str): The `path` parameter is a string that represents the path to the GTFS file.
      agency_id (Optional[str]): Filter by specific agency ID.
      threshold (int): Filter out service IDs with low frequency. Defaults to 1.
      parallel (bool): If True, process the feed in parallel. Defaults to False.
      date (Optional[Union[str, date_type, List[Union[str, date_type]]]]): Specific date(s) to restrict 
        services to. Can be:
        - Single date string in YYYYMMDD format (e.g., '20230315')  
        - Single datetime.date object
        - List of date strings and/or datetime.date objects
        If None, defaults to the busiest date of the feed.
      skip_invalid_dates (bool): If True and a list of dates is provided, skip invalid dates 
        and continue with valid ones. If False, raise an error for any invalid date. Defaults to False.

    Returns:
      A GTFS feed object containing route and schedule information.
      
    Raises:
      ValueError: If date format is invalid, date not found in calendar, or no services available.
    """
    # Get all days service IDs for validation and threshold filtering
    all_days_s_ids_df = get_all_days_s_ids(path)
    
    if date is not None:
        # Handle single date or list of dates
        if isinstance(date, (str, datetime, date_type)):
            # Single date case
            dates_to_process = [date]
        elif isinstance(date, list):
            # List of dates case
            if not date:  # Empty list
                raise ValueError("Date list cannot be empty")
            dates_to_process = date
        else:
            raise ValueError(f"Invalid date type: {type(date)}. Must be str, date, or list of str/date")
        
        # Parse and validate all dates
        target_dates = []
        invalid_dates = []
        
        for single_date in dates_to_process:
            try:
                # Parse string date if needed
                if isinstance(single_date, str):
                    try:
                        parsed_date = datetime.strptime(single_date, "%Y%m%d").date()
                    except ValueError:
                        raise ValueError(f"Date string '{single_date}' must be in YYYYMMDD format (e.g., '20230315')")
                elif isinstance(single_date, datetime):
                    parsed_date = single_date.date()
                elif isinstance(single_date, date_type):
                    parsed_date = single_date
                else:
                    raise ValueError(f"Invalid date type in list: {type(single_date)}")
                    
                # Validate date exists in GTFS calendar
                if parsed_date not in all_days_s_ids_df.index:
                    available_dates = sorted(all_days_s_ids_df.index)
                    error_msg = (
                        f"Date {parsed_date} not found in GTFS service calendar. "
                        f"Available date range: {available_dates[0]} to {available_dates[-1]}"
                    )
                    if skip_invalid_dates:
                        invalid_dates.append((single_date, error_msg))
                        continue
                    else:
                        raise ValueError(error_msg)
                
                target_dates.append(parsed_date)
                
            except ValueError as e:
                if skip_invalid_dates:
                    invalid_dates.append((single_date, str(e)))
                    continue
                else:
                    raise e
        
        # Check if we have any valid dates
        if not target_dates:
            raise ValueError("No valid dates found in the provided date list")
        
        # Report invalid dates if any were skipped
        if invalid_dates and skip_invalid_dates:
            print(f"Warning: Skipped {len(invalid_dates)} invalid dates:")
            for invalid_date, error_msg in invalid_dates:
                print(f"  - {invalid_date}: {error_msg}")
        
        # Collect all service IDs from all target dates
        all_service_ids = set()
        for target_date in target_dates:
            date_service_ids = all_days_s_ids_df.loc[target_date][all_days_s_ids_df.loc[target_date] > 0].index.tolist()
            all_service_ids.update(date_service_ids)
        
        bday_service_ids = list(all_service_ids)
        
        # Report dates being used
        if len(target_dates) == 1:
            print(f"Using requested date: {target_dates[0]}")
        else:
            print(f"Using requested dates: {sorted(target_dates)} (total: {len(target_dates)} dates)")
        
        # Check if any services are running on the requested dates
        if not bday_service_ids:
            dates_str = ', '.join(str(d) for d in sorted(target_dates))
            raise ValueError(f"No services are running on the requested date(s): {dates_str}")
            
    else:
        # Fallback to the busiest date
        target_date, bday_service_ids = ptg.read_busiest_date(path)
        print(f"Using the busiest day: {target_date}")
    
    # Filter service_ids by threshold frequency across all days
    series = all_days_s_ids_df[bday_service_ids].sum(axis=0) > threshold
    service_ids = series[series].index.values.tolist()
    
    # Report eliminated low-frequency service IDs
    removed_service_ids = set(bday_service_ids) - set(service_ids)
    if len(removed_service_ids) > 0:
        print("Service IDs eliminated due to low frequency:", removed_service_ids)
    
    # Check if any services remain after filtering
    if not service_ids:
        if 'target_dates' in locals():
            dates_str = ', '.join(str(d) for d in sorted(target_dates))
        else:
            dates_str = str(target_date)
        raise ValueError(f"No services meet the threshold requirement ({threshold}) for date(s) {dates_str}")
    
    # Define bus route types
    route_types = [3, 700, 702, 703, 704, 705]  # 701 is regional
    # Build view filter
    if agency_id is not None:
        view = {
            "routes.txt": {"route_type": route_types},  # Only bus routes
            "trips.txt": {"service_id": service_ids},  # Specified/busiest day only
            "agency.txt": {"agency_id": agency_id},  # Specific agency
        }
    else:
        view = {
            "routes.txt": {"route_type": route_types},  # Only bus routes
            "trips.txt": {"service_id": service_ids},  # Specified/busiest day only
        }
    
    # Load the feed
    feed = ptg.load_geo_feed(path, view=view)
    
    if parallel:
        num_cores = os.cpu_count()
        print(f":: Processing Feed in Parallel :: Number of cores: {num_cores}")
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
    # Create a DataFrame with explicit boolean dtype
    columns = sorted(list({col for row in data.keys() for col in row}))
    data_frame = pd.DataFrame(columns=columns, dtype=bool)

    # Iterate through the data and populate the DataFrame
    for service_ids, dates in data.items():
        for date_value in dates:
            data_frame.loc[date_value, list(service_ids)] = True

    # Fill missing values with False - now using explicit dtype
    data_frame = data_frame.fillna(False)
    return data_frame
