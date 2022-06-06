import os
import glob
import time
import shutil
import requests # To download gtfs files
import traceback # To print error traceback
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import partridge as ptg
import statsmodels.api as sm
from shapely.geometry import Point
from statsmodels.stats.weightstats import DescrStatsW
##GTFS
# !pip install gtfs_functions
import gtfs_modified as gtfs
## Plot style
plt.style.use('ggplot')