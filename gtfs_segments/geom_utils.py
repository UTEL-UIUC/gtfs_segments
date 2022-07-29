import utm
import numpy as np
import geopandas as gpd
from shapely.ops import split
from shapely.geometry import Point
from scipy.spatial import cKDTree
import contextily as cx
import matplotlib.pyplot as plt

def split_route(row):
    """
    It takes a row from a dataframe, and if the row has a start and end point, it splits the route into
    two segments
    
    Args:
      row: row in stop_df
    
    Returns:
      the geometry of the route segments.
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
    """
    It takes a dataframe of bus stops and a dataframe of bus routes and returns a dataframe of the
    nearest bus stop to each bus stop
    
    Args:
      route: the route id of the route you want to view
      point: the point you want to snap to the nearest point on the route
    
    Returns:
      a list of tuples. Each tuple contains the route_id, segment_id, and the distance between the two
    stops.
    """
    route = np.array(route.coords)
    point = np.array(point.coords)
    ckd_tree = cKDTree(route)
    return Point(route[ckd_tree.query(point, k=1)[1]][0]).wkt

def make_gdf(df):
    """
    It takes a dataframe and returns a geodataframe
    
    Args:
      df: the dataframe you want to convert to a geodataframe
    
    Returns:
      A GeoDataFrame
    """
    df = gpd.GeoDataFrame(df)
    df =  df.set_crs(epsg=4326,allow_override= True)
    return df

def code(zone,lat):
    """
    If the latitude is negative, the EPSG code is 32700 + the zone number. If the latitude is positive,
    the EPSG code is 32600 + the zone number
    
    Args:
      zone: The UTM zone number.
      lat: latitude of the point
    
    Returns:
      The EPSG code is 32600+zone for positive latitudes and 32700+zone for negatives.
    """
    #The EPSG code is 32600+zone for positive latitudes and 32700+zone for negatives.
    if lat <0:
        epsg_code = 32700 + zone[2]
    else:
        epsg_code = 32600 + zone[2]
    return epsg_code

def get_zone_epsg(stop_df):
    """
    > The function takes a dataframe with a geometry column and returns the EPSG code for the UTM zone
    that contains the geometry
    
    Args:
      stop_df: a dataframe with a geometry column
    
    Returns:
      The EPSG code for the UTM zone that the stop is in.
    """
    lon = stop_df.start[0].x
    lat = stop_df.start[0].y
    zone = utm.from_latlon(lat, lon)
    return code(zone,lat)

def view_spacings(df,basemap=False,level = "whole", axis ='on' ,**kwargs):
    """
    > This function plots the spacings of the bus network, or a specific route, or a specific segment
    
    Args:
      df: the dataframe containing the bus network
      basemap: if True, will add a basemap to the plot. Defaults to False
      level: "whole" or "route" or "segment". Defaults to whole
      axis: 'on' or 'off'. Defaults to on
    """
    fig,ax = plt.subplots(figsize = (8,6),dpi = 200)
    if level == "whole": 
        ax = df.plot(ax = ax,color='black',label='Bus network')
    if "route" in kwargs.keys():
        ax = df[df.route_id == kwargs['route']].plot(ax =ax, color = 'blue', label = kwargs['route'])
    if "segment" in kwargs.keys():
        ax = df[df.segment_id == kwargs['segment']].plot(ax =ax, color = 'brown', label = kwargs['segment'])
    if basemap:
        cx.add_basemap(ax,crs=df.crs)
    plt.axis(axis)
    plt.legend()
    plt.show()