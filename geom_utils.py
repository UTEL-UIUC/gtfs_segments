import utm
import numpy as np
import geopandas as gpd
from shapely.ops import split
from shapely.geometry import Point
from scipy.spatial import cKDTree

def split_route(row):
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
    route = np.array(route.coords)
    point = np.array(point.coords)
    ckd_tree = cKDTree(route)
    return Point(route[ckd_tree.query(point, k=1)[1]][0]).wkt

def make_gdf(df):
    df = gpd.GeoDataFrame(df)
    df =  df.set_crs(epsg=4326,allow_override= True)
    return df

def code(zone,lat):
    #The EPSG code is 32600+zone for positive latitudes and 32700+zone for negatives.
    if lat <0:
        epsg_code = 32700 + zone[2]
    else:
        epsg_code = 32600 + zone[2]
    return epsg_code

def get_zone_epsg(stop_df):
    lon = stop_df.start[0].x
    lat = stop_df.start[0].y
    zone = utm.from_latlon(lat, lon)
    return code(zone,lat)