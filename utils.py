import os
import shutil
import requests
import traceback
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
## Plot style
plt.style.use('ggplot')
from shapely.geometry import Point
from statsmodels.stats.weightstats import DescrStatsW

def plot_func(df,filename,path,max_spacing,save_fig = True):
    fig, ax = plt.subplots(figsize=(10,8),dpi=200)
    df_sub = df[df['distance']  < 3000]
    data = np.hstack([np.repeat(x, y) for x, y in zip(df_sub['distance'], df_sub.traversals)])
    sns.histplot(data,bins=int(max_spacing/50),kde=True,ax=ax)
    plt.xlim([0,max_spacing])
    plt.xlabel('Stop Spacing [m]')
    plt.ylabel('Density - Traversal Weighted')
    
    plt.title(filename.split('.')[0])
    if save_fig == True:
        plt.savefig(path+'/spacings.png', dpi=200)

def summary_stats(df,path,filename,b_day,link,bounds,max_spacing = 3000):
    weighted_stats = DescrStatsW(df["distance"], weights=df.traversals, ddof=0)
    quant = weighted_stats.quantile([0.25,0.5,0.75],return_pandas=False)
    percent_spacing = round(df[df["distance"] > max_spacing]['traversals'].sum()/df['traversals'].sum() *100,3)
    with open(path + '/summary.csv', 'w',encoding='utf-8') as f:
        f.write('Name,'+str(filename)+'\n')
        f.write('Busiest Day,'+str(b_day)+'\n')
        f.write('Link,'+str(link)+'\n')
        f.write('Min Latitude,'+str(bounds[0][1])+'\n')
        f.write('Min Longitude,'+str(bounds[0][0])+'\n')
        f.write('Max Latitude,'+str(bounds[1][1])+'\n')
        f.write('Max Longitude,'+str(bounds[1][0])+'\n')
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

def process(pipeline_gtfs,row,max_spacing):
    filename = row['file_name']
    url = row['urls.direct_download']
    bounds = [[row['location.bounding_box.minimum_longitude'],row['location.bounding_box.minimum_latitude']],[row['location.bounding_box.maximum_longitude'],row['location.bounding_box.maximum_latitude']]]
    print(filename)
#     pipeline_gtfs(filename,url,bounds,max_spacing)
    try:
        return pipeline_gtfs(filename,url,bounds,max_spacing)
    except:
        traceback.print_exc()
        folder_path  = os.path.join('output_files',filename)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        return "Failed for " + filename

def output_df(df,path,filename,max_spacing):
    ## Output to GeoJSON
    df.to_file(path+'/geojson.json', driver="GeoJSON")
    plot_func(df,filename,path,max_spacing)
    df = df[df["distance"] < max_spacing].reset_index(drop=True)
    s_df = df[['route_id','segment_id','stop_id1','stop_id2','distance','traversals','geometry']].copy()
    geom_list =  s_df.geometry.apply(lambda g: np.array(g.coords))
    s_df['start_point'] = [Point(g[0]).wkt for g in geom_list]
    s_df['end_point'] = [Point(g[-1]).wkt for g in geom_list]
    s_df['start_lon'] = [g[0][0] for g in geom_list]
    s_df['start_lat'] = [g[0][1] for g in geom_list]
    s_df['end_lon'] = [g[-1][0] for g in geom_list]
    s_df['end_lat'] = [g[-1][1] for g in geom_list]
    
    sg_df = s_df[['route_id','segment_id','stop_id1','stop_id2','distance','traversals','start_point','end_point','geometry']]
    ## Output With LS
    sg_df.to_csv(path+'/spacing_data_with_geometry.csv',index = False)
    d_df = s_df[['route_id','segment_id','stop_id1','stop_id2','start_lat','start_lon','end_lat','end_lon','distance','traversals']]
    ## Output without LS
    d_df.to_csv(path+'/spacing_data.csv',index = False)