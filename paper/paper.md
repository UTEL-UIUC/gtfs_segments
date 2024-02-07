---
title: 'GTFS Segments: A fast and efficient library to generate bus stop spacings'
tags:
  - Python
  - GTFS
  - Public Transit
  - Stop Spacings
  - Bus Stops
authors:
  - name: Saipraneeth Devunuri
    orcid: 0000-0002-5911-4681
    corresponding: true 
    equal-contrib: true
    affiliation: 1 
  - name: Lewis Lehe
    orcid: 0000-0001-8029-1706
    equal-contrib: false
    affiliation: 1 
affiliations:
 - name: Department of Civil and Environmental Engineering, University of Illinois Urbana-Champaign
   index: 1

date: 25 September 2023
bibliography: paper.bib
header-includes: |
    \usepackage{caption}
    \usepackage{subcaption}
---

# Summary

The GTFS Segments (gtfs-segments) library is an open-source Python toolkit for computing, visualizing and analyzing bus stop spacings: the distance a transit bus travels between stops. The library reads General Transit Feed Specification (GTFS) data, snaps bus stops to points along routes, divides routes into segments (the pieces of routes between two stops), and then produces a `GeoDataFrame` containing information about each segment. The library also features several functions that act on this GeoDataFrame. It can produce summary statistics of the spacings for a given network, using various weighting schemes (i.e., weighting by frequency of service), as well as histograms of spacings that display their full distribution. In addition to network-level statistics, the package can also compute statistics for each route, such as its length, headway, speed, and average stop spacing. It can draw maps of networks, routes, or segments over a basemap---which allows the user to manually validate data. The segments DataFrame can be exported to `.csv` and `.geojson` files. The package can fetch the most up-to-date GTFS data from Mobility Data[@MobData2023] repositories for user convenience.


# Statement of need

The choice of bus stop spacing involves a tradeoff between accessibility and speed: wider spacings mean passengers must travel farther to/from stops, but they allow the bus to move faster[@Wu2022]. Many US transit agencies have recently carried out *stop consolidation* campaigns that systematically remove stops, due partly to the perception US stop spacings are much narrower than those abroad. However, there are no reliable data sources to obtain current stop spacings despite the wide adoption of General Transit Feed Specification (GTFS) [@Voulgaris2023Predictors], because GTFS does not include data on stop spacings directly. Spacings must be computed from route shape geometries, stop locations, and stop sequences. A challenge is that stop locations are not placed on top of route shapes and therefore must be somehow projected onto the route's `LINESTRING`. To make spacings available for analysis, `gtfs-segments` use k-dimensional spatial trees and k-nearest neighbor heuristics to snap stops to routes and divide routes into segments for computation of spacings, as described below.

`gtfs-segments` was designed for researchers, transit planners, students and anyone interested in bus networks. The package has been used in several scholarly articles [@devunuri2023bus; @devunuri2023chatgpt; @lehe4135394bus] and to create databases of spacings for over 550 agencies in the US [@DVN/SFBIVU_2022] and 80 agencies in Canada[@DVN/QFTAPM_2023]. Several transit agencies, such as Regional Transportation District Denver (RTD- Denver), have used the package to visualize the effects of their bus stop consolidation efforts. Filtering functions allow the user to explore datasets, identify errors and compute specialized statistics.

# Functionality

The `gtfs-segments` package has four main functionalities: (1) Acquiring GTFS feeds (2) Computing segments (3) Visualizing stop spacings (4) Calculating stop spacing summary statistics. Each of these functionalities is further detailed below.

## Acquiring GTFS feeds

GTFS feeds undergo frequent changes, and obtaining the latest feed is essential to calculate up-to-date stop spacings. The package provides a convenient functionality to source and download over 1100 GTFS active feeds from across the world (over 550 in the US and 80 in Canada) from Mobility Database Catalogs[@MobData2023]. The package includes keyword search functionality to search for GTFS feeds using the name of the provider (full name or abbreviation) or the place (city or state (applicable only for the US)). Additionally, to account for typographical errors, the package also implements a fuzzy search feature by matching sub-strings based on [Levenshtein distance](https://en.wikipedia.org/wiki/Levenshtein_distance) algorithm, which is used popularly in text auto-correct.

## Computing segments

A `segment` is defined by three elements: (i) a start stop, (ii) an end stop and (iii) the path that the bus travels along the route in between the two consecutive stops. The segments are computed using route shape geometries and stop locations included in GTFS data. Packages such as `gtfs2gps`[@pereira2023exploring] and `gtfs_functions`[@Toso2023] can compute segments, but this package does so in computationally-efficient way and includes a new way to account for *errors* in the GTFS feed.

Firstly, unlike `gtfs2gps`, we filter the feed to use trips scheduled on the busiest day alone. We also filter unusual trips on the busiest day such as trips with considerably fewer traversals and trips added due to an exception in the service on `busiest_day`. Next, while processing the feed, we group trips based on their respective route shapes and process a representative trip in the group instead of all trips. While computing segments, we parallelize several intermediate steps on multiple CPU cores. However, without parallel processing, the `gtfs_segments` is faster than its alternatives at computing segments on most feeds. \autoref{tab:comparison} shows a comparison of average processing times (averaged over 3 independent runs) for `gtfs2gps`, `gtfs_functions`, and `gtfs_segmnets` packages. The experiments were run with an `Intel(R) Core(TM) i9-10920X` processor at 3.50GHz with 12 hyperthreaded CPU cores and 64 GB RAM, running on Windows. As of February 2024, the most recent GTFS feeds of the respective agencies are tested. The results demonstrate that our package has the best processing time for all but `TriMet` feed, which has higher than usual out-of-order stops.

\begin{table}[!hp]
\resizebox{\textwidth}{!}{%
\begin{tabular}{llc|cccc|}
\cline{4-7}
\multicolumn{3}{l|}{} &
  \multicolumn{4}{c|}{Average Processing Time (seconds) {[}n=3{]}} \\ \hline
\multicolumn{3}{|r|}{\textit{Package}} &
  \multicolumn{1}{c|}{\textit{gtfs2gps}} &
  \multicolumn{1}{c|}{\textit{gtfs\_functions}} &
  \multicolumn{2}{c|}{\textit{gtfs\_segments}} \\ \hline
\multicolumn{3}{|r|}{\textit{Parallel Processing}} &
  \multicolumn{1}{c|}{\textit{Y}} &
  \multicolumn{1}{c|}{\textit{N}} &
  \multicolumn{1}{c|}{\textit{N}} &
  \textit{Y} \\ \hline
\multicolumn{1}{|l|}{\textbf{Agency}} &
  \multicolumn{1}{l|}{\textbf{City}} &
  \textbf{\begin{tabular}[c]{@{}c@{}}File \\ Size\\  (MB)\end{tabular}} &
  \multicolumn{1}{c|}{v2.1.0} &
  \multicolumn{1}{c|}{v2.3.0} &
  \multicolumn{2}{c|}{v2.1.0} \\ \hline
\multicolumn{1}{|l|}{TheRide} &
  \multicolumn{1}{l|}{Ann Arbor} &
  1.5 &
  \multicolumn{1}{c|}{-} &
  \multicolumn{1}{c|}{7.0} &
  \multicolumn{1}{c|}{4.9} &
  \textbf{4.6} \\ \hline
\multicolumn{1}{|l|}{\begin{tabular}[c]{@{}l@{}}Capital \\ Metro\end{tabular}} &
  \multicolumn{1}{l|}{Austin} &
  6.8 &
  \multicolumn{1}{c|}{330.4} &
  \multicolumn{1}{c|}{-} &
  \multicolumn{1}{c|}{23.8} &
  \textbf{22.9} \\ \hline
\multicolumn{1}{|l|}{SFMTA} &
  \multicolumn{1}{l|}{\begin{tabular}[c]{@{}l@{}}San \\ Francisco\end{tabular}} &
  10.0 &
  \multicolumn{1}{c|}{1313.1} &
  \multicolumn{1}{c|}{15.8} &
  \multicolumn{1}{c|}{15.7} &
  \textbf{13.7} \\ \hline
\multicolumn{1}{|l|}{MBTA} &
  \multicolumn{1}{l|}{Boston} &
  14.9 &
  \multicolumn{1}{c|}{959.3} &
  \multicolumn{1}{c|}{47.1} &
  \multicolumn{1}{c|}{41.5} &
  \textbf{37.4} \\ \hline
\multicolumn{1}{|l|}{SEPTA} &
  \multicolumn{1}{l|}{Philadelphia} &
  21.3 &
  \multicolumn{1}{c|}{-} &
  \multicolumn{1}{c|}{95.0} &
  \multicolumn{1}{c|}{73.0} &
  \textbf{60.0} \\ \hline
\multicolumn{1}{|l|}{TriMet} &
  \multicolumn{1}{l|}{Portland} &
  35.5 &
  \multicolumn{1}{c|}{1255.3} &
  \multicolumn{1}{c|}{\textbf{59.1}} &
  \multicolumn{1}{c|}{67.0} &
  65.0 \\ \hline
\end{tabular}%
}
\caption{Comparison of average processing times for gtfs2gps, gtfs\_functions and gtfs\_segments. An empty value (-) indicates that the respective package could not compute segments for the Feed}\label{tab:comparison}
\end{table}

Lastly, we incorporate a new way to account for cases when the reported stop locations are misaligned with the route shapes. \autoref{fig:example} provides some example cases where a stop is equidistant from multiple points on a route. Thus, projecting the stop onto the route or snapping to the nearest geo-coordinate (lat, lon) may produce errors, such as stops that are out-of-order or stops being snapped far from their locations. Also, the time complexity of projection or snapping is $O(mn)$ using brute force for `m` geo-coordinates that represent the route shape and `n` stops that have to be projected. 

\begin{figure}[!h]
  \centering
  \includegraphics[width =0.8\textwidth]{snapping_difficulty.jpg}
  \caption{Example route shapes with stop locations that are equidistant from multiple points along the route.}\label{fig:example}
\end{figure}


`gtfs-segments` overcomes these challenges by increasing the route resolution (i.e., adding points in between geo-coordinates), using spatial k-d trees, and using more than one nearest neighbor. The increase in resolution allows stops to be snapped to nearby points. k-d trees[@maneewongvatana1999analysis] reduce the time complexity to $O(nlog(m))$ and make it possible to compare among several snapping points without added computation. \autoref{fig:interpolate} shows a difficult example route. In the first panel, snapping to the nearest point produces out-of-order stops (3/4/2) and stop 5 is snapped far away from its location. In the second panel, increased resolution fixes 5's location problem but the ordering problem persists. In the third panel, we use the `k=3` nearest neighbors and thus find a proper ordering. Once every stop has been snapped to a geo-coordinate on the route shape, the shape is segmented between stops and each segment is represented by a `LineString` for entry in the GeoDataFrame. In fact, `gtfs_segments` starts with `k=3` for the neighbors and doubles `k` until we find the correct sequence of stops or remove the corresponding trip. On average, fewer than 1% of trips fail, which can be manually corrected and validated by agencies. 

![Improvement in snapping due to an increase in resolution and suing k-nearest neighbors. Adapted from "Bus Stop Spacings Statistics: Theory and Evidence" [@devunuri2023bus].\label{fig:interpolate}](interpolation.jpg){ width=80% }

## Visualizing stop spacings

The computed segments are output as a `GeoDataFrame` which consists of the segments geometries represented using `LineString` or `MultiLineString`. The segments can be filtered based on the attributes such as distance, speed, route_id or traversals that are available in the dataframe.  These segments can be viewed using the `.plot()` method or can be imported into any GIS software for additional customization. The package natively provides functionality to view the stop spacings at different levels along with basemaps and stops overlayed. \autoref{fig:view_spacings} demonstrates the three hierarchical levels of viewing spacings: network, route, and segment. The network level pertains to the whole GTFS feed whereas the route and segment focus on the respective routes or segments alone. Within each level of display, the sub-levels can be highlighted. For example, at a network level, a particular route/ group of routes or a route and segment can be of focus. While each level provides a different perspective and attention to detail, the package also provides an interactive map feature that lets the user control the level of detail and select any segment of interest.

\begin{figure}[!hp]
\begin{subfigure}[]{0.45\textwidth}
  \includegraphics{network_vis.jpg}
  \caption{Network}
  \end{subfigure}
\begin{subfigure}[]{0.22\textwidth}
  \includegraphics[width=\textwidth]{route_vis.jpg}
  \caption{Route}
\end{subfigure}
\begin{subfigure}[]{0.25\textwidth}
  \centering
  \includegraphics[width=0.3\textwidth]{segment_vis.jpg}
  \caption{Segment}
\end{subfigure}
\caption{Visualize stop spacings at network, route or segment level. SFMTA GTFS feed was used to generate these.}\label{fig:view_spacings}
\end{figure}

The package also provides a few other visualization features that using the individual segments obtained. The user can generate a heatmap (interactive and static) by assigning a color to the segment based on the value of the column of interest. The distance-based heatmap provides an overview of the distribution and density of stops and stop spacings. The colormap helps the user identify the hotspot of interest. For example \autoref{fig:seq} uses a sequential colormap to represent wide spacings in red which are not convenient from a user's perspective.  An alternative is to use a divergent colormap (see \autoref{fig:div}) which highlights spacings that are on extremes of the tradeoff between accessibility and speed. Besides heatmap, a full distribution of stop spacings can be obtained as a histogram,see \autoref{fig:hist}.  A histogram helps to identify the most frequent spacing and outliers. It can also reveal if the spacings are distributed evenly and around the mean.  For policymakers and planners, understanding the distribution of stop spacings can inform broader strategic decisions about transport network design, urban density, and land use planning. From a modeling perspective, it can aid with the decision to use an unimodal, bimodal or multimodal approximation of the network.

\begin{figure}[!h]
\begin{subfigure}[]{0.5\textwidth}
  \centering
  \includegraphics[width=\textwidth]{heatmap_interactive.jpg}
  \caption{Interactive Heatmap [Sequential]}
  \label{fig:seq}
  \end{subfigure}
\begin{subfigure}[]{0.45\textwidth}
  \centering
  \includegraphics[width=\textwidth]{heatmap.jpg}
  \caption{Static Heatmap [Divergent]}
  \label{fig:div}
\end{subfigure}
\centering
\begin{subfigure}[]{0.5\textwidth}
  \centering
  \includegraphics[width=\textwidth]{hist.jpg}
  \caption{Histogram of stop spacings}
  \label{fig:hist}
\end{subfigure}
\caption{Other visualization features in the package. SFMTA GTFS feed was used to generate these.}
\end{figure}

## Calculating stop spacing summary statistics
In discussions about stop spacings or the process of consolidating stops, it is common to use statistical metrics like means and medians. These metrics are helpful in comparing different transportation agencies or tracking changes within an agency over time. The package provides the summary statistics at network and route levels. For the network as a whole, weighted mean and median values are calculated, incorporating weights based on segments, routes, and traversals (as outlined by [@devunuri2023bus]), in addition to providing measures of standard deviation and various quantiles. At a route level, we provide average values for stop spacings, bus spacings, headways, speeds, number of buses in operation, route lengths and journey times across all routes.

# Acknowledgements

The `gtfs-segments` package draws its inspiration from `gtfs_functions`[@Toso2023], `gtfs2gps`[@pereira2023exploring], and `partridge`[@Whalen2023] repositories. We thank the contributors of these packages for their excellent work. We also extend our thanks to Mobility Data[@MobData2023] for compiling GTFS from around the globe and constantly maintaining them.

# References