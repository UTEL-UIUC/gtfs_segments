import utm
import numpy as np
import geopandas as gpd
from shapely.ops import split
from shapely.geometry import Point
from scipy.spatial import cKDTree

def split_route(row):
    """Split route into segments

    Args:
        row (row): row in stop_df

    Returns:
        geometry: route segments
    """ 
    route= row['geometry']
    if row['snapped_start_id']:
        try:
            route = split(route,row['start']).geoms[1]
        except:
            route = route
    if row['snapped_end_id']:
        route = split(route,row['end']).geoms[0]
    return route.wkt

def nearest_snap(route,point):
    """Snap the stop the route geometry. Snap to nearest coord in route

    Args:
        route (geometry): bus route geometry
        point (geometry): bus stop geometry

    Returns:
        geometry: snapped Point
    """
    route = np.array(route.coords)
    point = np.array(point.coords)
    ckd_tree = cKDTree(route)
    return Point(route[ckd_tree.query(point, k=1)[1]][0]).wkt

def make_gdf(df):
    """Make DataFrame as GeoDataFrame

    Args:
        df (DataFrame): Any pandas DataFrame

    Returns:
        GeoDataFrame: GeoDataFrame with EPSG 4326
    """
    df = gpd.GeoDataFrame(df)
    df =  df.set_crs(epsg=4326,allow_override= True)
    return df

def code(zone,lat):
    """Obtain EPSG geo code for the lat longitude

    Args:
        zone (tuple): utm zone for City 
        lat (float): latitude   

    Returns:
        float: epsg_code
    """
    #The EPSG code is 32600+zone for positive latitudes and 32700+zone for negatives.
    if lat <0:
        epsg_code = 32700 + zone[2]
    else:
        epsg_code = 32600 + zone[2]
    return epsg_code

def get_zone_epsg(stop_df):
    """Get EPSG zone for the DataFrame

    Args:
        stop_df (DataFrame): DataFrame of stop times

    Returns:
        int: EPSG zone code
    """
    lon = stop_df.start[0].x
    lat = stop_df.start[0].y
    zone = utm.from_latlon(lat, lon)
    return code(zone,lat)