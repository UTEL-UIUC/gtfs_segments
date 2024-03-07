import os
import shutil
import traceback
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from scipy.stats import gaussian_kde
from shapely.geometry import Point

# Plot style
plt.style.use("ggplot")


def plot_hist(
    df: pd.DataFrame, save_fig: bool = False, show_mean: bool = False, **kwargs: Any
) -> plt.Figure:
    """
    It takes a dataframe with two columns, one with the distance between stops and the other with the
    number of traversals between those stops, and plots a weighted histogram of the distances

    Args:
      df: The dataframe that contains the data
      save_fig: If True, the figure will be saved to the file_path. Defaults to False
      show_mean: If True, will show the mean of the distribution. Defaults to False

    Returns:
      A matplotlib axis
    """
    if "max_spacing" not in kwargs.keys():
        max_spacing = 3000
        print("Using max_spacing = 3000")
    else:
        max_spacing = kwargs["max_spacing"]
    if "ax" in kwargs.keys():
        ax = kwargs["ax"]
    else:
        fig, ax = plt.subplots(figsize=(8, 6))
    df = df[df["distance"] < max_spacing]
    data = np.hstack([np.repeat(x, y) for x, y in zip(df["distance"], df.traversals)])
    plt.hist(
        data,
        range=(0, max_spacing),
        density=True,
        bins=int(max_spacing / 50),
        fc=(0, 105 / 255, 160 / 255, 0.4),
        ec="white",
        lw=0.8,
    )
    x = np.arange(0, max_spacing, 5)
    plt.plot(x, gaussian_kde(data)(x), lw=1.5, color=(0, 85 / 255, 120 / 255, 1))
    # sns.histplot(data,binwidth=50,stat = "density",kde=True,ax=ax)
    plt.xlim([0, max_spacing])
    plt.xlabel("Stop Spacing [m]")
    plt.ylabel("Density - Traversal Weighted")
    plt.title("Histogram of Spacing")
    if show_mean:
        plt.axvline(np.mean(data), color="k", linestyle="dashed", linewidth=2)
        _, max_ylim = plt.ylim()
        plt.text(
            np.mean(data) * 1.1,
            max_ylim * 0.9,
            "Mean: {:.0f}".format(np.mean(data)),
            fontsize=12,
        )
    if "title" in kwargs.keys():
        plt.title(kwargs["title"])
    if save_fig:
        assert "file_path" in kwargs.keys(), "Please pass in the `file_path`"
        plt.savefig(kwargs["file_path"], dpi=300)
    plt.close()
    return fig


def summary_stats(
    df: pd.DataFrame, max_spacing: float = 3000, min_spacing: float = 10, export: bool = False, **kwargs: Any
) -> pd.DataFrame:
    """
    It takes in a dataframe, and returns a dataframe with summary statistics.
    The max_spacing and min_spacing serve as threshold to remove outliers.

    Args:
      df: The dataframe that you want to get the summary statistics for.
      max_spacing: The maximum spacing between two stops. Defaults to 3000[m]
      min_spacing: The minimum spacing between two stops. Defaults to 10[m]
      export: If True, the summary will be exported to a csv file. Defaults to False

    Returns:
      A dataframe with the summary statistics
    """
    print("Using max_spacing = ", max_spacing)
    print("Using min_spacing = ", min_spacing)
    percent_spacing = round(
        df[df["distance"] > max_spacing]["traversals"].sum() / df["traversals"].sum() * 100,
        3,
    )
    df = df[(df["distance"] <= max_spacing) & (df["distance"] >= min_spacing)]
    seg_weighted_mean = (
        df.groupby(["segment_id", "distance"]).first().reset_index()["distance"].mean()
    )
    seg_weighted_median = (
        df.groupby(["segment_id", "distance"]).first().reset_index()["distance"].median()
    )
    route_weighted_mean = (
        df.groupby(["route_id", "segment_id", "distance"]).first().reset_index()["distance"].mean()
    )
    route_weighted_median = (
        df.groupby(["route_id", "segment_id", "distance"])
        .first()
        .reset_index()["distance"]
        .median()
    )
    weighted_data = np.hstack([np.repeat(x, y) for x, y in zip(df["distance"], df.traversals)])

    df_dict = {
        "Segment Weighted Mean": np.round(seg_weighted_mean, 2),
        "Route Weighted Mean": np.round(route_weighted_mean, 2),
        "Traversal Weighted Mean": np.round(np.mean(weighted_data), 3),
        "Segment Weighted Median": np.round(seg_weighted_median, 2),
        "Route Weighted Median": np.round(route_weighted_median, 2),
        "Traversal Weighted Median": np.round(np.median(weighted_data), 2),
        "Traversal Weighted Std": np.round(np.std(weighted_data), 3),
        "Traversal Weighted 25 % Quantile": np.round(np.quantile(weighted_data, 0.25), 3),
        "Traversal Weighted 50 % Quantile": np.round(np.quantile(weighted_data, 0.50), 3),
        "Traversal Weighted 75 % Quantile": np.round(np.quantile(weighted_data, 0.75), 3),
        "No of Segments": int(len(df.segment_id.unique())),
        "No of Routes": int(len(df.route_id.unique())),
        "No of Traversals": int(sum(df.traversals)),
        "Max Spacing": int(max_spacing),
        "% Segments w/ spacing > max_spacing": percent_spacing,
    }
    summary_df = pd.DataFrame([df_dict])
    # df.set_index(summary_df.columns[0],inplace=True)
    if export:
        assert "file_path" in kwargs.keys(), "Please pass in the `file_path`"
        summary_df.to_csv(kwargs["file_path"], index=False)
        print("Saved the summary in " + kwargs["file_path"])
    summary_df = summary_df.T
    return summary_df


def export_segments(
    df: pd.DataFrame, file_path: str, output_format: str, geometry: bool = True
) -> None:
    """
    This function takes a GeoDataFrame of segments, a file path, an output format, and a boolean value
    for whether or not to include the geometry in the output.

    If the output format is GeoJSON, the function will output the GeoDataFrame to a GeoJSON file.

    If the output format is CSV, the function will output the GeoDataFrame to a CSV file. If the
    geometry boolean is set to True, the function will output the CSV file with the geometry column. If
    the geometry boolean is set to False, the function will output the CSV file without the geometry
    column.

    The function will also add additional columns to the CSV file, including the start and end points of
    the segments, the start and end longitude and latitude of the segments, and the distance of the
    segments.

    The function will also add a column to the CSV file that indicates the number of times the segment
    was traversed.

    Args:
      df: the dataframe containing the segments
      file_path: The path to the file you want to export to.
      output_format: geojson or csv
      [Optional] geometry: If True, the output will include the geometry of the segments. If False, the output will
    only include the start and end points of the segments. Defaults to True
    """
    # Output to GeoJSON
    if output_format == "geojson":
        df.to_file(file_path, driver="GeoJSON")
    elif output_format == "csv":
        s_df = df.copy()
        geom_list = s_df.geometry.apply(lambda g: np.array(g.coords))
        s_df["start_point"] = [Point(g[0]).wkt for g in geom_list]
        s_df["end_point"] = [Point(g[-1]).wkt for g in geom_list]
        sg_df = s_df.copy()
        s_df["start_lon"] = [g[0][0] for g in geom_list]
        s_df["start_lat"] = [g[0][1] for g in geom_list]
        s_df["end_lon"] = [g[-1][0] for g in geom_list]
        s_df["end_lat"] = [g[-1][1] for g in geom_list]
        if geometry:
            # Output With LS
            sg_df.to_csv(file_path, index=False)
        else:
            d_df = s_df.drop(columns=["geometry", "start_point", "end_point"])
            # Output without LS
            d_df.to_csv(file_path, index=False)


def process(pipeline_gtfs: Any, row: pd.core.series.Series, max_spacing: float) -> Any:
    """
    It takes a pipeline, a row from the sources_df, and a max_spacing, and returns the output of the
    pipeline

    Args:
        pipeline_gtfs: This is the function that will be used to process the GTFS data.
        row: This is a row in the sources_df dataframe. It contains the name of the provider, the url to
            the gtfs file, and the bounding box of the area that the gtfs file covers.
        max_spacing: Maximum Allowed Spacing between two consecutive stops.

    Returns:
        The return value is a tuple of the form (filename,folder_path,df)
    """
    filename = row["provider"]
    url = row["urls.latest"]
    bounds = [
        [row["minimum_longitude"], row["minimum_latitude"]],
        [row["maximum_longitude"], row["maximum_latitude"]],
    ]
    print(filename)
    try:
        return pipeline_gtfs(filename, url, bounds, max_spacing)
    except Exception as e:
        traceback.print_exc()
        raise ValueError(f"Failed for {filename}") from e


def failed_pipeline(message: str, filename: str, folder_path: str) -> str:
    """
    "If the folder path exists, delete it and return the failure message."

    Args:
      message: The message to be returned
      filename: The name of the file that is being processed
      folder_path: The path to the folder where the file is located

    Returns:
      a string that is the concatenation of the message and the filename, indicating failure
    """

    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    return message + " : " + filename


def download_write_file(url: str, folder_path: str) -> str:
    """
    It takes a URL and a folder path as input, creates a new folder if it does not exist, downloads the
    file from the URL, and writes the file to the folder path

    Args:
      url: The URL of the GTFS file you want to download
      folder_path: The path to the folder where you want to save the GTFS file.

    Returns:
      The location of the file that was downloaded.
    """
    # Create a new directory if it does not exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    # Download file from URL
    gtfs_file_loc = os.path.join(folder_path, "gtfs.zip")

    try:
        r = requests.get(url, allow_redirects=True, timeout=300)
        # Write file locally
        file = open(gtfs_file_loc, "wb")
        file.write(r.content)
        file.close()
    except requests.exceptions.RequestException as e:
        print(e)
        raise ValueError(f"Failed to download {url}") from e
    return gtfs_file_loc
