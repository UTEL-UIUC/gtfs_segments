import utm
import numpy as np
import pandas as pd
from .geom_utils import code
from datetime import timedelta
import matplotlib.cm as cm

def get_zone_epsg_from_ls(geom):
    """
    > The function takes a dataframe with a geometry column and returns the EPSG code for the UTM zone
    that contains the geometry
    
    Args:
      stop_df: a dataframe with a geometry column
    
    Returns:
      The EPSG code for the UTM zone that the stop is in.
    """
    lon = geom.coords[0][0]
    lat = geom.coords[0][1]
    zone = utm.from_latlon(lat, lon)
    return code(zone,lat)

def get_sec(time_str):
    """
    It takes a string in the format of hh:mm:ss and returns the number of seconds
    
    Args:
      time_str: The time string to convert to seconds.
    
    Returns:
      the total number of seconds in the time string.
    """
    """Get seconds from time."""
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)

def get_trips_len(df,time):
    """
    > It returns the number of trips that are active at a given time
    
    Args:
      df: the dataframe of trips
      time: the time you want to get the number of trips for
    
    Returns:
      The number of trips that are active at a given time.
    """
    return len(df[(df.start_time <= time) & (df.end_time >= time)].trip_id.unique())

def get_trips(df,time):
    """
    > Return all trips that start before the given time and end after the given time
    
    Args:
      df: the dataframe containing the trips
      time: the time you want to get the trips for
    
    Returns:
      A dataframe of all trips that start before the time and end after the time.
    """
    return df[(df.start_time <= time) & (df.end_time >= time)]

def get_peak_time(df):
    """
    It takes a dataframe and returns the number of buses and the time at which the most buses are
    running
    
    Args:
      df: the dataframe
    
    Returns:
      The number of buses and the time of the peak
    """
    best = 0 
    peak_time = 0
    start_time = int(min(df.start_time))
    end_time = int(max(df.end_time))
    for time in range(start_time,end_time,60):
        no_buses = get_trips_len(df,time)
        if no_buses >= best:
            peak_time = str(timedelta(seconds = time))
            best = no_buses
    return [best,peak_time]

def get_service_length(df):
    """
    It takes a GTFS feed and a route_id and returns a dictionary of route statistics
    
    Args:
      df: the dataframe containing the stop times
    """
    df = df.sort_values(['stop_sequence'])
    if df.iloc[0]['pickup_type'] == 1:
        sp_dist = df.iloc[1]['shape_dist_traveled']
        df.shape_dist_traveled = df.shape_dist_traveled - sp_dist
        df.drop(index=df.iloc[0, :].index.tolist(), inplace=True, axis=0)
    return df.shape_dist_traveled.max()

def get_average_route_lengths(df):
    """
    For each route, get the peak time, then get the trips that occur at that time, then get the average
    length of those trips
    
    Args:
      df: the dataframe
    
    Returns:
      A dictionary with route_id as key and average route length as value
    """
    route_lengths = {}
    for route_id in df.route_id.unique():
        route_grp = get_route_grp(df,route_id)
        peak_time = get_peak_time(route_grp)[1]
        route_grp = get_trips(route_grp,get_sec(peak_time))
        all_lengths = []
        for trip_id in route_grp.trip_id.unique():
            df_trip = df[df.trip_id == trip_id]
            length = get_service_length(df_trip)
            all_lengths.append(all_lengths)
        route_lengths[route_id] = np.mean(all_lengths)
    return route_lengths

def get_route_grp(route_df):
    """
    It takes a dataframe of route information and returns a dataframe of route information with the
    first and last stop times for each trip
    
    Args:
      route_df: The dataframe containing the route information
    
    Returns:
      A dataframe with the first and last stop of each trip.
    """
    route_df = route_df.sort_values(['stop_sequence'])
    route_df_grp = route_df.groupby(['trip_id']).first()
    route_df_grp['start_time'] = route_df.groupby(['trip_id']).first().arrival_time
    route_df_grp['end_time'] = route_df.groupby(['trip_id']).last().arrival_time
    route_df_grp = route_df_grp.reset_index()
    col_filter = np.array(['trip_id','route_id','direction_id','start_time','end_time','pickup_type','drop_off_type','shape_dist_traveled'])
    col_subset = col_filter[np.in1d(col_filter,route_df_grp.columns)]
    return route_df_grp[col_subset]

def get_all_peak_times(df_dir):
    """
    It takes a dataframe of bus trips and returns the peak number of buses and the time of the peak
    
    Args:
      df: the dataframe of the route you want to get the peak times for
    
    Returns:
      A dictionary with the peak number of buses in each direction, and the peak times.
    """
    best = 0
    peak_times = []
    df = get_route_grp(df_dir)
    start_time = int(min(df.start_time))
    end_time = int(max(df.end_time))
    for time in range(start_time,end_time,60):
        trips_df = get_trips(df,time)
        no_buses = get_trips_len(df,time)
        if no_buses == best:
            peak_times.append(time)
        if no_buses > best:
            peak_times = [time]
    peak_time_condensed = np.array([str(timedelta(seconds = peak_times[0]))],dtype='object')
    for i,time in enumerate(peak_times):
        if i > 0:
            if (time - peak_times[i-1]) != 60:
                time = str(timedelta(seconds = time))
#                 peak_time_condensed[-1] =  peak_time_condensed[-1].split('-')[0] + '-' + str(time)
#             else:
                peak_time_condensed[-1] =  str(peak_time_condensed[-1]) + '-' + str(timedelta(seconds = peak_times[i-1]))
                peak_time_condensed = np.append(peak_time_condensed,str(time))
            else:
                if i == len(peak_times) -1:
                    peak_time_condensed[-1] =  str(peak_time_condensed[-1] + '-' + str(timedelta(seconds = peak_times[i])))
    return {"peak_buses":peak_time_condensed}

def get_cmap_string(palette, domain):
    """
    It takes a list of colors and a list of values, and returns a function that maps each value to its
    corresponding color
    
    Args:
      palette: the name of the matplotlib palette you want to use.
      domain: the unique values in the column you want to color
    
    Returns:
      A function that takes in a value and returns a color.
    """
    domain_unique = np.unique(domain)
    hash_table = {key: i_str for i_str, key in enumerate(domain_unique)}
    mpl_cmap = cm.get_cmap(palette, lut=len(domain_unique))

    def cmap_out(X, **kwargs):
        return mpl_cmap(hash_table[X], **kwargs)

    return cmap_out

def get_average_headway(df_dir):
    """
    For each route, find the shape with the most trips, then find the stop with the most trips on that
    shape, then find the average headway for that stop
    
    Args:
      df_route: a dataframe containing the route you want to analyze
    
    Returns:
      A dictionary with the average headway for each direction.
    """
    hdw_0 = np.array([0])
    if len(df_dir) > 1:
        shape_0 = df_dir.groupby('shape_id').count().trip_id.idxmax()
        df_dir = df_dir[df_dir.shape_id == shape_0]
        stop_id0 = df_dir.stop_id.unique()[0]
        hdw_0 = df_dir[df_dir.stop_id == stop_id0].sort_values(['arrival_time']).arrival_time.astype(int).diff()
    return {'headway' : np.round(hdw_0[hdw_0 <= 3*60*60].mean()/3600,2)}

def get_average_speed(df_dir, route_dict):
    """
    It takes a dataframe of a route and a dictionary of route information and returns a dictionary of
    average speeds for each direction
    
    Args:
      df_route: a dataframe of the route
      route_dict: a dictionary containing the route length and total time for each direction
    
    Returns:
      A dictionary with the average speed for each direction.
    """
    ret_dict = {}
    if len(df_dir) > 1:
        ret_dict['average speed'] = np.round(route_dict['route length'] / route_dict['total time'],2)
    return ret_dict

def get_route_time(df_dir):
    """
    For each route, find the shape_id that has the most trips, then find the trip_id that has that
    shape_id, then find the arrival_time of the first and last stop of that trip_id, then subtract the
    two to get the total time of the route
    
    Args:
      df_route: a dataframe of a route
    
    Returns:
      A dictionary with the total time for each direction.
    """
    if len(df_dir) > 1:
        shape_0 =df_dir.groupby('shape_id').count().trip_id.idxmax()
        trip_0 = df_dir[df_dir.trip_id == df_dir[df_dir.shape_id == shape_0].trip_id.unique()[0]]
        time_0 = trip_0.arrival_time.max() - trip_0.arrival_time.min()
    return {'total time' : np.round(time_0/3600,2) if time_0 !=0 else 0}

def get_bus_spacing(df_route,route_dict):
    """
    It takes a dataframe of a route and a dictionary of route information and returns a dictionary of
    the minimum spacing between buses on the route
    
    Args:
      df_route: a dataframe of all the trips for a given route
      route_dict: a dictionary containing the route length and number of buses for each direction
    
    Returns:
      A dictionary with the keys 'spacing dir 0' and 'spacing dir 1'
    """
    return {'spacing' : np.round(route_dict['route length']/route_dict['n bus avg'],3)}
  
def average_active_buses(df_dir):
    n_buses = []
    df = get_route_grp(df_dir)
    start_time = int(min(df.start_time))
    end_time = int(max(df.end_time))
    for time in range(start_time,end_time,5*60):
        no_buses = get_trips_len(df,time)
        n_buses.append(no_buses)
    n_buses = np.array(n_buses)
    return {'n bus avg':np.round(np.mean(n_buses[n_buses > 0]),3)}

def get_stop_spacing(df_dir,route_dict):
    """
    For each route, find the shape with the most trips, and then find the number of stops on that trip.
    Then divide the route length by the number of stops to get the stop spacing
    
    Args:
      df_route: a dataframe of the stops for a given route
      route_dict: a dictionary containing the route_id, route length in each direction, and the number
    of trips in each direction
    
    Returns:
      A dictionary with the stop spacing for each direction.
    """
    spc_0 = 0
    spc_1 = 0
    if len(df_dir) > 1:
        shape_0 =df_dir.groupby('shape_id').count().trip_id.idxmax()
        n_stops = len(df_dir[df_dir.trip_id == df_dir[df_dir.shape_id == shape_0].trip_id.unique()[0]])
        spc_0 = route_dict['route length']/n_stops
    return {'stop spacing' : np.round(spc_0,2) if spc_0 !=0 else 0}

def get_route_lens(df_dir, df_shapes):
    """
    It takes a dataframe of trips for a given route and a dataframe of shapes for a given route, and
    returns a dictionary with the length of the route in each direction
    
    Args:
      df_route: a dataframe of the routes.txt file
      df_shapes: the shapes dataframe
    
    Returns:
      A dictionary with the route lengths for each direction.
    """
    epsg_zone = get_zone_epsg_from_ls(df_shapes.iloc[0]['geometry'])
    len_0 = 0
    if len(df_dir) > 1:
        shape_0 = df_dir.groupby('shape_id').count().trip_id.idxmax()
        len_0 =  df_shapes.loc[df_shapes.shape_id == shape_0].to_crs(epsg_zone).geometry.length.iloc[0]
    return {'route length' : np.round(len_0/1000,2)}

def get_route_stats(feed, peak_time = False):
    """
    It takes a GTFS feed and a route_id and returns a dataframe with the following columns:
    
    - route_id
    - route_length
    - route_time
    - average_headway
    - peak_times
    - average_speed
    - min_spacing
    - stop_spacing
    
    The function is a bit long, but it's not too complicated. 
    
    The first thing it does is merge the stop_times and trips tables. This is necessary because the
    stop_times table doesn't have the route_id column. 
    
    The next thing it does is create an empty dictionary called route_dict. This will be used to store
    the results of the analysis. 
    
    For each route, it creates a new dictionary called ret_dict. This will be used to store the results
    of the analysis for the current
    
    Args:
      feed: the GTFS feed object
      route_id: The route_id of the route you want to analyze
    
    Returns:
      A dataframe with the route_id as the first column and the rest columns are the stats for the route.
    """
    df_merge = feed.stop_times.merge(feed.trips, how='left',on='trip_id')
    df_shapes = feed.shapes
    route_list = []
    for route in df_merge.route_id.unique():
      df_route = df_merge[df_merge.route_id == route]
      for direction in  df_route.direction_id.unique():
        df_dir = df_route[df_route.direction_id == direction]
        ret_dict = {}
        ret_dict['route'] = route
        ret_dict['direction'] = direction
        ret_dict.update(get_route_lens(df_dir,df_shapes))
        ret_dict.update(get_route_time(df_dir))
        ret_dict.update(get_average_headway(df_dir))
        ret_dict.update(get_average_speed(df_dir,ret_dict))
        ret_dict.update(average_active_buses(df_dir))
        ret_dict.update(get_bus_spacing(df_dir,ret_dict))
        ret_dict.update(get_stop_spacing(df_dir,ret_dict))
        if peak_time:
          ret_dict.update(get_all_peak_times(df_dir))
  
        route_list.append(ret_dict)
    df = pd.DataFrame.from_records(route_list)
    return df.reset_index(drop =True)
