import os
from statsmodels.stats.weightstats import DescrStatsW
import pandas as pd

def read_moblity_sources(abb_path,mob_path):
    """Read mobility Data csv and generate DataFrame

    Args:
        abb_path (str): path to state abbreviations csv 
        mob_path (_type_): path to sources csv

    Returns:
        DataFrame: Sources DataFrame
    """
    abb_df = pd.read_csv(abb_path)
    sources_df = pd.read_csv(mob_path)
    sources_df = sources_df[sources_df['location.country_code'] == 'US']
    sources_df = pd.merge(sources_df,abb_df,how='left',left_on='location.subdivision_name',right_on='State')
    sources_df = sources_df[~sources_df.Code.isna()]
    sources_df['location.municipality'] = sources_df['location.municipality'].astype("str")
    file_names = []
    for i,row in sources_df.iterrows():
        if row['location.municipality'] != 'nan':
            file_names.append(str(row['location.municipality'])+'-'+str(row['provider'])+'-'+str(row['Code']))
        else :
            file_names.append(str(row['location.subdivision_name'])+'-'+str(row['provider'])+'-'+str(row['Code']))
    sources_df['file_name'] = file_names
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
    weighted_stats = DescrStatsW(df["distance"], weights=df.traversals, ddof=0)
    quant = weighted_stats.quantile([0.25,0.5,0.75],return_pandas=False)
    percent_spacing = round(df[df["distance"] > max_spacing]['traversals'].sum()/df['traversals'].sum() *100,3)
    csv_path = os.path.join(folder_path,'summary.csv')
    
    df_dict = {"Name":filename,
            'Busiest Day': b_day,
            'Link': link,
            'Min Latitude': bounds[0][1],
            'Min Longitude': bounds[0][0],
            'Max Latitude': bounds[1][1],
            'Max Longitude': bounds[1][0],
            'Mean': round(weighted_stats.mean,3),
            'Std': round(weighted_stats.std,3),
            '25 % Quantile': round(quant[0],3),
            '50 % Quantile': round(quant[1],3),
            '75 % Quantile': round(quant[2],3),
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