# Welcome to GTFS Segments Documentation

<div align="center">
  <a href="https://github.com/UTEL-UIUC/gtfs_segments">
    <img src="https://raw.githubusercontent.com/UTEL-UIUC/gtfs_segments/main/images/logo.jpg" alt="Logo" width=200 height=200>
  </a>

<h3 align="center">GTFS Segments</h3>
  <p align="center">
    A fast and efficient library to generate bus stop spacings
    <br />
    <!-- <a href="https://github.com/UTEL-UIUC/gtfs_segments"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/UTEL-UIUC/gtfs_segments">View Demo</a>
    ·
    <a href="https://github.com/UTEL-UIUC/gtfs_segments/issues">Report Bug</a>
    ·
    <a href="https://github.com/UTEL-UIUC/gtfs_segments/issues">Request Feature</a> -->
  </p>
</div>


# About The Project
<!-- <div align="center">
  <img src="images/example.jpg" alt="map" width="400"/>
</div> -->

The `gtfs-segments` is a Python package that represents GTFS data for **buses** in a concise tabular manner using segments. The distribution of bus stop spacings can be viewed by generating histograms. The stop spacings can be visualized at the network, route, or segment level. The segment data can be exported to well known formats such as `.csv` or `.geojson` for further analysis. Additionally, the package provides commands to download the latest data from [@mobility data](https://mobilitydata.org/) sources.

The package condenses the raw GTFS data by considering the services offered only on the `busiest day`(in the data). More discussion on the interpretation of different weightings for stop spacings,  and the process in which the package condenses information can be seen in our [arXiv paper](https://arxiv.org/abs/2208.04394). The usage of the package is detailed in [documentation](https://utel-uiuc.github.io/gtfs_segments_docs/). The stop spacings dataset containing over 540 transit providers in the US generated using this package can be found on [Harvard Dataverse](https://doi.org/10.7910/DVN/SFBIVU).

 

<p align="right">(<a href="#top">back to top</a>)</p>

# Acknowledgments
* Parts of the code use the [Partridge](https://github.com/remix/partridge) library 
* Do check out [gtfs_functions](https://github.com/Bondify/gtfs_functions) which was an inspiration for this project
* Shoutout to [Mobility Data](https://mobilitydata.org) for compiling GTFS from around the globe and constantly maintaining them
