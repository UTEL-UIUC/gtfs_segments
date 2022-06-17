from setuptools import setup, find_packages

VERSION = '0.0.3' 
DESCRIPTION = 'GTFS segments'
LONG_DESCRIPTION = 'A fast and efficient library to generate bus stop spacings'
REQUIREMENTS = ['geopandas',
                'scipy',
                'partridge',
                'statsmodels',
                'shapely',
                'numpy',
                'pandas',
                'seaborn',
                'matplotlib',
                'utm']
# Setting up
setup(
        name="gtfs_segments", 
        version=VERSION,
        author="Saipraneeth Devunuri",
        author_email="<sd37@illinois.edu>",
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        packages=find_packages(),
        install_requires=REQUIREMENTS, # add any additional packages that 
        # needs to be installed along with your package. Eg: 'caer'
        
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