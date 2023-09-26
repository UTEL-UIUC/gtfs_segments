import os
from setuptools import setup, find_packages

__version__ = '0.0.9' 
DESCRIPTION = 'GTFS segments'
with open("README.md", "r", encoding="utf8") as fh:
    LONG_DESCRIPTION = fh.read()
    
REQUIREMENTS = ['geopandas',
                'scipy',
                'shapely',
                'numpy',
                'pandas',
                'matplotlib',
                'utm',
                'contextily',
                'requests']

# Setting up
setup(
        name="gtfs_segments", 
        version=__version__,
        author="Saipraneeth Devunuri",
        author_email="<sd37@illinois.edu>",
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        long_description_content_type='text/markdown',
        packages=find_packages(),
        install_requires=REQUIREMENTS, # add any additional packages that 
        # needs to be installed along with your package. Eg: 'caer'
        url = "https://github.com/UTEL-UIUC/gtfs_segments",
        keywords=['python', 'gtfs', 'geodata'],
        classifiers= [
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Education",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 3",
            "Operating System :: MacOS :: MacOS X",
            "Operating System :: Microsoft :: Windows",
            "License :: OSI Approved :: MIT License",
        ]
)