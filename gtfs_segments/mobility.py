import os
import re
from .utils import *
import pandas as pd
import numpy as np

MOBILITY_SOURCES_link = "https://bit.ly/catalogs-csv"
ABBREV_link = 'https://raw.githubusercontent.com/UTEL-UIUC/gtfs_segments/main/state_abbreviations.json'

def fetch_gtfs_source(place ='ALL'):
    """Read mobility Data csv and generate DataFrame

    Returns:
        DataFrame: Sources DataFrame
    """
    abb_df = pd.read_json(ABBREV_link)
    sources_df = pd.read_csv(MOBILITY_SOURCES_link)
    sources_df = sources_df[sources_df['location.country_code'] == 'US']
    sources_df = sources_df[sources_df['data_type'] == 'gtfs']
    sources_df = pd.merge(sources_df,abb_df,how='left',left_on='location.subdivision_name',right_on='state')
    sources_df = sources_df[~sources_df.state_code.isna()]
    sources_df['location.municipality'] = sources_df['location.municipality'].astype("str")
    sources_df.drop(['entity_type','mdb_source_id','data_type','location.country_code','note',
                     'static_reference','urls.direct_download','urls.authentication_type','urls.license','location.bounding_box.extracted_on', 'urls.authentication_info','urls.api_key_parameter_name','features'],axis=1,inplace=True)
    file_names = []
    for i,row in sources_df.iterrows():
        if row['location.municipality'] != 'nan':
            if len(sources_df[(sources_df['location.municipality'] == row['location.municipality']) & (sources_df['provider'] == row['provider'])]) <= 1:
                f_name = str(row['location.municipality'])+'-'+str(row['provider'])+'-'+str(row['state_code'])
            else:
                f_name = str(row['location.municipality'])+'-'+str(row['provider'])+'-'+str(row['name'])+'-'+str(row['state_code'])
        else:
            if len(sources_df[(sources_df['location.subdivision_name'] == row['location.subdivision_name']) & (sources_df['provider'] == row['provider'])]) <= 1:
                f_name = str(row['location.subdivision_name'])+'-'+str(row['provider'])+'-'+str(row['state_code'])
            else:
                f_name =str(row['location.subdivision_name'])+'-'+str(row['provider'])+'-'+str(row['name'])+'-'+str(row['state_code'])
        f_name = f_name.replace('/','').strip()
        file_names.append(f_name)
    sources_df.drop(['provider','location.municipality','location.subdivision_name','name','state_code','state'],axis=1,inplace=True)
    sources_df.insert(0,'provider',file_names)
    sources_df.columns = sources_df.columns.str.replace('location.bounding_box.',"",regex=True))
    if place == 'ALL':
        return sources_df
    else:
        sources_df = sources_df[sources_df.apply(lambda row: row.astype(str).str.contains(place.lower(), case=False).any(), axis=1)]
        if len(sources_df) == 0:
            return "No sources found for the given place"
        else:
            return sources_df


def summary_stats_mobility(df,folder_path,filename,b_day,link,bounds,max_spacing = 3000,export = False):
    """Generate a report of summary statistics for the gtfs file

    Args:
        df (DataFrame): DataFrame
        folder_path (str): Folder Path
        filename (str): Filename
        b_day (date): Busiest Day
        link (str): Download URL
        bounds (tuple): Lat Long bounds
        max_spacing (int, optional): Maximum Allowed Spacing between two consecutive stops. Defaults to 3000.
    """
    percent_spacing = round(df[df["distance"] > max_spacing]['traversals'].sum()/df['traversals'].sum() *100,3)
    df = df[df["distance"] <= max_spacing]
    csv_path = os.path.join(folder_path,'summary.csv')
    stop_weighted_mean = df.groupby(['segment_id','distance']).first().reset_index()["distance"].mean()
    route_weighted_mean = df.groupby(['route_id','segment_id','distance']).first().reset_index()["distance"].mean()
    weighted_data =  np.hstack([np.repeat(x, y) for x, y in zip(df['distance'], df.traversals)])
    df_dict = {"Name":filename,
            'Busiest Day': b_day,
            'Link': link,
            'Min Latitude': bounds[0][1],
            'Min Longitude': bounds[0][0],
            'Max Latitude': bounds[1][1],
            'Max Longitude': bounds[1][0],
            'Segment Weighted Mean' : stop_weighted_mean,
            'Route Weighted Mean' : route_weighted_mean,
            'Traversal Weighted Mean': round(np.mean(weighted_data),3),
            'Traversal Weighted Std': round(np.std(weighted_data),3),
            'Traversal Weighted 25 % Quantile': round(np.quantile(weighted_data,0.25),3),
            'Traversal Weighted 50 % Quantile': round(np.quantile(weighted_data,0.5),3),
            'Traversal Weighted 75 % Quantile': round(np.quantile(weighted_data,0.75),3),
            'No of Segments':len(df),
            'No of Routes':len(df.route_id.unique()),
            'No of Traversals':sum(df.traversals),  
            'Max Spacing':max_spacing,
            '% Segments w/ spacing > max_spacing':percent_spacing}
    summary_df = pd.DataFrame([df_dict])
    # df.set_index(summary_df.columns[0],inplace=True)
    if export:
        summary_df.to_csv(csv_path,index = False)
        return "Saved the summary.csv in "+folder_path
    else:
       summary_df = summary_df.T
       return summary_df
   
def download_latest_data(out_folder_path,sources_df):
    for i,row in sources_df.iterrows():
        try:
            download_write_file(row['urls.latest'],os.path.join(out_folder_path,row['provider']))
        except:
            continue
    print("Downloaded the latest data")    
    