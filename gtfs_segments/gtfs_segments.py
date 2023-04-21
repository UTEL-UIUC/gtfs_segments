import geopandas as gpd
from .partridge_func import get_bus_feed
from .geom_utils import *
from .utils import *
from .mobility import *


def merge_trip_geom(trip_df,shape_df):
    """
    It takes a dataframe of trips and a dataframe of shapes, and returns a geodataframe of trips with
    the geometry of the shapes
    
    Args:
      trip_df: a dataframe of trips
      shape_df: a GeoDataFrame of the shapes.txt file
    
    Returns:
      A GeoDataFrame
    """
    ## `direction_id` and `shape_id` are optional
    if ('direction_id' in trip_df.columns):
    ## Check is direction_ids are listed as null
        if trip_df['direction_id'].isnull().sum() == 0:
            grp = trip_df.groupby(['route_id','shape_id','direction_id'])
        else:
            grp = trip_df.groupby(['route_id','shape_id'])
    else:
        grp = trip_df.groupby(['route_id','shape_id'])
    trip_df = grp.first().reset_index()
    trip_df['traversals'] = grp.count().reset_index(drop=True)['trip_id']
    subset_list = np.array(['route_id','trip_id','shape_id','service_id','direction_id','traversals'])
    col_subset = subset_list[np.in1d(subset_list,trip_df.columns)]
    trip_df = trip_df[col_subset]
    trip_df = trip_df.dropna(how='all', axis=1)
    trip_df = shape_df.merge(trip_df, on='shape_id',how='left')
    return make_gdf(trip_df)

def make_segments_unique(df):
    """
    For each route_id and segment_id combination, if there are more than one unique distance values,
    then split the segment_id into three parts, and add a number to the end of the segment_id
    
    Args:
      df: the dataframe
    
    Returns:
      A dataframe with unique segment_ids
    """
    
    grp_filter = df.groupby(['route_id','segment_id']).filter(lambda row : row['distance'].round().nunique() > 1)
    grp_dict = grp_filter.groupby(['route_id','segment_id']).groups
    for key in grp_dict.keys():
        inds = grp_dict[key]
        for i,index in enumerate(inds):
            if i != 0:
                seg_split = key[1].split('-')
                df.loc[index,'segment_id'] = seg_split[0]+'-'+seg_split[1]+'-'+str(i+1)
    grp_again = df.groupby(['route_id','segment_id'])
    df = grp_again.first().reset_index()
    df['traversals'] = grp_again['traversals'].sum().values
    return df

def filter_stop_df(stop_df,trip_ids):
    """
    It takes a dataframe of stops and a list of trip IDs and returns a dataframe of stops that are in
    the list of trip IDs
    
    Args:
      stop_df: the dataframe of all stops
      trip_ids: a list of trip_ids that you want to filter the stop_df by
    
    Returns:
      A dataframe with the trip_id, s top_id, and stop_sequence for the trips in the trip_ids list.
    """
    stop_df = stop_df.sort_values(['trip_id','stop_sequence']).reset_index(drop=True)
    stop_df['main_index'] = stop_df.index
    stop_df_grp = stop_df.groupby('trip_id')
    drop_inds = []
    ## To eliminate deadheads
    if "pickup_type" in stop_df.columns:
      grp_f = stop_df_grp.first()
      drop_inds.append(grp_f.loc[grp_f['pickup_type'] == 1,'main_index'])
    if "drop_off_type" in stop_df.columns:
      grp_l = stop_df_grp.last()
      drop_inds.append(grp_l.loc[grp_f['drop_off_type'] == 1,'main_index'])
    stop_df = stop_df[~stop_df['main_index'].isin(drop_inds)].reset_index(drop=True)
    stop_df = stop_df[['trip_id','stop_id','stop_sequence']]
    stop_df = stop_df[stop_df.trip_id.isin(trip_ids)].reset_index(drop=True)
    stop_df = stop_df.sort_values(['trip_id','stop_sequence']).reset_index(drop=True)
    return stop_df

def merge_stop_geom(stop_df,stop_loc_df):      
    """
    > Merge the stop_loc_df with the stop_df, and then convert the result to a GeoDataFrame
    
    Args:
      stop_df: a dataframe of stops
      stop_loc_df: a GeoDataFrame of the stops
    
    Returns:
      A GeoDataFrame
    """
    stop_df['start'] = stop_df.copy().merge(stop_loc_df,how='left',on='stop_id')['geometry']
    stop_df = gpd.GeoDataFrame(stop_df,geometry='start')
    return make_gdf(stop_df)
  
def process_feed_stops(feed,max_spacing = None):
    """
    This function processes feed stops by merging trip and stop dataframes, calculating distances
    between stops, and returning a geodataframe.
    
    Args:
      feed: a GTFS feed object containing information about transit routes, stops, and schedules.
      max_spacing: max_spacing is an optional parameter that can be passed to the function
    process_feed_stops. It is used to filter out stops that are too close to each other. If two stops
    are closer than max_spacing, only one of them will be included in the output. If max_spacing is not
    provided,
    
    Returns:
      A GeoDataFrame containing information about the stops in the feed, including their location, the
    trips they are associated with, and the distance between stops. The function also calculates the
    mean distance between stops and can optionally filter stops based on a maximum spacing parameter.
    """
    trip_df = merge_trip_geom(feed.trips,feed.shapes)
    trip_ids = trip_df.trip_id.unique()
    stop_df = filter_stop_df(feed.stop_times,trip_ids)
    stop_loc_df = feed.stops[['stop_id','geometry']]
    stop_df = merge_stop_geom(stop_df,stop_loc_df)    
    stop_df = stop_df.merge(trip_df,on='trip_id',how='left')
    stops = stop_df.groupby('shape_id').count().reset_index()['geometry']
    stop_df = stop_df.groupby('shape_id').first().reset_index()
    stop_df['n_stops'] = stops
    epsg_zone = get_zone_epsg(stop_df)
    stop_df = make_gdf(stop_df)    
    stop_df['distance'] = stop_df.set_geometry('geometry').to_crs(epsg_zone).geometry.length
    stop_df['mean_distance'] = stop_df['distance']/stop_df['n_stops']
    return make_gdf(stop_df)
    
def create_segments(stop_df):
    """
    This function creates segments between stops based on their proximity and returns a GeoDataFrame.
    
    Args:
      stop_df: A pandas DataFrame containing information about stops on a transit network, including
    their stop_id, coordinates, and trip_id.
    
    Returns:
      a GeoDataFrame with segments created from the input stop_df.
    """
    stop_df = nearest_points(stop_df)
    stop_df = stop_df.rename({'stop_id':'stop_id1'},axis =1)
    grp = pd.DataFrame(stop_df).groupby('trip_id',group_keys= False).shift(-1).reset_index(drop=True)
    stop_df[['stop_id2','end','snap_end_id']] = grp[['stop_id1','start','snap_start_id']]
    stop_df['segment_id'] = stop_df.apply(lambda row: str(row['stop_id1']) +'-'+ str(row['stop_id2'])+'-1',axis =1)
    stop_df = stop_df.dropna().reset_index(drop=True)
    stop_df.snap_end_id = stop_df.snap_end_id.astype(int)
    stop_df = stop_df[stop_df['snap_end_id'] > stop_df['snap_start_id']].reset_index(drop=True)
    stop_df['geometry'] = stop_df.apply(lambda row: LineString(row['geometry'].coords[row['snap_start_id']:row['snap_end_id']+1]),axis=1)
    return make_gdf(stop_df)

def process_feed_stops(feed,max_spacing = None):
    """
    It takes a GTFS feed, merges the trip and shape data, filters the stop_times data to only include
    the trips that are in the feed, merges the stop_times data with the stop data, creates a segment for
    each stop pair, gets the EPSG zone for the feed, creates a GeoDataFrame, and calculates the length
    of each segment
    
    Args:
      feed: a GTFS feed object
      max_spacing: the maximum distance between stops in meters. If a stop is more than this distance
    from the previous stop, it will be dropped.
    
    Returns:
      A GeoDataFrame with the following columns:
    """
    trip_df = merge_trip_geom(feed.trips,feed.shapes)
    trip_ids = trip_df.trip_id.unique()
    stop_df = filter_stop_df(feed.stop_times,trip_ids)
    stop_loc_df = feed.stops[['stop_id','geometry']]
    stop_df = merge_stop_geom(stop_df,stop_loc_df)    
    stop_df = stop_df.merge(trip_df,on='trip_id',how='left')
    stops = stop_df.groupby('shape_id').count().reset_index()['geometry']
    stop_df = stop_df.groupby('shape_id').first().reset_index()
    stop_df['n_stops'] = stops
    epsg_zone = get_zone_epsg(stop_df)
    stop_df = make_gdf(stop_df)    
    stop_df['distance'] = stop_df.set_geometry('geometry').to_crs(epsg_zone).geometry.length
    stop_df['mean_distance'] = stop_df['distance']/stop_df['n_stops']
    return make_gdf(stop_df)
    
def process_feed(feed,max_spacing = None):
    ## Set a Spatial Resolution and increase the resolution of the shapes
    shapes = ret_high_res_shape(feed.shapes,spat_res = 5)
    trip_df = merge_trip_geom(feed.trips,shapes)
    trip_ids = trip_df.trip_id.unique()
    stop_df = filter_stop_df(feed.stop_times,trip_ids)
    stop_loc_df = feed.stops[['stop_id','geometry']]
    stop_df = merge_stop_geom(stop_df,stop_loc_df)    
    stop_df = stop_df.merge(trip_df,on='trip_id',how='left')
    stop_df = create_segments(stop_df)
    epsg_zone = get_zone_epsg(stop_df)
    stop_df = make_gdf(stop_df)    
    stop_df['distance'] = stop_df.set_geometry('geometry').to_crs(epsg_zone).geometry.length
    stop_df['distance'] =  stop_df['distance'].round(2) # round to 2 decimal places
    stop_df = make_segments_unique(stop_df)
    subset_list = np.array(['segment_id','route_id','direction_id','trip_id','traversals','distance','stop_id1','stop_id2','geometry'])
    col_subset = subset_list[np.in1d(subset_list,stop_df.columns)]
    stop_df = stop_df[col_subset]
    if max_spacing != None:
        stop_df = stop_df[stop_df['distance'] <= max_spacing]
    return make_gdf(stop_df)

def inspect_feed(feed):
    """
    It checks to see if the feed has any bus routes and if it has a `shape_id` column in the `trips`
    table
    
    Args:
      feed: The feed object that you want to inspect.
    
    Returns:
      A message
    """
    message = True
    if len(feed.stop_times) == 0:
        message = 'No Bus Routes in ' 
    if not "shape_id" in feed.trips.columns:
        message = "Missing `shape_id` column in "
    return message 

def get_gtfs_segments(path,max_spacing = None):
    """
    > It reads a GTFS file, and returns a list of segments
    
    Args:
      path: the path to the GTFS file
    
    Returns:
      A list of segments.
    """
    bday ,feed = get_bus_feed(path)
    return process_feed(feed,max_spacing)

def pipeline_gtfs(filename,url,bounds,max_spacing):
    """
    It takes a GTFS file, downloads it, reads it, processes it, and then outputs a bunch of files. 
    
    Let's go through the function step by step. 
    
    First, we define the function and give it a name. We also give it a few arguments: 
    
    - filename: the name of the file we want to save the output to. 
    - url: the url of the GTFS file we want to download. 
    - bounds: the bounding box of the area we want to analyze. 
    - max_spacing: the maximum spacing we want to analyze. 
    
    We then create a folder to save the output to. 
    
    Next, we download the GTFS file and save it to the folder we just created. 
    
    Then, we read the GTFS file using the `get_bus_feed` function. 
    
    Args:
      filename: the name of the file you want to save the output to
      url: the url of the GTFS file
      bounds: the bounding box of the area you want to analyze. This is in the format
    [min_lat,min_lon,max_lat,max_lon]
      max_spacing: The maximum distance between stops that you want to consider.
    
    Returns:
      a string with the name of the file that was processed.
    """
    folder_path  = os.path.join('output_files',filename)
    gtfs_file_loc = download_write_file(url,folder_path)
    
    ## read file using GTFS Fucntions
    busisest_day, feed = get_bus_feed(gtfs_file_loc)
    ## Remove Null entries
    message =  inspect_feed(feed)
    if message != True:
        return failed_pipeline(message,filename,folder_path)
    
    df = process_feed(feed)
    df_sub = df[df['distance']  < 3000].copy().reset_index(drop=True)
    if len(df_sub) == 0:
        return failed_pipeline('Only Long Bus Routes in ',filename,folder_path)
    ## Output files and Stats
    summary_stats_mobility(df,folder_path,filename,busisest_day,url,bounds,max_spacing,export=True)

    plot_hist(df,file_path = os.path.join(folder_path,'spacings.png'),title = filename.split(".")[0],max_spacing = max_spacing,save_fig=True)
    export_segments(df,os.path.join(folder_path,'geojson'), output_format ='geojson',geometry = True)
    export_segments(df,os.path.join(folder_path,'spacings_with_geometry'), output_format ='csv',geometry = True)
    export_segments(df,os.path.join(folder_path,'spacings'), output_format ='csv',geometry = False)
    return "Success for "+filename