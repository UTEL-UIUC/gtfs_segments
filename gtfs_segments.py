import os
import utm
import glob
import time
import shutil
import pygeos
import requests # To download gtfs files
import traceback # To print error traceback
import numpy as np
import pandas as pd
import seaborn as sns
import partridge as ptg
# from partridge_mod import partridge as ptg
import statsmodels.api as sm
import matplotlib.pyplot as plt
from shapely.geometry import Point,MultiPoint,LineString
from statsmodels.stats.weightstats import DescrStatsW
## Plot style
plt.style.use('ggplot')
from shapely import wkt
import geopandas as gpd
from shapely.ops import nearest_points,split,snap

def filter_bus_routes(routes, stops, stop_times, trips, shapes):
    ##Bus route_ids
    routes = routes[routes.route_type == 3]
    route_ids = routes.route_id
    stop_times = stop_times[stop_times.route_id.isin(route_ids)]
    trips = trips[trips.route_id.isin(route_ids)]

    stops_ids = stop_times.stop_id.unique()
    stops = stops[stops.stop_id.isin(stops_ids)]
    shape_ids = trips.shape_id.unique()
    shapes = shapes[shapes.shape_id.isin(shape_ids)]
    return routes, stops, stop_times, trips, shapes

def output_df(df,path,filename,max_spacing):
    ## Output to GeoJSON
    df.to_file(path+'/geojson.json', driver="GeoJSON")
    plot_func(df,filename,path,max_spacing)
    df = df[df["distance"] < max_spacing]
    s_df = df[['route_id','segment_id','stop_id1','stop_id2','distance','traversals','geometry']]
    s_df['start_point'] = s_df.geometry.apply(lambda x: Point(x.coords[0]))
    s_df['end_point'] = s_df.geometry.apply(lambda x: Point(x.coords[-1]))
    s_df['start_lon'] = s_df.geometry.apply(lambda x: x.coords[0][0])
    s_df['start_lat'] = s_df.geometry.apply(lambda x: x.coords[0][1])
    s_df['end_lon'] = s_df.geometry.apply(lambda x: x.coords[1][0])
    s_df['end_lat'] = s_df.geometry.apply(lambda x:x.coords[1][1])
    
    sg_df = s_df[['route_id','segment_id','stop_id1','stop_id2','distance','traversals','start_point','end_point','geometry']]
    ## Output With LS
    sg_df.to_csv(path+'/spacing_data_with_geometry.csv',index = False)
    d_df = s_df[['route_id','segment_id','stop_id1','stop_id2','start_lat','start_lon','end_lat','end_lon','distance','traversals']]
    ## Output without LS
    d_df.to_csv(path+'/spacing_data.csv',index = False)

def summary_stats(df,path,filename,b_day,max_spacing):
    weighted_stats = DescrStatsW(df["distance"], weights=df.traversals, ddof=0)
    quant = weighted_stats.quantile([0.25,0.5,0.75],return_pandas=False)
    percent_spacing = round(df[df["distance"] > max_spacing]['traversals'].sum()/df['traversals'].sum() *100,3)
    with open(path + '/summary.csv', 'w',encoding='utf-8') as f:
        f.write('Name,'+str(filename)+'\n')
        f.write('Busiest Day,'+str(b_day)+'\n')
#         f.write('Link,'+str(link)+'\n')
#         f.write('Min Latitude,'+str(bounds[0][1])+'\n')
#         f.write('Min Longitude,'+str(bounds[0][0])+'\n')
#         f.write('Max Latitude,'+str(bounds[1][1])+'\n')
#         f.write('Max Longitude,'+str(bounds[1][0])+'\n')
        f.write('Mean,'+str(round(weighted_stats.mean,3))+'\n')
        f.write('Std,'+str(round(weighted_stats.std,3))+'\n')
        f.write('25 % Quantile,'+str(round(quant[0],3))+'\n')
        f.write('50 % Quantile,'+str(round(quant[1],3))+'\n')
        f.write('75 % Quantile,'+str(round(quant[2],3))+'\n')
        f.write('No of Segments,'+str(len(df))+'\n')
        f.write('No of Routes,'+str(len(df.route_id.unique()))+'\n')
        f.write('No of Traversals,'+str(sum(df.traversals))+'\n')
        f.write('Max Spacing,'+str(max_spacing)+'\n')
        f.write('% Segments w/ spacing > max_spacing,'+str(percent_spacing))
        f.close()
    summary_df = pd.read_csv(path + '/summary.csv')
    summary_df.set_index(summary_df.columns[0],inplace=True)
    summary_df = summary_df.T
    summary_df.to_csv(path + '/summary.csv',index = False)
#         f.write('% Segments w/ spacing > max_spacing: '+str(round(len(df[df["distance"] > max_spacing])/len(df) *100,3)))

def pipeline_gtfs(filename,url,max_spacing):
    folder_path  = os.path.join('output_files',filename)
    isExist = os.path.exists(folder_path)
    if not isExist:
      # Create a new directory because it does not exist 
      os.makedirs(folder_path)
    
    ## Download file from URL
    r = requests.get(url, allow_redirects=True)
    gtfs_file_loc = folder_path+"/try_gtfs.zip"
    
    ## Write file locally
    file = open(gtfs_file_loc, "wb")
    file.write(r.content)
    file.close()
    
    ## read file using GTFS Fucntions
    routes, stops, stop_times, trips, shapes = gtfs.import_gtfs(gtfs_file_loc,busiest_date= True)
    busisest_day = ptg.read_busiest_date(gtfs_file_loc)[0]
#     print("Read Success")
    ## Filter only bus routes - route_type ==3
    routes, stops, stop_times, trips, shapes = filter_bus_routes(routes, stops, stop_times, trips, shapes)
#     print("Filter Success")
    
    if len(stop_times) == 0:
        print('No Bus Routes')
        isExist = os.path.exists(folder_path)
        if isExist:
            shutil.rmtree(folder_path)
        return 'No Bus Routes in '+filename
    
    ## Interpolate missing arrival and departure times
    stop_times['arrival_time'] = stop_times.groupby('trip_id')['arrival_time'].apply(lambda group: group.interpolate())
    stop_times['departure_time'] = stop_times.groupby('trip_id')['departure_time'].apply(lambda group: group.interpolate())
    
    ## Obtain Segments GDF and Segments Freq
    segments_gdf = gtfs.cut_gtfs(stop_times, stops, shapes)
    seg_freq = gtfs.segments_freq(segments_gdf, stop_times, routes, cutoffs = [0,24])
    df = merge_segment_freq(segments_gdf,seg_freq)
#     print("Cut Success")
    
    ## Output files and Stats
    output_df(df,folder_path,filename,max_spacing)
    summary_stats(df,folder_path,filename,busisest_day,url,bounds,max_spacing)
    return "Success for "+filename