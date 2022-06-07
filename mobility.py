import pandas as pd

def read_moblity_sources(abb_path,mob_path):
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