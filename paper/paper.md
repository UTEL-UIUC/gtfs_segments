---
title: 'GTFS Segments: A Fast and Efficient Library to Generate Bus Stop Spacings'
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
    \usepackage{graphicx}
---

# Summary

The GTFS Segments (gtfs-segments) library is an open-source Python toolkit for computing, visualizing and analyzing bus stop spacings: the distance a transit bus travels between stops. The library reads General Transit Feed Specification (GTFS) data, snaps bus stops to points along routes, divides routes into segments (the pieces of routes between two stops), and then produces a `GeoDataFrame` containing information about each segment. The library also features several functions that act on this GeoDataFrame. It can produce summary statistics of the spacings for a given network, using various weighting schemes (i.e., weighting by frequency of service), as well as histograms of spacings that display their full distribution. In addition to network-level statistics, the package can also compute statistics for each route, such as its length, headway, speed, and average stop spacing. It can draw maps of networks, routes, or segments over a basemap---which allows the user to manually validate data. The segments DataFrame can be exported to `.csv` and `.geojson` files. The package can fetch the most up-to-date GTFS data from Mobility Data [@MobData2023] repositories for user convenience.

# Statement of need

The choice of bus stop spacing involves a tradeoff between accessibility and speed: wider spacings mean passengers must travel farther to/from stops, but they allow the bus to move faster [@Wu2022]. Many US transit agencies have recently carried out *stop consolidation* campaigns that systematically remove stops, due partly to the perception US stop spacings are much narrower than those abroad. However, there are no reliable data sources to obtain current stop spacings despite the wide adoption of General Transit Feed Specification (GTFS) [@Voulgaris2023Predictors], because GTFS does not include data on stop spacings directly. Spacings must be computed from route shape geometries, stop locations, and stop sequences. A challenge is that stop locations are not placed on top of route shapes and therefore must be somehow projected onto the route's `LINESTRING`. To make spacings available for analysis, `gtfs-segments` use k-dimensional spatial trees and k-nearest neighbor heuristics to snap stops to routes and divide routes into segments for computation of spacings, as described below.

`gtfs-segments` was designed for researchers, transit planners, students and anyone interested in bus networks. The package has been used in several scholarly articles [@devunuri2023bus; @devunuri2023chatgpt; @lehe4135394bus] and to create databases of spacings for over 550 agencies in the US [@DVN/SFBIVU_2022] and 80 agencies in Canada [@DVN/QFTAPM_2023]. Several transit agencies, such as Regional Transportation District Denver (RTD- Denver), have used the package to visualize the effects of their bus stop consolidation efforts. Filtering functions allow the user to explore datasets, identify errors and compute specialized statistics.

# Functionality

The `gtfs-segments` package has four main functionalities: (1) Acquiring GTFS feeds (2) Computing segments (3) Visualizing stop spacings (4) Calculating stop spacing summary statistics. Each of these functionalities is further detailed below.

## Acquiring GTFS feeds

GTFS feeds undergo frequent changes, and obtaining the latest feed is essential to calculate up-to-date stop spacings. The package facilitates accessing over 1100 active GTFS feeds from across the world from Mobility Database Catalogs [@MobData2023]. It includes keyword search functionality to search for GTFS feeds using either the name of the provider (full name or abbreviation) or the place (city or state[^1]). Additionally, to account for typographical errors, the package also implements a fuzzy search feature by matching sub-strings based on the Levenshtein distance [@levenshtein1965binary] algorithm.

[^1]: Search by state is currently applicable only to the US alone.

## Computing segments

A `segment` is defined by three elements: (i) a start stop, (ii) an end stop and (iii) the path that the bus travels along the route in between the two consecutive stops. The segments are computed using route shape geometries and stop locations included in GTFS data. Packages such as `gtfs2gps` [@pereira2023exploring] and `gtfs_functions` [@Toso2023] can compute segments, but this package has the following advantages:

- Faster processing rate[^2] both with and without parallel processing, as evidenced by \autoref{tab:comparison}
- Computationally efficient through lazy loading; using trips only on `busiest_day`; and processing representative trips instead of all trips.
- Filters unusual trips on the `busiest_day` such as trips with considerably fewer traversals or added as an exception to regular service.
- More tolerant to missing files, fields and non-conforming field datatypes and entries.
- Lastly, we incorporate a new way to account for cases when the reported stop locations are misaligned with the route shapes (further detailed below).

[^2]: The average processing rate is the average number of trips processed per second, averaged over 3 independent runs. The experiments were run with an `Intel(R) Core(TM) i9-10920X` processor at 3.50GHz with 12 hyperthreaded CPU cores and 64 GB RAM, running on Windows. The most recent GTFS feeds (as of February 2024) for the respective agencies were used.

\begin{table}[!h]
  \centering
  \resizebox{\textwidth}{!}{%
  \begin{tabular}{llc|cccc|}
    \cline{4-7}
    \multicolumn{3}{l|}{} &
      \multicolumn{4}{c|}{Average Processing Rate (Trips/Second) {[}n=3{]}} \\ \hline
    \multicolumn{3}{|r|}{\textit{Package}} &
      \multicolumn{1}{c|}{\textit{gtfs2gps}} &
      \multicolumn{1}{c|}{\textit{gtfs\_functions}} &
      \multicolumn{2}{c|}{\textit{gtfs\_segments}} \\ \hline
    \multicolumn{3}{|r|}{\textit{Parallel Processing}} &
      \multicolumn{1}{c|}{\textit{Y}} &
      \multicolumn{1}{c|}{\textit{N}} &
      \multicolumn{1}{p{.5in}|}{\textit{\hfil N}} &
      \multicolumn{1}{p{.5in}|}{\textit{\hfil Y}} \\ \hline
    \multicolumn{1}{|l|}{\textbf{Agency}} &
      \multicolumn{1}{l|}{\textbf{City}} &
      \textbf{\begin{tabular}[c]{@{}c@{}}File \\ Size\\  (MB)\end{tabular}} &
      \multicolumn{1}{c|}{v2.1.0} &
      \multicolumn{1}{c|}{v2.3.0} &
      \multicolumn{2}{c|}{v2.1.0} \\ \hline
    \multicolumn{1}{|l|}{SFMTA} &
      \multicolumn{1}{l|}{\begin{tabular}[c]{@{}l@{}}San \\ Francisco\end{tabular}} &
      10.0 &
      \multicolumn{1}{c|}{41} &
      \multicolumn{1}{c|}{621} &
      \multicolumn{1}{c|}{625} &
      \textbf{716} \\ \hline
    \multicolumn{1}{|l|}{MBTA} &
      \multicolumn{1}{l|}{Boston} &
      14.9 &
      \multicolumn{1}{c|}{87} &
      \multicolumn{1}{c|}{325} &
      \multicolumn{1}{c|}{388} &
      \textbf{431} \\ \hline
    \multicolumn{1}{|l|}{TriMet} &
      \multicolumn{1}{l|}{Portland} &
      35.5 &
      \multicolumn{1}{c|}{64} &
      \multicolumn{1}{c|}{85} &
      \multicolumn{1}{c|}{103} &
      \textbf{106} \\ \hline
  \end{tabular}%
  }
  \caption{Comparison of average processing times for gtfs2gps, gtfs\_functions and gtfs\_segments.}\label{tab:comparison}
\end{table}

\autoref{fig:snapping_difficulty} provides example cases where a stop is equidistant from multiple points on a route. Here, projecting the stop onto the route or snapping to the nearest geo-coordinate (lat, lon) may produce errors, such as stops that are out-of-order or stops being snapped far from their locations. Also, the time complexity of projection or snapping is $O(nm)$ using brute force for `n` stops and `m` geo-coordinates that represent the route shape. `gtfs-segments` overcomes these challenges by increasing the route resolution (i.e., adding points in between geo-coordinates), using spatial k-d trees, and using more than one nearest neighbor. The increase in resolution allows stops to be snapped to nearby points. k-d trees [@maneewongvatana1999analysis] reduces the time complexity to $O(nlog(m))$ and makes it possible to compare among several snapping points without added computation. \autoref{fig:interpolate} shows a difficult example route. In the first panel, snapping to the nearest point produces out-of-order stops (3/4/2) and stop 5 is snapped far away from its location. In the second panel, increased resolution fixes 5's location problem but the ordering problem persists. In the third panel, we use the `k=3` nearest neighbors and thus find a proper ordering. Once every stop has been snapped to a geo-coordinate on the route shape, the shape is segmented between stops and each segment is represented by a `LineString` for entry in the GeoDataFrame. We start with `k=3` for the neighbors and double `k` until we find the correct sequence of stops or remove the corresponding trip. On average, fewer than 1% of trips fail, which can be manually corrected and validated by agencies.

\begin{figure}[!h]
\centering
\begin{subfigure}[]{0.75\textwidth}
  \centering
  \includegraphics[width=\textwidth]{snapping_difficulty.jpg}
  \caption{Example route shapes with stop locations that are equidistant from multiple points along the route.}
  \label{fig:snapping_difficulty}
\end{subfigure}
\begin{subfigure}[]{0.75\textwidth}
  \centering
  \includegraphics[width=\textwidth]{interpolation.jpg}
  \caption{Improvement in snapping due to an increase in resolution and using k-nearest neighbors. Adapted from ``Bus Stop Spacings Statistics: Theory and Evidence'' (\protect\hyperlink{ref-devunuri2023bus}{Devunuri, Qiam, Lehe, Pandey,
et al., 2023})}
  \label{fig:interpolate}
\end{subfigure}
\caption{Handling misaligned stops that are far from their route shapes}
\end{figure}

## Visualizing stop spacings

The package allows viewing stop spacings at different hierarchical levels--network, route, and segment--with basemaps and stops overlayed. Moreover, the interactive map feature lets the user control the level of detail and select any segment of interest. Additionally, the user can generate a heatmap by mapping colors to segment values for a selected column. For example \autoref{fig:div}  shows a distance-based heatmap with a divergent colormap, which highlights spacings that are too wide or too narrow. Also, a full distribution of stop spacings can be obtained as a histogram, see \autoref{fig:hist}. Understanding the distribution of stop spacings can inform broader strategic decisions about transport network design and land use planning.

\begin{figure}[!h]
\centering
\begin{subfigure}[]{0.5\textwidth}
  \centering
  \includegraphics[width=\textwidth]{heatmap_interactive.jpg}
  \caption{Interactive Heatmap [Divergent]}
  \label{fig:div}
  \end{subfigure}
\begin{subfigure}[]{0.45\textwidth}
  \centering
  \includegraphics[width=\textwidth]{hist.jpg}
  \caption{Histogram of stop spacings}
  \label{fig:hist}
\end{subfigure}
\caption{Other visualization features in the package. SFMTA GTFS feed was used to generate these.}
\end{figure}

## Calculating stop spacing summary statistics

In discussions about stop spacings, it is common to report statistical metrics like means and medians. These metrics help compare different agencies or track changes within an agency over time. At a network level, weighted mean and median values are provided, incorporating weights based on segments, routes, and traversals (as outlined by @devunuri2023bus), in addition to providing measures of standard deviation and various quantiles. At a route level, we provide average values for stop spacings, bus spacings, headways, speeds, number of buses in operation, route lengths and journey times across all routes.

# Acknowledgments

The `gtfs-segments` package draws its inspiration from `gtfs_functions` [@Toso2023], `gtfs2gps` [@pereira2023exploring], and `partridge` [@Whalen2023] repositories. We thank the contributors of these packages for their excellent work. We also extend our thanks to Mobility Data [@MobData2023] for compiling GTFS from around the globe and constantly maintaining them.

# References
