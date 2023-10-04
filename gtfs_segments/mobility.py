import os
from .utils import download_write_file
import pandas as pd
import numpy as np

MOBILITY_SOURCES_link = "https://bit.ly/catalogs-csv"
ABBREV_link = "https://raw.githubusercontent.com/UTEL-UIUC/gtfs_segments/main/state_abbreviations.json"


def fetch_gtfs_source(place="ALL", active=True) -> pd.DataFrame:
    """
    It reads the mobility data sources csv file and generates a dataframe with the sources that are of
    type gtfs and are from the US

    Args:
      place: The place you want to get the GTFS data for. This can be a city, state, or country.
    Defaults to ALL. Defaults to ALL
      [Optional] active: If True, it will only download active feeds. If False, it will download all feeds.
    Defaults to True

    Returns:
      A dataframe with sources
    """
    abb_df = pd.read_json(ABBREV_link)
    sources_df = pd.read_csv(MOBILITY_SOURCES_link)
    sources_df = sources_df[sources_df["location.country_code"] == "US"]
    sources_df = sources_df[sources_df["data_type"] == "gtfs"]
    # Download only active feeds
    if active:
        sources_df = sources_df[sources_df["status"].isin(["active", np.NAN])]
        sources_df.drop(["status"], axis=1, inplace=True)
    sources_df = pd.merge(
        sources_df,
        abb_df,
        how="left",
        left_on="location.subdivision_name",
        right_on="state",
    )
    sources_df = sources_df[~sources_df.state_code.isna()]
    sources_df["location.municipality"] = sources_df["location.municipality"].astype(
        "str"
    )
    sources_df.drop(
        [
            "entity_type",
            "mdb_source_id",
            "data_type",
            "location.country_code",
            "note",
            "static_reference",
            "urls.direct_download",
            "urls.authentication_type",
            "urls.license",
            "location.bounding_box.extracted_on",
            "urls.authentication_info",
            "urls.api_key_parameter_name",
            "features",
        ],
        axis=1,
        inplace=True,
    )
    file_names = []
    for i, row in sources_df.iterrows():
        if row["location.municipality"] != "nan":
            if (
                len(
                    sources_df[
                        (
                            sources_df["location.municipality"]
                            == row["location.municipality"]
                        )
                        & (sources_df["provider"] == row["provider"])
                    ]
                )
                <= 1
            ):
                f_name = (
                    str(row["location.municipality"])
                    + "-"
                    + str(row["provider"])
                    + "-"
                    + str(row["state_code"])
                )
            else:
                f_name = (
                    str(row["location.municipality"])
                    + "-"
                    + str(row["provider"])
                    + "-"
                    + str(row["name"])
                    + "-"
                    + str(row["state_code"])
                )
        else:
            if (
                len(
                    sources_df[
                        (
                            sources_df["location.subdivision_name"]
                            == row["location.subdivision_name"]
                        )
                        & (sources_df["provider"] == row["provider"])
                    ]
                )
                <= 1
            ):
                f_name = (
                    str(row["location.subdivision_name"])
                    + "-"
                    + str(row["provider"])
                    + "-"
                    + str(row["state_code"])
                )
            else:
                f_name = (
                    str(row["location.subdivision_name"])
                    + "-"
                    + str(row["provider"])
                    + "-"
                    + str(row["name"])
                    + "-"
                    + str(row["state_code"])
                )
        f_name = f_name.replace("/", "").strip()
        file_names.append(f_name)
    sources_df.drop(
        [
            "provider",
            "location.municipality",
            "location.subdivision_name",
            "name",
            "state_code",
            "state",
        ],
        axis=1,
        inplace=True,
    )
    sources_df.insert(0, "provider", file_names)
    sources_df.columns = sources_df.columns.str.replace(
        "location.bounding_box.", "", regex=True
    )
    sources_df.rename(
        columns={
            "minimum_longitude": "min_lon",
            "maximum_longitude": "max_lon",
            "minimum_latitude": "min_lat",
            "maximum_latitude": "max_lat",
            "urls.latest": "url",
        },
        inplace=True,
    )
    if place == "ALL":
        return sources_df.reset_index(drop=True)
    else:
        sources_df = sources_df[
            sources_df.apply(
                lambda row: row.astype(str)
                .str.contains(place.lower(), case=False)
                .any(),
                axis=1,
            )
        ]
        if len(sources_df) == 0:
            return "No sources found for the given place"
        else:
            return sources_df.reset_index(drop=True)


def summary_stats_mobility(
    df, folder_path, filename, b_day, link, bounds, max_spacing=3000, export=False
)-> pd.DataFrame:
    """
    It takes in a dataframe, a folder path, a filename, a busiest day, a link, a bounding box, a max
    spacing, and a boolean for exporting the summary to a csv.

    It then calculates the percentage of segments that have a spacing greater than the max spacing. It
    then filters the dataframe to only include segments with a spacing less than the max spacing. It
    then calculates the segment weighted mean, route weighted mean, traversal weighted mean, traversal
    weighted standard deviation, traversal weighted 25th percentile, traversal weighted 50th percentile,
    traversal weighted 75th percentile, number of segments, number of routes, number of traversals, and
    the max spacing. It then creates a dictionary with all of the above values and creates a dataframe
    from the dictionary. It then exports the dataframe to a csv if the export boolean is true. If the
    export boolean is false, it transposes the dataframe and returns it.

    Args:
      df: the dataframe containing the mobility data
      folder_path: The path to the folder where you want to save the summary.csv file.
      filename: The name of the file you want to save the data as.
      b_day: The busiest day of the week
      link: The link of the map you want to use.
      bounds: The bounding box of the area you want to analyze.
      max_spacing: The maximum distance between two stops that you want to consider. Defaults to 3000
      export: If True, the summary will be saved as a csv file in the folder_path. If False, the summary
    will be returned as a dataframe. Defaults to False

    Returns:
      A dataframe with the summary statistics of the mobility data.
    """
    percent_spacing = round(
        df[df["distance"] > max_spacing]["traversals"].sum()
        / df["traversals"].sum()
        * 100,
        3,
    )
    df = df[df["distance"] <= max_spacing]
    csv_path = os.path.join(folder_path, "summary.csv")
    seg_weighted_mean = (
        df.groupby(["segment_id", "distance"])
        .first()
        .reset_index()["distance"]
        .mean()
        .round(2)
    )
    seg_weighted_median = (
        df.groupby(["segment_id", "distance"])
        .first()
        .reset_index()["distance"]
        .median()
        .round(2)
    )
    route_weighted_mean = (
        df.groupby(["route_id", "segment_id", "distance"])
        .first()
        .reset_index()["distance"]
        .mean()
        .round(2)
    )
    route_weighted_median = (
        df.groupby(["route_id", "segment_id", "distance"])
        .first()
        .reset_index()["distance"]
        .median()
        .round(2)
    )
    weighted_data = np.hstack(
        [np.repeat(x, y) for x, y in zip(df["distance"], df.traversals)]
    )
    df_dict = {
        "Name": filename,
        "Busiest Day": b_day,
        "Link": link,
        "Min Latitude": bounds[0][1],
        "Min Longitude": bounds[0][0],
        "Max Latitude": bounds[1][1],
        "Max Longitude": bounds[1][0],
        "Segment Weighted Mean": seg_weighted_mean,
        "Route Weighted Mean": route_weighted_mean,
        "Traversal Weighted Mean": round(np.mean(weighted_data), 3),
        "Segment Weighted Median": seg_weighted_median,
        "Route Weighted Median": route_weighted_median,
        "Traversal Weighted Median": round(np.median(weighted_data), 2),
        "Traversal Weighted Std": round(np.std(weighted_data), 3),
        "Traversal Weighted 25 % Quantile": round(np.quantile(weighted_data, 0.25), 3),
        "Traversal Weighted 50 % Quantile": round(np.quantile(weighted_data, 0.5), 3),
        "Traversal Weighted 75 % Quantile": round(np.quantile(weighted_data, 0.75), 3),
        "No of Segments": len(df.segment_id.unique()),
        "No of Routes": len(df.route_id.unique()),
        "No of Traversals": sum(df.traversals),
        "Max Spacing": max_spacing,
        "% Segments w/ spacing > max_spacing": percent_spacing,
    }
    summary_df = pd.DataFrame([df_dict])
    if export:
        summary_df.to_csv(csv_path, index=False)
        return "Saved the summary.csv in " + folder_path
    else:
        summary_df = summary_df.T
        return summary_df


def download_latest_data(sources_df, out_folder_path) -> None:
    """
    It iterates over the rows of the dataframe, and for each row, it tries to download the file from the
    URL in the `urls.latest` column, and write it to the folder specified in the `provider` column

    Args:
      sources_df: This is the dataframe that contains the urls for the data.
      out_folder_path: The path to the folder where you want to save the data.
    """
    for i, row in sources_df.iterrows():
        try:
            download_write_file(
                row["url"], os.path.join(out_folder_path, row["provider"])
            )
        except Exception as e:
            print("Error downloading the file for " + row["provider"] + " : " + str(e))
            continue
    print("Downloaded the latest data")
