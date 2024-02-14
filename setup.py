from setuptools import find_packages, setup

__version__ = "0.2.0"
DESCRIPTION = "GTFS segments"
with open("README.md", "r", encoding="utf8") as fh:
    LONG_DESCRIPTION = fh.read()

REQUIREMENTS = [
    "geopandas",
    "scipy",
    "shapely",
    "numpy",
    "pandas",
    "matplotlib",
    "utm",
    "contextily",
    "requests",
    "isoweek",
    "faust-cchardet",
    "charset_normalizer",
    "folium",
    "thefuzz",
]

# Setting up
setup(
    name="gtfs_segments",
    version=__version__,
    author="Saipraneeth Devunuri",
    author_email="<sd37@illinois.edu>",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=REQUIREMENTS,
    url="https://github.com/UTEL-UIUC/gtfs_segments",
    keywords=["python", "gtfs", "geodata"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "License :: OSI Approved :: MIT License",
    ],
)
