## Prerequisites
The major dependencies of this library are the following packages. 
<table>
<tr>
</tr>
<tr>
<td>
<ul>
  <li>numpy</li>
  <li>shapely</li>
  <li>pandas</li>
  <li>scipy</li>
</ul>
</td>
<td>
<ul>
  <li>geopandas</li>
  <li>matplotlib</li>
  <li>contextily</li>
</ul>
</td>
</tr>
</table>

## Installation Options

### Option A

Use pip to install the package. 

```sh
pip install gtfs-segments
```
> ℹ️ Windows users may have to download and install Microsoft Visual C++ distributions. Follow [these](https://stackoverflow.com/questions/29846087/error-microsoft-visual-c-14-0-is-required-unable-to-find-vcvarsall-bat) instructions. 

> 📓 <b> Google Colab :</b> You can install and use the `gtfs-segments` via google colab. Here is a [tutorial](https://colab.research.google.com/drive/1mGmFxw8G194bmg3VQm6vg7dVxCt715eD?usp=sharing
) to help you get started. Make a copy and get started with your work!

### **Option** B

1. Clone the repo
```sh
    git clone https://github.com/UTEL-UIUC/gtfs_segments.git
```
2. Install geopandas using the following code. Read more [here](https://geopandas.org/en/stable/getting_started/install.html)
   
```sh
    conda create -n geo_env -c conda-forge python=3.11 geopandas
```
3. Install the `gtfs_segments` package
```sh
    cd gtfs_segments
    python setup.py install
```
<p align="right">(<a href="#top">back to top</a>)</p>
