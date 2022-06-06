def plot_func(df,filename,path,max_spacing):
    fig, ax = plt.subplots(figsize=(10,8),dpi=200)
    sns.distplot(df[df["distance"] <max_spacing]["distance"], bins = int(max_spacing/50), hist_kws={'weights': df[df["distance"] <max_spacing]["traversals"]}, kde=True,ax=ax)
    plt.xlim([0,max_spacing])
    plt.xlabel('Stop Spacing [m]')
    plt.ylabel('Density - Traversal Weighted')
    
    plt.title(filename.split('.')[0])
    plt.savefig(path+'/spacings.png', dpi=200)