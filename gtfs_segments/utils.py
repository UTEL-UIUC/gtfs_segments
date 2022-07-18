import os
import shutil
import requests
import traceback
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
## Plot style
plt.style.use('ggplot')
from scipy.stats import gaussian_kde
from shapely.geometry import Point

def plot_hist(df,save_fig = False,show_mean = False,**kwargs):
    # df,file_path,filename,save_fig = True
    """Used to Plot Weighted Histogram of distributions

    Args:
        df (DataFrame): Final DataFrame  
        file_path (str): File Path
        title (str): Title of plot
        max_spacing (_type_): Maximum Allowed Spacing between two stops. Defaults to 3000.
        save_fig (bool, optional): Field to save the generated figure. Defaults to True.
    
    Returns:
        axis: A matplotlib axis
    """ 
    if "max_spacing" not in kwargs.keys():
        max_spacing = 3000
        print("Using max_spacing = 3000")
    else:
        max_spacing = kwargs['max_spacing']
    if "ax" in kwargs.keys():
        ax = kwargs['ax']
    else:
        fig, ax = plt.subplots(figsize=(8,6))
    df = df[df['distance'] < max_spacing]
    data = np.hstack([np.repeat(x, y) for x, y in zip(df['distance'], df.traversals)])
    plt.hist(data,range=(0,max_spacing),density = True,bins = int(max_spacing/50),fc=(0, 105/255, 160/255, 0.4),ec = "white",lw =0.8)
    x = np.arange(0,max_spacing,5)
    plt.plot(x,gaussian_kde(data)(x),lw = 1.5,color=(0, 85/255, 120/255, 1))
    # sns.histplot(data,binwidth=50,stat = "density",kde=True,ax=ax)
    plt.xlim([0,max_spacing])
    plt.xlabel('Stop Spacing [m]')
    plt.ylabel('Density - Traversal Weighted')
    plt.title("Histogram of Spacing")
    if show_mean:
        plt.axvline(np.mean(data), color='k', linestyle='dashed', linewidth=2)
        min_ylim, max_ylim = plt.ylim()
        plt.text(np.mean(data)*1.1, max_ylim*0.9, 'Mean: {:.0f}'.format(np.mean(data)),fontsize=12)
    if "title" in kwargs.keys():
        plt.title(kwargs['title'])
    if save_fig == True:
        assert "file_path" in kwargs.keys(), "Please pass in the `file_path`"
        plt.savefig(kwargs['file_path'], dpi=300)
    plt.show()
    plt.close(fig)
    return ax

def summary_stats(df,export = False,**kwargs):
    """Generate a report of summary statistics for the gtfs file

    Args:
        df (DataFrame): DataFrame
        file_path (str): File Path
        max_spacing (int, optional): Maximum Allowed Spacing between two consecutive stops. Defaults to 3000.
    """
    
    if "max_spacing" not in kwargs.keys():
        max_spacing = 3000
        print("Using max_spacing = 3000")
    else:
        max_spacing = kwargs['max_spacing']
    percent_spacing = round(df[df["distance"] > max_spacing]['traversals'].sum()/df['traversals'].sum() *100,3)
    df = df[df["distance"] > max_spacing]
    stop_weighted_mean = df.groupby(['segment_id','distance']).first().reset_index()["distance"].mean()
    route_weighted_mean = df.groupby(['route_id','segment_id','distance']).first().reset_index()["distance"].mean()
    weighted_data =  np.hstack([np.repeat(x, y) for x, y in zip(df['distance'], df.traversals)])
    
    df_dict = {
            'Stop Weighted Mean' : stop_weighted_mean,
            'Route Weighted Mean' : route_weighted_mean,
            'Traversal Weighted Mean': round(np.mean(weighted_data),3),
            'Traversal Weighted Std': round(np.std(weighted_data),3),
            'Traversal Weighted 25 % Quantile': round(np.quantile(weighted_data,0.25),3),
            'Traversal Weighted 50 % Quantile': round(np.quantile(weighted_data,0.50),3),
            'Traversal Weighted 75 % Quantile': round(np.quantile(weighted_data,0.75),3),
            'No of Segments':int(len(df)),
            'No of Routes':int(len(df.route_id.unique())),
            'No of Traversals':int(sum(df.traversals)),  
            'Max Spacing':int(max_spacing),
            '% Segments w/ spacing > max_spacing':percent_spacing}
    summary_df = pd.DataFrame([df_dict])
    # df.set_index(summary_df.columns[0],inplace=True)
    if export:
        assert "file_path" in kwargs.keys(), "Please pass in the `file_path`"
        summary_df.to_csv(kwargs['file_path'],index = False)
        print("Saved the summary in "+kwargs['file_path'])
    summary_df = summary_df.T
    return summary_df 
        
def export_segments(df,file_path,output_format, geometry = True):
    """Write the DataFrame as csv and geojson

    Args:
        df (DataFrame): DataFrame
        file_path (str): Output File Path
    """
    ## Output to GeoJSON
    if output_format == 'geojson':
        df.to_file(file_path+'.json', driver="GeoJSON")
    elif output_format == 'csv':
        s_df = df[['route_id','segment_id','stop_id1','stop_id2','distance','traversals','geometry']].copy()
        geom_list =  s_df.geometry.apply(lambda g: np.array(g.coords))
        s_df['start_point'] = [Point(g[0]).wkt for g in geom_list]
        s_df['end_point'] = [Point(g[-1]).wkt for g in geom_list]
        s_df['start_lon'] = [g[0][0] for g in geom_list]
        s_df['start_lat'] = [g[0][1] for g in geom_list]
        s_df['end_lon'] = [g[-1][0] for g in geom_list]
        s_df['end_lat'] = [g[-1][1] for g in geom_list]
        sg_df = s_df[['route_id','segment_id','stop_id1','stop_id2','distance','traversals','start_point','end_point','geometry']]
        if geometry == True:
            ## Output With LS
            sg_df.to_csv(file_path+'.csv',index = False)
        else:
            d_df = s_df[['route_id','segment_id','stop_id1','stop_id2','start_lat','start_lon','end_lat','end_lon','distance','traversals']]
            ## Output without LS
            d_df.to_csv(file_path+'.csv',index = False)


def process(pipeline_gtfs,row,max_spacing):
    """

    Args:
        pipeline_gtfs (function): Pipeline that will return processed dataframe
        row (row): row in sources_df
        max_spacing (int): Maximum Allowed Spacing between two consecutive stops.
    """
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
        return failed_pipeline("Failed",filename,folder_path)

def failed_pipeline(message,filename,folder_path):
    """Used to terminate the process and return error message

    Args:
        message (str): Failure cause
        filename (str): Filename
        folder_path (str): Folder path

    Returns:
        str: Failure Message
    """
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    return message + filename

def download_write_file(url,folder_path):
    """Function to download the gtfs file from url and save it in a folder

    Args:
        url (str): URL to download
        folder_path (str): Folder path

    Returns:
        str: Path to downloaded file
    """
    ## Download file from URL
    r = requests.get(url, allow_redirects=True)
    gtfs_file_loc = folder_path+"/gtfs.zip"
    
    ## Write file locally
    file = open(gtfs_file_loc, "wb")
    file.write(r.content)
    file.close()
    return gtfs_file_loc