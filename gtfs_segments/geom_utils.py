import utm
import numpy as np
import pandas as pd
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
    route = row['geometry']
    if row['snapped_start_id']:
        try:
            route = split(route, row['start']).geoms[1]
        except:
            route = route
    if row['snapped_end_id']:
        route = split(route, row['end']).geoms[0]
    return route.wkt


def nearest_snap(route, point):
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
    df = df.set_crs(epsg=4326, allow_override=True)
    return df


def code(zone, lat):
    """
    If the latitude is negative, the EPSG code is 32700 + the zone number. If the latitude is positive,
    the EPSG code is 32600 + the zone number
    
    Args:
      zone: The UTM zone number.
      lat: latitude of the point
    
    Returns:
      The EPSG code is 32600+zone for positive latitudes and 32700+zone for negatives.
    """
    # The EPSG code is 32600+zone for positive latitudes and 32700+zone for negatives.
    if lat < 0:
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
    return code(zone, lat)


def view_spacings(df, basemap=False, show_stops=False, level="whole", show_axis='on', **kwargs):
  """
  Plots the whole bus network. You can plot a specific route, segment, or direction instead of whole network.
  
  Args:
    df: the dataframe containing the spacings
    basemap: if True, adds a basemap to the plot. Defaults to False
    show_stops: if True, will show the stops on the map. Defaults to False
    level: "whole" or "route" or "segment". Defaults to whole
    show_axis: Plot axis option: 'on' or 'off'. Defaults to on.
  
  Returns:
    A figure object
  """
  fig, ax = plt.subplots(figsize=(10, 10), dpi=100)
  if "direction" in kwargs.keys():
      df = df[df.direction_id == kwargs['direction']].copy()
  if level == "whole":
      ax = df.plot(ax=ax, color='y', linewidth=0.50,
                   edgecolor='black', label='Bus network', zorder=1)
  if "route" in kwargs.keys():
      df = df[df.route_id == kwargs['route']].copy()
      ax = df.plot(ax=ax, linewidth=1.5, color='dodgerblue',
                   label='Route ID:'+kwargs['route_id'], zorder=2)
  if "segment" in kwargs.keys():
      ax = df[df.segment_id == kwargs['segment']].plot(
          ax=ax, color='brown', label='Segment ID:'+kwargs['segment'])
  if basemap:
      cx.add_basemap(ax, crs=df.crs)
  plt.axis(show_axis)
  plt.legend()
  plt.close(fig)
  return fig


def view_spacings(df, basemap=False, show_stops=False, level="whole", axis='on', **kwargs):
    """
    > This function plots the spacings of the bus network, or a specific route, or a specific segment
    
    Args:
      df: the dataframe containing the bus network
      basemap: if True, will add a basemap to the plot. Defaults to False
      level: "whole" or "route" or "segment". Defaults to whole
      axis: 'on' or 'off'. Defaults to on
    """
    fig, ax = plt.subplots(figsize=(10, 10), dpi=100)
    
    ## Filter based on direction and level
    if "direction" in kwargs.keys():
      df = df[df.direction_id == kwargs['direction']].copy()
    if level == "whole":
      markersize = 15
      ax = df.plot(ax=ax, color='y', linewidth=0.50,
                   edgecolor='black', label='Bus network', zorder=1)
    elif level == "route":
      markersize = 30
      assert "route" in kwargs.keys(), "Please provide a route_id in route attibute"
      df = df[df.route_id == kwargs['route']].copy()
    elif level == "segment":
      markersize = 50
      assert "segment" in kwargs.keys(), "Please provide a segment_id in segment attibute"
      df = df[df.segment_id == kwargs['segment']].copy()
    else:
      raise ValueError("level must be either whole, route, or segment")
    
    ## Plot the spacings
    if "route" in kwargs.keys():
        df = df[df.route_id == kwargs['route']].copy()
        ax = df.plot(ax=ax, linewidth=1.5, color='dodgerblue',
                     label='Route ID:'+kwargs['route'], zorder=2)
    if "segment" in kwargs.keys():
        try:
          df = df[df.segment_id == kwargs['segment']].copy()
        except:
          raise ValueError("No such segment exists. Check if direction_id is incorrect") 
        ax = df.plot(ax=ax, linewidth=2, color='red',
                     label='Segment ID: '+str(kwargs['segment']), zorder=3)
    if show_stops:
        geo_series = df.geometry.apply(lambda line: Point(line.coords[0]))
        geo_series = pd.concat([geo_series, gpd.GeoSeries(Point(df.iloc[-1].geometry.coords[-1]))])
        geo_series.set_crs(crs=df.crs).plot(ax=ax, color='white', edgecolor='#3700b3', linewidth=1, markersize=markersize, alpha=0.95, zorder=10)

    if basemap:
        cx.add_basemap(ax, crs=df.crs, source=cx.providers.Stamen.TonerLite, attribution_size=5)
    plt.axis(axis)
    plt.legend(loc='lower right')
    plt.close(fig)
    return fig
