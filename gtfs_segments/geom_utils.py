from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, Optional, Tuple

import contextily as cx
import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import utm
from matplotlib.figure import Figure
from pyproj import Geod
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point
from shapely.ops import split

geod = Geod(ellps="WGS84")


def split_route(row: pd.Series) -> str:
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


def nearest_snap(route_string: LineString, stop_point: Point) -> str:
    """
    It takes a dataframe of bus stops and a dataframe of bus routes and
    returns a dataframe of the nearest bus stop to each bus stop

    Args:
      route: the route geometry
      point: the point you want to snap to the nearest point on the route

    Returns:
      A list of tuples. Each tuple contains the route_id, segment_id, and
      the distance between the two stops.
    """
    route = np.array(route_string.coords)
    point = np.array(stop_point.coords)
    ckd_tree = cKDTree(route)
    return Point(route[ckd_tree.query(point, k=1)[1]][0]).wkt


def make_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    It takes a dataframe and returns a geodataframe

    Args:
      df: the dataframe you want to convert to a geodataframe

    Returns:
      A GeoDataFrame
    """
    gdf = gpd.GeoDataFrame(df)
    gdf = gdf.set_crs(epsg=4326, allow_override=True)
    return gdf


def code(zone: List, lat: float) -> int:
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


def get_zone_epsg(stop_df: gpd.GeoDataFrame) -> int:
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
    gdf: gpd.GeoDataFrame,
    basemap: bool = False,
    map_provider: str = cx.providers.CartoDB.Positron,
    show_stops: bool = False,
    level: str = "whole",
    axis: str = "on",
    dpi: int = 300,
    **kwargs: Any,
) -> Figure:
    """
    The `view_spacings` function plots the spacings of a bus network, route, or segment, with options to
    add a basemap and show stops.

    Args:
      gdf: The GTFS segments GeoDataframe containing the bus network data.
      basemap: The `basemap` parameter is a boolean value that determines whether to add a basemap to
    the plot. If set to `True`, a basemap will be added. If set to `False`, no basemap will be added.
    The default value is `False`. Defaults to False
      map_provider: The `map_provider` parameter is used to specify the source of the basemap that
    will be added to the plot. It is set to `cx.providers.CartoDB.Positron` by default, which means
    that the basemap will be sourced from CartoDB's Positron. Use `contextily.providers` to see full
    list of providers
      show_stops: The `show_stops` parameter is a boolean flag that determines whether or not to display
    the bus stops on the plot. If set to `True`, the bus stops will be shown as white markers on the
    plot. If set to `False`, the bus stops will not be shown. Defaults to False
      level: The "level" parameter determines the level of detail to plot the spacings. It can take one
    of three values:. Defaults to whole
      axis: The `axis` parameter determines whether the axis of the plot should be displayed or not. If
    `axis` is set to "on", the axis will be displayed. If `axis` is set to "off", the axis will not be
    displayed. Defaults to on
      dpi: The `dpi` parameter determines the resolution of the plot. Defaults to 300

    Returns:
      a matplotlib Figure object.
    """
    _, ax = plt.subplots(figsize=(10, 10), dpi=dpi)
    crs = gdf.crs
    # Filter based on direction and level
    if "direction" in kwargs:
        gdf = gdf[gdf.direction_id == kwargs["direction"]].copy()
    if level == "whole":
        markersize = 20
        ax = gdf.plot(
            ax=ax,
            color="#34495e",
            linewidth=0.5,
            edgecolor="black",
            label="Bus network",
            zorder=1,
        )
    elif level == "route":
        markersize = 40
        assert "route" in kwargs, "Please provide a route_id in route attibute"
        gdf = gdf[gdf.route_id.isin(kwargs["route"])].copy()
    elif level == "segment":
        markersize = 60
        assert "segment" in kwargs, "Please provide a segment_id in segment attibute"
        gdf = gdf[gdf.segment_id.isin(kwargs["segment"])].copy()
    else:
        raise ValueError("level must be either whole, route, or segment")

    # Plot the spacings
    if "route" in kwargs:
        gdf = gdf[gdf.route_id.isin(kwargs["route"])].copy()
        if len(kwargs["route"]) > 1:
            ax = gdf.plot(
                ax=ax,
                linewidth=2,
                column="route_id",
                label="Route ID:" + str(kwargs["route"]),
                zorder=2,
                cmap="tab20",
                legend=True,
            )
        else:
            ax = gdf.plot(
                ax=ax,
                linewidth=2,
                color="#2ecc71",
                label="Route ID:" + str(kwargs["route"]),
                zorder=2,
            )
    if "segment" in kwargs:
        try:
            gdf = gdf[gdf.segment_id.isin(kwargs["segment"])].copy()
        except ValueError as e:
            raise ValueError(f"No such segment exists. Check if direction_id is incorrect {e}")
        ax = gdf.plot(
            ax=ax,
            linewidth=2.5,
            color="#000000",
            label="Segment ID: " + str(kwargs["segment"]),
            zorder=3,
        )
    if show_stops:
        geo_series = gdf.geometry.apply(lambda line: Point(line.coords[0]))
        geo_series = pd.concat([geo_series, gpd.GeoSeries(Point(gdf.iloc[-1].geometry.coords[-1]))])
        geo_series.set_crs(crs=gdf.crs).plot(
            ax=ax,
            color="#FFD700",
            edgecolor="#000000",
            linewidth=1,
            markersize=markersize,
            alpha=0.95,
            zorder=10,
        )

    if basemap:
        df = gpd.GeoDataFrame(gdf, crs=crs)
        cx.add_basemap(ax, crs=df.crs, source=map_provider, attribution_size=5)
    plt.axis(axis)
    if level != "segment":
        plt.legend(loc="best")
    else:
        ax.legend().set_visible(False)
    return ax


def view_spacings_interactive(
    gdf: gpd.GeoDataFrame,
    basemap: bool = True,
    show_stops: bool = False,
    level: str = "whole",
    **kwargs: Any,
) -> folium.Map:
    """
    Generates an interactive Folium map to visualize stop spacings.

    Parameters:
        gdf (gpd.GeoDataFrame): The GeoDataFrame containing the stop spacing data.
        basemap (bool, optional): Whether to add a basemap to the map. Defaults to True.
        show_stops (bool, optional): Whether to show the stops on the map. Defaults to False.
        level (str, optional): The level at which to filter the data. Can be 'whole', 'route', or 'segment'.
            Defaults to 'whole'.
        **kwargs: Additional keyword arguments for filtering the data based on level.

    Returns:
        folium.Map: The generated Folium map.

    Raises:
        AssertionError: If the required attributes for filtering the data are not provided.

    Example usage:
        gdf = gpd.GeoDataFrame(...)
        map = view_spacings_interactive(gdf, basemap=True, show_stops=True, level='route', route='123')
    """
    if "direction" in kwargs:
        gdf = gdf[gdf.direction_id == kwargs["direction"]].copy()
    # Convert CRS to EPSG:4326 if needed
    if gdf.crs.to_string() != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)

    # Initialize Folium Map
    bounds = gdf.total_bounds
    map_center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    fmap = folium.Map(location=map_center, control_scale=True, zoom_start=12)

    # Filter and plot based on level
    if level == "route":
        assert "route" in kwargs, "Please provide a route_id in route attribute"
        gdf = gdf[gdf.route_id == kwargs["route"]].copy()
    elif level == "segment":
        assert "segment" in kwargs, "Please provide a segment_id in segment attribute"
        gdf = gdf[gdf.segment_id == kwargs["segment"]].copy()

    # Add lines to map
    tooltip = folium.GeoJsonTooltip(fields=["segment_id", "distance"])
    popup = folium.GeoJsonPopup(fields=gdf.drop(columns=["geometry"]).columns.tolist())

    def style_function(x: Any) -> dict[str, Any]:
        if "route" in kwargs:
            return {
                "color": (
                    "#2ecc71" if x["properties"]["route_id"] == kwargs["route"] else "#34495e"
                ),
                "weight": (5 if x["properties"]["route_id"] == kwargs["route"] else 2),
            }
        if "segment" in kwargs:
            return {
                "color": (
                    "#000000" if x["properties"]["segment_id"] == kwargs["segment"] else "#34495e"
                ),
                "weight": (5 if x["properties"]["segment_id"] == kwargs["segment"] else 2),
                "z_index": 1000,
            }
        return {"color": "#34495e", "weight": 2}

    folium.GeoJson(
        gdf, tooltip=tooltip, popup=popup, zoom_on_click=True, style_function=style_function
    ).add_to(fmap)

    # Show stops
    if show_stops:
        if "route" in kwargs:
            gdf = gdf[gdf.route_id == kwargs["route"]].copy()
        if "segment" in kwargs:
            gdf = gdf[gdf.segment_id == kwargs["segment"]].copy()
        stop_ids = {}
        for _, row in gdf.iterrows():
            stop_ids[row["stop_id1"]] = Point(row["geometry"].coords[0])
            stop_ids[row["stop_id2"]] = Point(row["geometry"].coords[-1])
        for stop_id, point in stop_ids.items():
            folium.CircleMarker(
                location=[point.y, point.x],
                radius=(6 if "segment" in kwargs else 4 if "route" in kwargs else 2),
                scale_radius=True,
                weight=1,
                fill_opacity=0.9,
                color="#000000",
                fill_color="#FFD700",
                fill=True,
                tooltip=str(stop_id),
            ).add_to(fmap)

    # Add basemap
    if basemap:
        folium.TileLayer("CartoDB positron", name="Light Map", control=False).add_to(fmap)

    return fmap


def increase_resolution(geom: LineString, spat_res: int = 5) -> LineString:
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
    coord_pairs = np.array([coords[i : i + 2] for i in range(len(coords) - 1)])
    coord_dists = np.array(
        [geod.geometry_length(LineString(coords[i : i + 2])) for i in range(len(coords) - 1)]
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


def ret_high_res_shape(
    shapes: gpd.GeoDataFrame, trips: pd.DataFrame, spat_res: int = 5
) -> gpd.GeoDataFrame:
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
    shape_ids = trips.shape_id.unique()
    shapes = shapes[shapes.shape_id.isin(shape_ids)].copy()
    high_res_shapes = [
        increase_resolution(row["geometry"], spat_res) for i, row in shapes.iterrows()
    ]
    shapes.geometry = high_res_shapes
    return shapes


def ret_high_res_shape_parallel(shapes: gpd.GeoDataFrame, spat_res: int = 5) -> gpd.GeoDataFrame:
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

    def process_shape(row: pd.core.series.Series) -> LineString:
        return increase_resolution(row["geometry"], spat_res)

    high_res_shapes = []
    with ThreadPoolExecutor(max_workers=None) as executor:
        high_res_shapes = list(executor.map(process_shape, shapes.to_dict("records")))

    shapes.geometry = high_res_shapes
    return shapes


def nearest_points(stop_df: gpd.GeoDataFrame, k_neighbors: int = 3) -> pd.DataFrame:
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
    total_trip_count = 0
    defective_trip_count = 0
    for name, group in stop_df.groupby("trip_id"):
        # print(name)
        count += 1
        total_trip_count += len(group)
        neighbors = k_neighbors
        geom_line = group["geometry"].iloc[0]
        # print(len(geom_line.coords))
        tree = cKDTree(data=np.array(geom_line.coords))
        stops = [x.coords[0] for x in group["start"]]
        if len(stops) <= 1:
            failed_trips.append(name)
            print("Excluding Trip: " + name + " because of too few stops")
            defective_trip_count += len(group)
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
                        defective_trip_count += len(group)
                        break
            if len(points) == len(stops):
                solution_found = True
        if len(points) != len(set(points)):
            print("Processing", count, len(stop_df.trip_id.unique()))
            print("Points defective")

        if not failed_trip:
            stop_df.loc[stop_df.trip_id == name, "snap_start_id"] = points

    print("Total trips processed: ", total_trip_count)
    if defective_trip_count > 0:
        percent_defective = defective_trip_count / total_trip_count * 100
        print("Total defective trips: ", defective_trip_count)
        print(f"Percentage defective trips: {percent_defective:.2f}%",
        )
    stop_df = stop_df[~stop_df.trip_id.isin(failed_trips)].reset_index(drop=True)
    return stop_df


# def process_trip_group(
#     name: str, group: pd.core.groupby.DataFrameGroupBy, k_neighbors: int, geo_const: float
# ) -> Tuple:
#     neighbors = k_neighbors
#     geom_line = group["geometry"].iloc[0]
#     tree = cKDTree(data=np.array(geom_line.coords))
#     stops = [x.coords[0] for x in group["start"]]
#     n_stops = len(stops)
#     if n_stops <= 1:
#         return name, None, True  # Failed trip due to too few stops

#     failed_trip = False
#     solution_found = False
#     points = []
#     while not solution_found:
#         np_dist, np_inds = tree.query(stops, workers=-1, k=neighbors)
#         np_dist = np_dist * geo_const  # Approx distance in meters
#         prev_point = min(np_inds[0])
#         points = [prev_point]
#         for i, nps in enumerate(np_inds[1:]):
#             condition = (nps > prev_point) & (nps < max(np_inds[i + 1]))
#             points_valid = nps[condition]
#             if len(points_valid) > 0:
#                 points_score = np.power(points_valid - prev_point, 3) * np.power(
#                     np_dist[i + 1, condition], 1
#                 )
#                 prev_point = nps[condition][np.argmin(points_score)]
#                 points.append(prev_point)
#             else:
#                 # Capping the number of nearest neighbors to 11
#                 if neighbors < min(n_stops, 11):
#                     neighbors = min(neighbors + 2, n_stops)
#                     break
#                 else:
#                     failed_trip = True
#                     solution_found = True
#                     break
#         if len(points) == n_stops:
#             solution_found = True

#     if failed_trip:
#         return name, None, True
#     else:
#         return name, points, False


def process_trip_group(
    name: str, group: pd.core.groupby.DataFrameGroupBy, k_neighbors: int, geo_const: float
) -> Tuple:
    neighbors = k_neighbors
    geom_line = group["geometry"].iloc[0]
    tree = cKDTree(data=np.array(geom_line.coords))
    stops = [x.coords[0] for x in group["start"]]
    n_stops = len(stops)
    MAX_NEIGHBORS = min(n_stops, 9)
    if n_stops <= 1:
        return name, None, True  # Failed trip due to too few stops

    failed_trip = False
    solution_found = False
    points = []
    np_dist_all, np_inds_all = tree.query(stops, workers=-1, k=MAX_NEIGHBORS)
    np_dist_all = np_dist_all * geo_const  # Approx distance in meters
    while not solution_found:
        np_inds = np_inds_all[:, :neighbors]
        np_dist = np_dist_all[:, :neighbors]
        prev_point = min(np_inds[0])
        points = [prev_point]
        for i, nps in enumerate(np_inds[1:]):
            condition = (nps > prev_point) & (nps < max(np_inds[i + 1]))
            points_valid = nps[condition]
            if len(points_valid) > 0:
                points_score = np.power(points_valid - prev_point, 3) * np.power(
                    np_dist[i + 1, condition], 1
                )
                prev_point = nps[condition][np.argmin(points_score)]
                points.append(prev_point)
            else:
                # Capping the number of nearest neighbors to 11
                if neighbors < MAX_NEIGHBORS:
                    neighbors = min(neighbors + 2, n_stops)
                    break
                else:
                    failed_trip = True
                    solution_found = True
                    break
        if len(points) == n_stops:
            solution_found = True

    if failed_trip:
        return name, None, True
    else:
        return name, points, False


def nearest_points_parallel(stop_df: gpd.GeoDataFrame, k_neighbors: int = 5) -> pd.DataFrame:
    stop_df["snap_start_id"] = -1
    geo_const = 6371000 * np.pi / 180
    failed_trips = []
    defective_trip_count = 0
    with ThreadPoolExecutor(max_workers=None) as executor:
        results = executor.map(
            lambda x: process_trip_group(x[0], x[1], k_neighbors, geo_const),
            stop_df.groupby("trip_id"),
        )

    for name, points, failed in results:
        if failed:
            failed_trips.append(name)
        else:
            stop_df.loc[stop_df.trip_id == name, "snap_start_id"] = points
    defective_trip_count = (
        stop_df[stop_df.trip_id.isin(failed_trips)].groupby("trip_id").first().traversals.sum()
    )
    total_trip_count = len(stop_df)
    stop_df = stop_df[~stop_df.trip_id.isin(failed_trips)].reset_index(drop=True)

    print("Total trips processed:", total_trip_count)
    if defective_trip_count > 0:
        print("Total defective trips:", defective_trip_count)
        print(
            "Percentage defective trips:{:.2f}".format(
                defective_trip_count / total_trip_count * 100
            )
        )
    return stop_df


def view_heatmap(
    gdf: gpd.GeoDataFrame,
    column: str = "distance",
    cmap: Optional[str] = "RdYlBu",
    light_mode: bool = True,
    interactive: bool = False,
) -> Any:
    """
    Generates a heatmap visualization of a GeoDataFrame.

    Parameters:
        gdf (gpd.GeoDataFrame): The GeoDataFrame containing the data to be visualized.
        cmap (Optional[str], optional): The colormap to be used for the heatmap. Defaults to "RdYlBu".
        light_mode (bool, optional): Specifies whether to use a light mode basemap. Defaults to True.
        interactive (bool, optional): Specifies whether to generate an interactive map. Defaults to False.

    Returns:
        Any: The generated heatmap visualization.

    """
    df_filtered = gdf.copy()
    df_filtered[column] = pd.to_numeric(df_filtered[column])
    if column == "distance":
        MAX_RANGE = gdf["distance"].max()
        df_filtered = gdf[(gdf["distance"] >= 30)].copy()
        bins = [125, 200, 400, 600, 800, 1000, 1200, 1500, 2000, MAX_RANGE]
    else:
        df_filtered = df_filtered[(df_filtered[column] >= df_filtered[column].quantile(0.01))]
        df_filtered = df_filtered[(df_filtered[column] <= df_filtered[column].quantile(1 - 0.01))]
    if interactive:
        if column == "distance":
            fmap = df_filtered.explore(
                column=column,
                scheme="UserDefined",
                tooltip=["segment_id", "distance"],
                tiles="CartoDB Positron" if light_mode else "CartoDB Dark Matter",
                legend=True,
                cmap=cmap,  # YlOrRd
                classification_kwds=dict(bins=bins),
                legend_kwds=dict(colorbar=False, fmt="{:.0f}"),
                style_kwds=dict(opacity=0.75, fillOpacity=0.75),
                popup=True,
            )
        else:
            fmap = df_filtered.explore(
                column=column,
                cmap=cmap,  # YlOrRd
                tooltip=["segment_id", column],
                tiles="CartoDB Positron" if light_mode else "CartoDB Dark Matter",
                legend=True,
                style_kwds=dict(opacity=0.75, fillOpacity=0.75),
                popup=True,
                scheme="Quantiles",
                legend_kwds=dict(colorbar=False, fmt="{:.0f}"),
            )
        return fmap
    else:
        fig, ax = plt.subplots(figsize=(10, 8), dpi=300)
        if column == "distance":
            df_filtered.plot(
                column=column,
                scheme="UserDefined",
                cmap=cmap,  # YlOrRd
                kind="geo",
                ax=ax,
                legend=True,
                classification_kwds=dict(bins=bins),
                legend_kwds=dict(
                    fmt="{:.0f}", loc="upper left", bbox_to_anchor=(0, 1), interval=True
                ),
                alpha=0.75,
            )
        else:
            df_filtered.plot(
                column=column,
                cmap=cmap,  # YlOrRd
                kind="geo",
                ax=ax,
                legend=True,
                alpha=0.275,
                scheme="Quantiles",
            )
        map_provider = (
            cx.providers.CartoDB.Positron if light_mode else cx.providers.CartoDB.DarkMatter
        )
        cx.add_basemap(ax, crs=gdf.crs, source=map_provider, attribution_size=5)
        plt.axis("off")
        plt.close()
        return fig
