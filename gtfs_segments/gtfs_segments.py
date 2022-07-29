import geopandas as gpd
from .partridge_func import ptg_read_file
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
    
#     trip_df = trip_df.set_crs(epsg=4326,allow_override=True)
    return make_gdf(trip_df)

def create_segments(stop_df):
    """
    It takes a dataframe of stops and returns a dataframe of segments
    
    Args:
      stop_df: a dataframe with the following columns:
    
    Returns:
      A dataframe with the following columns:
    """
    stop_df = stop_df.rename({'stop_id':'stop_id1'},axis =1)
    start_wkts = stop_df.apply(lambda row: nearest_snap(row['geometry'],row['start']), axis = 1)
    stop_df['start'] = gpd.GeoSeries.from_wkt(start_wkts)
    grp = stop_df.groupby('trip_id').apply(lambda df: df.shift(-1)).reset_index(drop=True)
    stop_df[['stop_id2','end']] = grp[['stop_id1','start']]
    stop_df = stop_df.dropna().reset_index(drop=True)
    stop_df['segment_id'] = stop_df.apply(lambda row: str(row['stop_id1']) +'-'+ str(row['stop_id2']),axis =1)
    # stop_df['segment_id'] = stop_df.apply(lambda row: str(row['stop_id1']) +'-'+ str(row['stop_id2'])+'-'+ str(row['shape_id']),axis =1)
    stop_df['snapped_start_id'] = stop_df.apply(lambda row: row['start'].within(row['geometry']), axis = 1)
    stop_df['snapped_end_id'] = stop_df.apply(lambda row: row['end'].within(row['geometry']), axis = 1)
    split_routes = stop_df.apply(lambda row: split_route(row),axis = 1)
    stop_df['geometry'] = gpd.GeoSeries.from_wkt(split_routes)
    return stop_df

def filter_stop_df(stop_df,trip_ids):
    """
    It takes a dataframe of stops and a list of trip IDs and returns a dataframe of stops that are in
    the list of trip IDs
    
    Args:
      stop_df: the dataframe of all stops
      trip_ids: a list of trip_ids that you want to filter the stop_df by
    
    Returns:
      A dataframe with the trip_id, stop_id, and stop_sequence for the trips in the trip_ids list.
    """
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
    
def process_feed(feed):
    """
    It takes a GTFS feed, merges the trip and shape data, filters the stop_times data to only include
    the trips that are in the feed, merges the stop_times data with the stop data, creates a segment for
    each stop pair, gets the EPSG zone for the feed, creates a GeoDataFrame, and calculates the length
    of each segment
    
    Args:
      feed: a GTFS feed object
    
    Returns:
      A GeoDataFrame with the following columns:
    """
    trip_df = merge_trip_geom(feed.trips,feed.shapes)
    trip_ids = trip_df.trip_id.unique()
    stop_df = filter_stop_df(feed.stop_times,trip_ids)
    stop_loc_df = feed.stops[['stop_id','geometry']]
    stop_df = merge_stop_geom(stop_df,stop_loc_df)    
    stop_df = stop_df.merge(trip_df,on='trip_id',how='left')
    stop_df = create_segments(stop_df)
    # return stop_df
    epsg_zone = get_zone_epsg(stop_df)
    subset_list = np.array(['route_id','shape_id','service_id','segment_id','stop_id1','stop_id2','direction_id','traversals','geometry'])
    col_subset = subset_list[np.in1d(subset_list,stop_df.columns)]
    stop_df = stop_df[col_subset]
    stop_df = make_gdf(stop_df)    
    stop_df['distance'] = stop_df.to_crs(epsg_zone).geometry.length
    return stop_df

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

def get_gtfs_segments(path):
    """
    > It reads a GTFS file, and returns a list of segments
    
    Args:
      path: the path to the GTFS file
    
    Returns:
      A list of segments.
    """
    bday ,feed = ptg_read_file(path)
    return process_feed(feed)

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
    
    Then, we read the GTFS file using the `ptg_read_file` function. 
    
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
    busisest_day, feed = ptg_read_file(gtfs_file_loc)
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