import rasterio
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, LineString
from rasterio.transform import rowcol
from tqdm import tqdm
import pandas as pd
import matplotlib.pyplot as plt
import contextily as cx

def extract_segment_elevations(raster_path, segments_gdf, sample_distance=100):
    """
    Extracts elevation data for GTFS segments using a raster elevation file.

    Args:
      raster_path: The file path to the raster elevation data.
      segments_gdf: A GeoDataFrame containing GTFS segments with 'geometry' and 'distance' columns.
      sample_distance: The distance in meters between elevation samples along each segment. Defaults to 100.

    Returns:
      A GeoDataFrame with the input segments and additional columns for elevation data:
      - start_elevation: The elevation at the start of the segment.
      - end_elevation: The elevation at the end of the segment.
      - min_elevation: The minimum elevation along the segment.
      - max_elevation: The maximum elevation along the segment.
      - avg_elevation: The average elevation along the segment.
      - elevation_diff: The difference between end and start elevations.
      - end_to_end_grade: The actual grade (in percent) from start to end of the segment.
      - avg_grade: The average actual grade (in percent) along the segment.
    """
    try:
        with rasterio.open(raster_path) as src:
            # Check if the raster file is valid
            if src.count != 1:
                raise ValueError(f"Expected 1 band in raster, but found {src.count}")
            
            if src.crs is None:
                raise ValueError("Raster file has no coordinate reference system (CRS) defined")
            
            # Check if the raster covers the extent of the segments
            segments_bounds = segments_gdf.total_bounds
            raster_bounds = src.bounds
            if not (raster_bounds.left <= segments_bounds[0] and
                    raster_bounds.bottom <= segments_bounds[1] and
                    raster_bounds.right >= segments_bounds[2] and
                    raster_bounds.top >= segments_bounds[3]):
                raise ValueError("Raster does not fully cover the extent of the segments")

            raster_data = src.read(1)

            # Check for valid elevation values
            if np.all(np.isnan(raster_data)):
                raise ValueError("Raster contains only NaN values")

            if np.all(raster_data == raster_data.flatten()[0]):
                raise ValueError("Raster contains only a single constant value")

            def get_elevations(points):
                xs, ys = zip(*[(p.x, p.y) for p in points])
                rows, cols = rowcol(src.transform, xs, ys)
                # Ensure rows and cols are numpy arrays for element-wise comparison
                rows, cols = np.array(rows), np.array(cols)
                valid_mask = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
                elevations = np.full(len(points), np.nan, dtype=np.float64)
                elevations[valid_mask] = raster_data[rows[valid_mask], cols[valid_mask]]
                return elevations

            def sample_elevations(line, total_length, sample_distance):
                num_samples = int(np.ceil(total_length / sample_distance)) + 1
                distances = np.linspace(0, total_length, num_samples)
                points = [Point(line.interpolate(d / total_length, normalized=True)) for d in distances]
                elevations = get_elevations(points)
                valid_mask = ~np.isnan(elevations)
                return elevations[valid_mask], distances[valid_mask]

            def process_segment(row):
                geometry = row["geometry"]
                if isinstance(geometry, LineString):
                    total_distance = row["distance"]  # in meters
                    elevations, distances = sample_elevations(geometry, total_distance, sample_distance)

                    if len(elevations) > 1:
                        start_elevation = elevations[0]
                        end_elevation = elevations[-1]
                        min_elevation = np.min(elevations)
                        max_elevation = np.max(elevations)
                        avg_elevation = np.mean(elevations)

                        elevation_diff = end_elevation - start_elevation
                        end_to_end_grade = (elevation_diff / total_distance) * 100  # Removed abs()
                        segment_grades = np.diff(elevations) / np.diff(distances) * 100  # Removed abs()
                        avg_grade = np.average(segment_grades) if segment_grades.size > 0 else 0

                        return (
                            start_elevation,
                            end_elevation,
                            min_elevation,
                            max_elevation,
                            avg_elevation,
                            elevation_diff,
                            end_to_end_grade,
                            avg_grade,
                        )

                return None, None, None, None, None, None, None, None

            tqdm.pandas(desc="Processing segments")
            results = segments_gdf.progress_apply(process_segment, axis=1)

            segments_gdf[
                [
                    "start_elevation",
                    "end_elevation",
                    "min_elevation",
                    "max_elevation",
                    "avg_elevation",
                    "elevation_diff",
                    "end_to_end_grade",
                    "avg_grade",
                ]
            ] = pd.DataFrame(results.tolist(), index=segments_gdf.index)

    except rasterio.errors.RasterioIOError as e:
        raise IOError(f"Error opening raster file: {e}")

    return segments_gdf

def view_spacings_with_grade(
    gdf: gpd.GeoDataFrame,
    grade_column: str = "avg_grade",
    abs_grade: bool = False,
    basemap: bool = True,
    map_provider: str = cx.providers.CartoDB.Positron,
    dpi: int = 300,
    figsize: tuple = (12, 8),
    cmap: str = "RdYlBu_r",
    vmin: float = None,
    vmax: float = None,
) -> plt.Figure:
    """
    Visualizes GTFS segments with their grades using a color gradient.

    Args:
      gdf: GeoDataFrame containing the segments with grade information.
      grade_column: Column name for the grade to visualize. Defaults to "avg_grade"
      abs_grade: Whether to use the absolute value of the grade. Defaults to False.
      basemap: Whether to add a basemap to the plot. Defaults to True.
      map_provider: The map provider for the basemap. Defaults to CartoDB Positron.
      dpi: The resolution of the plot. Defaults to 300.
      figsize: The size of the figure. Defaults to (12, 8).
      cmap: The colormap to use for the grade visualization. Defaults to "RdYlBu_r".
      vmin: The minimum value for the colormap scale. If None, uses the data minimum.
      vmax: The maximum value for the colormap scale. If None, uses the data maximum.

    Returns:
      A matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    # Set vmin and vmax if not provided
    if vmin is None:
        vmin = gdf[grade_column].min()
    if vmax is None:
        vmax = gdf[grade_column].max()

    # Plot segments with color based on grade
    if abs_grade:
        gdf[grade_column] = gdf[grade_column].abs()
    gdf.plot(
        column=grade_column,
        ax=ax,
        cmap=cmap,
        linewidth=1.5,
        vmin=vmin,
        vmax=vmax,
        legend=True,
        legend_kwds={
            "label": f"{grade_column.replace('_', ' ').title()} (%)",
            "orientation": "vertical",
            "shrink": 0.8,
        },
    )

    # Add basemap if requested
    if basemap:
        cx.add_basemap(ax, crs=gdf.crs, source=map_provider, attribution_size=8)

    # Set plot title and remove axis labels
    ax.set_title(f"GTFS Segments Colored by {grade_column.replace('_', ' ').title()}", fontsize=16)
    ax.set_axis_off()

    # Adjust layout
    plt.tight_layout()
    
    # Return the figure without displaying it
    return ax
