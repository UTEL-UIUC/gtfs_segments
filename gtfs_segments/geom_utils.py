import utm
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.ops import split
from shapely.geometry import Point, LineString
from scipy.spatial import cKDTree
import contextily as cx
import matplotlib.pyplot as plt
from pyproj import Geod

geod = Geod(ellps="WGS84")


def split_route(row):
    """
    It takes a row from a dataframe, and if the row has a start and end point,
    it splits the route into two segments

    Args:
      row: row in stop_df

    Returns:
      the geometry of the route segments.
    """
    route = row["geometry"]
    if row["snapped_start_id"]:
        try:
            route = split(route, row["start"]).geoms[1]
        except IndexError:
            pass
    if row["snapped_end_id"]:
        route = split(route, row["end"]).geoms[0]
    return route.wkt


def nearest_snap(route, point):
    """
    It takes a dataframe of bus stops and a dataframe of bus routes and
    returns a dataframe of the nearest bus stop to each bus stop

    Args:
      route: the route id of the route you want to view
      point: the point you want to snap to the nearest point on the route

    Returns:
      A list of tuples. Each tuple contains the route_id, segment_id, and
      the distance between the two stops.
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
    If the latitude is negative, the EPSG code is 32700 + the zone number. If
    the latitude is positive, the EPSG code is 32600 + the zone number

    Args:
      zone: The UTM zone number.
      lat: latitude of the point

    Returns:
      The EPSG Code
    """
    if lat < 0:
        epsg_code = 32700 + zone[2]
    else:
        epsg_code = 32600 + zone[2]
    return epsg_code


def get_zone_epsg(stop_df):
    """
    > The function takes a dataframe with a geometry column and returns the
    EPSG code for the UTM zone that contains the geometry

    Args:
      stop_df: a dataframe with a geometry column

    Returns:
      The EPSG code for the UTM zone that the stop is in.
    """
    lon = stop_df.start[0].x
    lat = stop_df.start[0].y
    zone = utm.from_latlon(lat, lon)
    return code(zone, lat)


def view_spacings(
    df, basemap=False, show_stops=False, level="whole", axis="on", **kwargs
):
    """
    > This function plots the spacings of the bus network, or a specific route,
    or a specific segment

    Args:
      df: the dataframe containing the bus network
      basemap: if True, will add a basemap to the plot. Defaults to False
      level: "whole" or "route" or "segment". Defaults to whole
      axis: 'on' or 'off'. Defaults to on
    """
    fig, ax = plt.subplots(figsize=(10, 10), dpi=100)
    crs = df.crs
    # Filter based on direction and level
    if "direction" in kwargs.keys():
        df = df[df.direction_id == kwargs["direction"]].copy()
    if level == "whole":
        markersize = 15
        ax = df.plot(
            ax=ax,
            color="y",
            linewidth=0.50,
            edgecolor="black",
            label="Bus network",
            zorder=1,
        )
    elif level == "route":
        markersize = 30
        assert "route" in kwargs.keys(), "Please provide a route_id in route attibute"
        df = df[df.route_id == kwargs["route"]].copy()
    elif level == "segment":
        markersize = 50
        assert (
            "segment" in kwargs.keys()
        ), "Please provide a segment_id in segment attibute"
        df = df[df.segment_id == kwargs["segment"]].copy()
    else:
        raise ValueError("level must be either whole, route, or segment")

    # Plot the spacings
    if "route" in kwargs.keys():
        df = df[df.route_id == kwargs["route"]].copy()
        ax = df.plot(
            ax=ax,
            linewidth=1.5,
            color="dodgerblue",
            label="Route ID:" + kwargs["route"],
            zorder=2,
        )
    if "segment" in kwargs.keys():
        try:
            df = df[df.segment_id == kwargs["segment"]].copy()
        except ValueError as e:
            raise ValueError(
                "No such segment exists. Check if direction_id is incorrect {}".format(e)
            )
        ax = df.plot(
            ax=ax,
            linewidth=2,
            color="red",
            label="Segment ID: " + str(kwargs["segment"]),
            zorder=3,
        )
    if show_stops:
        geo_series = df.geometry.apply(lambda line: Point(line.coords[0]))
        geo_series = pd.concat(
            [geo_series, gpd.GeoSeries(Point(df.iloc[-1].geometry.coords[-1]))]
        )
        geo_series.set_crs(crs=df.crs).plot(
            ax=ax,
            color="white",
            edgecolor="#3700b3",
            linewidth=1,
            markersize=markersize,
            alpha=0.95,
            zorder=10,
        )

    if basemap:
        df = gpd.GeoDataFrame(df, crs=crs)
        cx.add_basemap(
            ax,
            crs=df.crs,
            source=cx.providers.Stamen.TonerLite,
            attribution_size=5
        )
    plt.axis(axis)
    plt.legend(loc="lower right")
    plt.close(fig)
    return fig


def increase_resolution(geom, spat_res=5):
    """
    This function increases the resolution of a LineString geometry by adding 
    points along the line at a specified spatial resolution.

    Args:
      geom: The input geometry that needs to be modified (in this case, a LineString).
      spat_res: spatial resolution, which is the desired distance between consecutive points
        on the LineString. If the distance between two consecutive points is greater than the
        spatial resolution, the function will add additional points to the LineString to
        increase its resolution. Defaults to 5

    Returns:
      a LineString object with increased resolution based on the input spatial resolution.
    """
    coords = geom.coords
    coord_pairs = np.array([coords[i: i + 2] for i in range(len(coords) - 1)])
    coord_dists = np.array(
        [
            geod.geometry_length(LineString(coords[i: i + 2]))
            for i in range(len(coords) - 1)
        ]
    )
    new_ls = []
    for i, dists in enumerate(coord_dists):
        pair = coord_pairs[i]
        if dists > spat_res:
            factor = int(np.ceil(dists / spat_res))
            ret_points = [tuple(pair[0])]
            for j in range(1, factor):
                new_point = (
                    pair[0][0] + (pair[1][0] - pair[0][0]) * j / factor,
                    pair[0][1] + (pair[1][1] - pair[0][1]) * j / factor,
                )
                ret_points.append(new_point)
            for pt in ret_points:
                new_ls.append(pt)
        else:
            new_ls.append(tuple(pair[0]))
    new_ls.append(tuple(coord_pairs[-1][1]))
    return LineString(new_ls)


def ret_high_res_shape(shapes, spat_res=5):
    """
    This function increases the resolution of the geometries in a given dataframe of shapes by a
    specified spatial resolution.

    Args:
      shapes: a pandas DataFrame containing a column named 'geometry' that contains shapely geometry
    objects
      spat_res: spatial resolution, which is the size of each pixel or cell in a raster dataset. In this
    function, it is used to increase the resolution of the input shapes by creating more vertices in
    their geometries. The default value is 5, which means that the resolution will be increased by
    adding vertices. Defaults to 5

    Returns:
      a GeoDataFrame with the geometry column updated to have higher resolution shapes.
    """
    high_res_shapes = []
    for i, row in shapes.iterrows():
        high_res_shapes.append(increase_resolution(row["geometry"], spat_res))
    shapes.geometry = high_res_shapes
    return shapes


def nearest_points(stop_df, k_neighbors=3):
    """
    The function takes a dataframe of stops and snaps them to the nearest points on a line geometry,
    with an option to specify the number of nearest neighbors to consider.

    Args:
      stop_df: a pandas DataFrame containing information about stops along a set of trips, including the
    trip ID, the stop location (as a Shapely Point object), and the geometry of the trip (as a Shapely
    LineString object)
      k_neighbors: The number of nearest neighbors to consider when snapping stops to a line geometry.
    Default value is 3. Defaults to 3

    Returns:
      the stop_df dataframe with an additional column 'snap_start_id' which contains the indices of the
    nearest points on the trip route for each stop. If any trips failed to snap, they are excluded from
    the returned dataframe.
    """
    stop_df["snap_start_id"] = -1
    geo_const = 6371000 * np.pi / 180
    failed_trips = []
    count = 0
    for name, group in stop_df.groupby("trip_id"):
        # print(name)
        count += 1
        neighbors = k_neighbors
        geom_line = group["geometry"].iloc[0]
        # print(len(geom_line.coords))
        tree = cKDTree(data=np.array(geom_line.coords))
        stops = [x.coords[0] for x in group["start"]]
        if len(stops) <= 1:
            failed_trips.append(name)
            print("Excluding Trip: " + name + " because of too few stops")
            continue
        failed_trip = False
        solution_found = False
        while not solution_found:
            np_dist, np_inds = tree.query(stops, workers=-1, k=neighbors)
            # Approx distance in meters
            np_dist = np_dist * geo_const  
            prev_point = min(np_inds[0])
            points = [prev_point]
            for i, nps in enumerate(np_inds[1:]):
                condition = (nps > prev_point) & (nps < max(np_inds[i + 1]))
                points_valid = nps[condition]
                if len(points_valid) > 0:
                    points_score = (np.power(points_valid - prev_point, 3)) * np.power(
                        np_dist[i + 1, condition], 1
                    )
                    prev_point = nps[condition][np.argmin(points_score)]
                    points.append(prev_point)
                else:
                    # No valid points found
                    if neighbors < len(stops):
                        neighbors = min(neighbors + 2, len(stops))
                        break
                    else:
                        failed_trips.append(name)
                        failed_trip = True
                        # Make this to exit the while loop
                        solution_found = True 

                        print("Excluding Trip: " + name + " because of failed snap!")
                        break
            if len(points) == len(stops):
                solution_found = True
        if len(points) != len(set(points)):
            print("Processing", count, len(stop_df.trip_id.unique()))
            print("Points defective")

        if not failed_trip:
            stop_df.loc[stop_df.trip_id == name, "snap_start_id"] = points
    stop_df = stop_df[~stop_df.trip_id.isin(failed_trips)].reset_index(drop=True)
    return stop_df
