from tracemalloc import stop
import geopandas as gpd
from .partridge_func import ptg_read_file
from .geom_utils import *
from .utils import *


def filter_bus_routes(routes, stops, stop_times, trips, shapes):
    ##Bus route_ids
    routes = routes[routes.route_type == 3]
    route_ids = routes.route_id
    stop_times = stop_times[stop_times.route_id.isin(route_ids)]
    trips = trips[trips.route_id.isin(route_ids)]

    stops_ids = stop_times.stop_id.unique()
    stops = stops[stops.stop_id.isin(stops_ids)]
    shape_ids = trips.shape_id.unique()
    shapes = shapes[shapes.shape_id.isin(shape_ids)]
    return routes, stops, stop_times, trips, shapes


def merge_trip_geom(trip_df,shape_df):
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
    col_subset = set(['route_id','trip_id','shape_id','service_id','direction_id','traversals'])
    trip_df = trip_df[trip_df.columns.intersection(col_subset)]
    trip_df = trip_df.dropna(how='all', axis=1)
    trip_df = shape_df.merge(trip_df, on='shape_id',how='left')
    
#     trip_df = trip_df.set_crs(epsg=4326,allow_override=True)
    return make_gdf(trip_df)

def create_segments(stop_df):
    stop_df = stop_df.rename({'stop_id':'stop_id1'},axis =1)
    start_wkts = stop_df.apply(lambda row: nearest_snap(row['geometry'],row['start']), axis = 1)
    stop_df['start'] = gpd.GeoSeries.from_wkt(start_wkts)
    grp = stop_df.groupby('trip_id').apply(lambda df: df.shift(-1)).reset_index(drop=True)
    stop_df[['stop_id2','end']] = grp[['stop_id1','start']]
    stop_df = stop_df.dropna().reset_index(drop=True)
    stop_df['segment_id'] = stop_df.apply(lambda row: str(row['stop_id1']) +'-'+ str(row['stop_id2']),axis =1)
    stop_df['snapped_start_id'] = stop_df.apply(lambda row: row['start'].within(row['geometry']), axis = 1)
    stop_df['snapped_end_id'] = stop_df.apply(lambda row: row['end'].within(row['geometry']), axis = 1)
    split_routes = stop_df.apply(lambda row: split_route(row),axis = 1)
    stop_df['geometry'] = gpd.GeoSeries.from_wkt(split_routes)
    return stop_df

def filter_stop_df(stop_df,trip_ids):
    stop_df = stop_df[['trip_id','stop_id','stop_sequence']]
    stop_df = stop_df[stop_df.trip_id.isin(trip_ids)].reset_index(drop=True)
    stop_df = stop_df.sort_values(['trip_id','stop_sequence']).reset_index(drop=True)
    return stop_df

def merge_stop_geom(stop_df,stop_loc_df):
    stop_df['start'] = stop_df.copy().merge(stop_loc_df,how='left',on='stop_id')['geometry']
    stop_df = gpd.GeoDataFrame(stop_df,geometry='start')
    return make_gdf(stop_df)
    
def process_feed(feed):
    trip_df = merge_trip_geom(feed.trips,feed.shapes)
    trip_ids = trip_df.trip_id.unique()
    stop_df = filter_stop_df(feed.stop_times,trip_ids)
    stop_loc_df = feed.stops[['stop_id','geometry']]
    stop_df = merge_stop_geom(stop_df,stop_loc_df)    
    stop_df = stop_df.merge(trip_df,on='trip_id',how='left')
    stop_df = create_segments(stop_df)
    # return stop_df
    epsg_zone = get_zone_epsg(stop_df)
    col_subset = set(['route_id','service_id','segment_id','stop_id1','stop_id2','direction_id','traversals','geometry'])
    stop_df = stop_df[stop_df.columns.intersection(col_subset)]
    stop_df = make_gdf(stop_df)    
    stop_df['distance'] = stop_df.to_crs(epsg_zone).geometry.length
    return stop_df

def inspect_feed(feed):
    message = True
    if len(feed.stop_times) == 0:
        message = 'No Bus Routes in ' 
    if not "shape_id" in feed.trips.columns:
        message = "Missing `shape_id` column in "
    return message 

def get_gtfs_segments(path):
    bday ,feed = ptg_read_file(path)
    return process_feed(feed)

def pipeline_gtfs(filename,url,bounds,max_spacing):
    folder_path  = os.path.join('output_files',filename)
    if not os.path.exists(folder_path):
      # Create a new directory because it does not exist 
      os.makedirs(folder_path)
    
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
    summary_stats(df,folder_path,filename,busisest_day,url,bounds,max_spacing)

    plot_func(df,folder_path,filename,max_spacing)
    output_df(df_sub,folder_path)
    return "Success for "+filename