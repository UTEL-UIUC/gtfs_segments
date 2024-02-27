import os
from typing import List, Optional, Set

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString

from .geom_utils import (
    get_zone_epsg,
    make_gdf,
    nearest_points,
    nearest_points_parallel,
    ret_high_res_shape,
)
from .mobility import summary_stats_mobility
from .partridge_func import get_bus_feed
from .partridge_mod.gtfs import Feed
from .utils import download_write_file, export_segments, failed_pipeline, plot_hist


def merge_trip_geom(trip_df: pd.DataFrame, shape_df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    It takes a dataframe of trips and a dataframe of shapes, and returns a geodataframe of trips with
    the geometry of the shapes

    Args:
      trip_df: a dataframe of trips
      shape_df: a GeoDataFrame of the shapes.txt file

    Returns:
      A GeoDataFrame
    """
    trips_with_no_shape_id = list(trip_df[trip_df["shape_id"].isna()].trip_id)
    if len(trips_with_no_shape_id) > 0:
        print("Excluding Trips with no shape_id:", trips_with_no_shape_id)
        trip_df = trip_df[~trip_df["trip_id"].isin(trips_with_no_shape_id)]

    non_existent_shape_id = set(trip_df["shape_id"]) - set(shape_df["shape_id"])
    if len(non_existent_shape_id) > 0:
        trips_with_no_corresponding_shape = list(trip_df[trip_df["shape_id"].isin(non_existent_shape_id)].trip_id)
        print("Excluding Trips with non-existent shape_ids in shapes.txt:", trips_with_no_corresponding_shape)
        trip_df = trip_df[~trip_df["shape_id"].isin(non_existent_shape_id)]

    # `direction_id` and `shape_id` are optional
    if "direction_id" in trip_df.columns:
        # Check is direction_ids are listed as null
        if trip_df["direction_id"].isnull().sum() == 0:
            grp = trip_df.groupby(["route_id", "shape_id", "direction_id"])
        else:
            grp = trip_df.groupby(["route_id", "shape_id"])
    else:
        grp = trip_df.groupby(["route_id", "shape_id"])
    trip_df = grp.first().reset_index()
    trip_df["traversals"] = grp.count().reset_index(drop=True)["trip_id"]
    subset_list = np.array(
        ["route_id", "trip_id", "shape_id", "service_id", "direction_id", "traversals"]
    )
    col_subset = subset_list[np.in1d(subset_list, trip_df.columns)]
    trip_df = trip_df[col_subset]
    trip_df = trip_df.dropna(how="all", axis=1)
    trip_df = shape_df.merge(trip_df, on="shape_id", how="left")
    return make_gdf(trip_df)


def make_segments_unique(df: gpd.GeoDataFrame, traversal_threshold: int = 1) -> gpd.GeoDataFrame:
    # Compute the number of unique rounded distances for each route_id and segment_id
    unique_counts = df.groupby(["route_id", "segment_id"])["distance"].apply(
        lambda x: x.round().nunique()
    )

    # Filter rows where unique count is greater than 1
    filtered_df = df[
        df.set_index(["route_id", "segment_id"]).index.isin(unique_counts[unique_counts > 1].index)
    ].copy()

    # Create a segment modification function
    def modify_segment(segment_id: str, count: int) -> str:
        seg_split = str(segment_id).split("-")
        return seg_split[0] + "-" + seg_split[1] + "-" + str(count + 1)

    # Apply the modification function to the segment_id
    filtered_df["modification"] = filtered_df.groupby(["route_id", "segment_id"]).cumcount()
    filtered_df["segment_id"] = filtered_df.apply(
        lambda row: modify_segment(row["segment_id"], row["modification"])
        if row["modification"] != 0
        else row["segment_id"],
        axis=1,
    )

    # Merge the modified segments back into the original DataFrame
    df = pd.concat([df[~df.index.isin(filtered_df.index)], filtered_df], ignore_index=True)

    # Aggregate traversals and filter by traversal threshold
    grp_again = df.groupby(["route_id", "segment_id"])
    df = grp_again.first().reset_index()
    df["traversals"] = grp_again["traversals"].sum().values
    df = df[df.traversals > traversal_threshold].reset_index(drop=True)
    return make_gdf(df)


def filter_stop_df(stop_df: pd.DataFrame, trip_ids: Set, stop_loc_df: pd.DataFrame) -> pd.DataFrame:
    """
    It takes a dataframe of stops and a list of trip IDs and returns a dataframe of stops that are in
    the list of trip IDs

    Args:
      stop_df: the dataframe of all stops
      trip_ids: a list of trip_ids that you want to filter the stop_df by

    Returns:
      A dataframe with the trip_id, s top_id, and stop_sequence for the trips in the trip_ids list.
    """
    missing_stop_locs = set(stop_df.stop_id) - set(stop_loc_df.stop_id)
    if len(missing_stop_locs) > 0:
        print("Missing stop locations for:", missing_stop_locs)
        missing_trips = stop_df[stop_df.stop_id.isin(missing_stop_locs)].trip_id.unique()
        for trip in missing_trips:
            trip_ids.discard(trip)
            print(
                "Removed the trip_id:", trip, "as stop locations are missing for stops in the trip"
            )
    # Filter the stop_df to only include the trip_ids in the trip_ids list
    stop_df = stop_df[stop_df.trip_id.isin(trip_ids)].reset_index(drop=True)
    stop_df = stop_df.sort_values(["trip_id", "stop_sequence"]).reset_index(drop=True)
    stop_df["main_index"] = stop_df.index
    stop_df_grp = stop_df.groupby("trip_id")
    drop_inds = []
    # To eliminate deadheads
    if "pickup_type" in stop_df.columns:
        grp_f = stop_df_grp.first()
        drop_inds.append(grp_f.loc[grp_f["pickup_type"] == 1, "main_index"])
    if "drop_off_type" in stop_df.columns:
        grp_l = stop_df_grp.last()
        drop_inds.append(
            grp_l.loc[grp_l["drop_off_type"] == 1, "main_index"]
        )  # Fixed the variable name from grp_f to grp_l
    if len(drop_inds) > 0 and len(drop_inds[0]) > 0:
        stop_df = stop_df[~stop_df["main_index"].isin(drop_inds)].reset_index(drop=True)
    stop_df = stop_df[["trip_id", "stop_id", "stop_sequence", "arrival_time"]]

    stop_df = stop_df.sort_values(["trip_id", "stop_sequence"]).reset_index(drop=True)
    return stop_df


def merge_stop_geom(stop_df: pd.DataFrame, stop_loc_df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    > Merge the stop_loc_df with the stop_df, and then convert the result to a GeoDataFrame

    Args:
      stop_df: a dataframe of stops
      stop_loc_df: a GeoDataFrame of the stops

    Returns:
      A GeoDataFrame
    """
    stop_df["start"] = stop_df.copy().merge(stop_loc_df, how="left", on="stop_id")["geometry"]
    return stop_df


def create_segments(stop_df: gpd.GeoDataFrame, parallel: bool = False) -> pd.DataFrame:
    """
    This function creates segments between stops based on their proximity and returns a GeoDataFrame.

    Args:
      stop_df: A pandas DataFrame containing information about stops on a transit network, including
    their stop_id, coordinates, and trip_id.

    Returns:
      a GeoDataFrame with segments created from the input stop_df.
    """
    if parallel:
        stop_df = nearest_points_parallel(stop_df)
    else:
        stop_df = nearest_points(stop_df)
    stop_df = stop_df.rename({"stop_id": "stop_id1", "arrival_time": "arrival_time1"}, axis=1)
    grp = (
        pd.DataFrame(stop_df).groupby("trip_id", group_keys=False).shift(-1).reset_index(drop=True)
    )
    stop_df[["stop_id2", "end", "snap_end_id", "arrival_time2"]] = grp[
        ["stop_id1", "start", "snap_start_id", "arrival_time1"]
    ]
    stop_df["segment_id"] = stop_df.apply(
        lambda row: str(row["stop_id1"]) + "-" + str(row["stop_id2"]) + "-1", axis=1
    )
    stop_df = stop_df.dropna().reset_index(drop=True)
    stop_df.snap_end_id = stop_df.snap_end_id.astype(int)
    stop_df = stop_df[stop_df["snap_end_id"] > stop_df["snap_start_id"]].reset_index(drop=True)
    stop_df["geometry"] = stop_df.apply(
        lambda row: LineString(
            row["geometry"].coords[row["snap_start_id"] : row["snap_end_id"] + 1]
        ),
        axis=1,
    )
    return stop_df


def process_feed_stops(feed: Feed) -> gpd.GeoDataFrame:
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
    trip_df = merge_trip_geom(feed.trips, feed.shapes)
    trip_ids = set(trip_df.trip_id.unique())
    stop_loc_df = feed.stops[["stop_id", "geometry"]]
    stop_df = filter_stop_df(feed.stop_times, trip_ids, stop_loc_df)
    stop_df = merge_stop_geom(stop_df, stop_loc_df)
    stop_df = stop_df.merge(trip_df, on="trip_id", how="left")
    stops = stop_df.groupby("shape_id").count().reset_index()["geometry"]
    stop_df = stop_df.groupby("shape_id").first().reset_index()
    stop_df["n_stops"] = stops
    epsg_zone = get_zone_epsg(stop_df)
    if epsg_zone is not None:
        stop_df["distance"] = stop_df.geometry.to_crs(epsg_zone).length
        stop_df["mean_distance"] = stop_df["distance"] / stop_df["n_stops"]
    return make_gdf(stop_df)


def process_feed(
    feed: Feed, parallel: bool = False, max_spacing: Optional[float] = None
) -> gpd.GeoDataFrame:
    """
    The function `process_feed` takes a feed and optional maximum spacing as input, performs various
    data processing and filtering operations on the feed, and returns a GeoDataFrame containing the
    processed data.

    Args:
      feed: The `feed` parameter is a data structure that contains information about a transit network.
    It likely includes data such as shapes (geometric representations of routes), trips (sequences of
    stops), stop times (arrival and departure times at stops), and stops (locations of stops).
      [Optional] max_spacing: The `max_spacing` parameter is an optional parameter that specifies the maximum
    distance between stops. If provided, the function will filter out stops that are farther apart than
    the specified maximum spacing.

    Returns:
      A GeoDataFrame containing information about the stops and segments in the feed with segments smaller than the max_spacing values.
    """
    # Set a Spatial Resolution and increase the resolution of the shapes
    # shapes = ret_high_res_shape_parallel(feed.shapes, spat_res=5)
    ## Note: Currently, the parallel version of the function ret_high_res_shape_parallel is not working as expected and is slower than the non-parallel version
    shapes = ret_high_res_shape(feed.shapes, feed.trips, spat_res=5)
    trip_df = merge_trip_geom(feed.trips, shapes)
    trip_ids = set(trip_df.trip_id.unique())
    stop_loc_df = feed.stops[["stop_id", "geometry"]]
    stop_df = filter_stop_df(feed.stop_times, trip_ids, stop_loc_df)
    stop_df = merge_stop_geom(stop_df, stop_loc_df)
    stop_df = stop_df.merge(trip_df, on="trip_id", how="left")
    stop_df = create_segments(stop_df, parallel=parallel)
    stop_df = make_gdf(stop_df)
    epsg_zone = get_zone_epsg(stop_df)
    if epsg_zone is not None:
        stop_df["distance"] = stop_df.set_geometry("geometry").to_crs(epsg_zone).geometry.length
        stop_df["distance"] = stop_df["distance"].round(2)  # round to 2 decimal places
    stop_df["traversal_time"] = (stop_df["arrival_time2"] - stop_df["arrival_time1"]).astype(
        "float"
    )
    stop_df["speed"] = stop_df["distance"].div(stop_df["traversal_time"])
    stop_df = make_segments_unique(stop_df, traversal_threshold=0)
    subset_list = np.array(
        [
            "segment_id",
            "route_id",
            "direction_id",
            "trip_id",
            "traversals",
            "distance",
            "stop_id1",
            "stop_id2",
            "traversal_time",
            "speed",
            "geometry",
        ]
    )
    col_subset = subset_list[np.in1d(subset_list, stop_df.columns)]
    stop_df = stop_df[col_subset]
    if max_spacing is not None:
        stop_df = stop_df[stop_df["distance"] <= max_spacing]
    return make_gdf(stop_df)


def inspect_feed(feed: Feed) -> str:
    """
    It checks to see if the feed has any bus routes and if it has a `shape_id` column in the `trips`
    table

    Args:
      feed: The feed object that you want to inspect.

    Returns:
      A message
    """
    message = "Valid GTFS Feed"
    if len(feed.stop_times) == 0:
        message = "No Bus Routes in "
    if "shape_id" not in feed.trips.columns:
        message = "Missing `shape_id` column in "
    return message


def get_gtfs_segments(
    path: str,
    agency_id: Optional[str] = None,
    threshold: Optional[int] = 1,
    max_spacing: Optional[float] = None,
    parallel: bool = False,
) -> gpd.GeoDataFrame:
    """
    The function `get_gtfs_segments` takes a path to a GTFS feed file, an optional agency name, a
    threshold value, and an optional maximum spacing value, and returns processed GTFS segments.

    Args:
      path: The path parameter is the file path to the GTFS (General Transit Feed Specification) data.
    This is the data format used by public transportation agencies to provide schedule and geographic
    information about their services.
      [Optional] agency_id: The agency_id of the transit agency for which you want to retrieve the bus feed. If this
    parameter is not provided, the function will retrieve the bus feed for all transit agencies. You can pass
    a list of agency_ids to retrieve the bus feed for multiple transit agencies.
      [Optional] threshold: The threshold parameter is used to filter out bus trips that have fewer stops than the
    specified threshold. Trips with fewer stops than the threshold will be excluded from the result.
    Defaults to 1
      [Optional] max_spacing: The `max_spacing` parameter is used to specify the maximum distance between two
    consecutive stops in a segment. If the distance between two stops exceeds the `max_spacing` value,
    the segment is split into multiple segments.

    Returns:
      A GeoDataFrame containing information about the stops and segments in the feed with segments
      smaller than the max_spacing values. Each row contains the following columns:
      - segment_id: the segment's identifier, produced by gtfs-segments
      - stop_id1: The `stop_id` identifier of the segment's beginning stop.
        The identifier is the same one the agency has chosen in the stops.txt file of its GTFS package.
      - stop_id2: The `stop_id` identifier of the segment's ending stop.
      - route_id: The same route ID listed in the agency's routes.txt file.
      - direction_id: The route's direction identifier.
      - traversals: The number of times the indicated route traverses the segment during the "measurement interval."
        The "measurement interval" chosen is the busiest day in the GTFS schedule: the day which has the most bus services running.
      - distance: The length of the segment in meters.
      - geometry: The segment's LINESTRING (a format for encoding geographic paths).
        All geometries are re-projected onto Mercator (EPSG:4326/WGS84) to maintain consistency.
    """
    feed = get_bus_feed(path, agency_id=agency_id, threshold=threshold, parallel=parallel)
    df = process_feed(feed, parallel=parallel)
    if max_spacing is not None:
        print("Using max_spacing {:.0f} to filter segments".format(max_spacing))
        df = df[df["distance"] <= max_spacing]
    return df


def pipeline_gtfs(filename: str, url: str, bounds: List, max_spacing: float) -> str:
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
      Success or Failure of the pipeline
    """
    folder_path = os.path.join("output_files", filename)
    gtfs_file_loc = download_write_file(url, folder_path)

    # read file using GTFS Fucntions
    feed = get_bus_feed(gtfs_file_loc)
    # Remove Null entries
    message = inspect_feed(feed)
    if message != "Valid GTFS Feed":
        return failed_pipeline(message, filename, folder_path)

    df = process_feed(feed)
    df_sub = df[df["distance"] < 3000].copy().reset_index(drop=True)
    if len(df_sub) == 0:
        return failed_pipeline("Only Long Bus Routes in ", filename, folder_path)
    # Output files and Stats
    summary_stats_mobility(df, folder_path, filename, url, bounds, max_spacing, export=True)

    plot_hist(
        df,
        file_path=os.path.join(folder_path, "spacings.png"),
        title=filename.split(".")[0],
        max_spacing=max_spacing,
        save_fig=True,
    )
    export_segments(
        df, os.path.join(folder_path, "geojson"), output_format="geojson", geometry=True
    )
    export_segments(
        df,
        os.path.join(folder_path, "spacings_with_geometry"),
        output_format="csv",
        geometry=True,
    )
    export_segments(df, os.path.join(folder_path, "spacings"), output_format="csv", geometry=False)
    return "Success for " + filename
