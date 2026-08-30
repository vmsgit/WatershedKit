import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pyproj import CRS
from pyproj.exceptions import CRSError
import geopandas as gpd
from shapely.geometry import Point


def reproject_raster(src_path, dst_path, dst_crs, resampling_method=Resampling.bilinear):
    
    with rasterio.open(src_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )

        kwargs = src.meta.copy()
        kwargs.update({
            "crs": dst_crs,
            "transform": transform,
            "width": width,
            "height": height,
            "nodata": src.nodata
        })

        with rasterio.open(dst_path, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=resampling_method
                )

    print(f"Reprojected raster written to: {dst_path}")
    return dst_path

"""
    Reproject a raster to a new CRS and save it to disk.

    Parameters
    ----------
    src_path : str
        Path to the source raster (relative to Whitebox working dir, or absolute).
    dst_path : str
        Path where the reprojected raster will be written.
    dst_crs : str
        Target CRS, e.g. "EPSG:32643".
    resampling_method : rasterio.warp.Resampling, optional
        Resampling algorithm. Use Resampling.bilinear or Resampling.cubic
        for continuous data (elevation), Resampling.nearest for categorical
        data (e.g. land cover). Defaults to bilinear.

    Returns
    -------
    str
        The path to the written output raster.
    """


def check_and_choose_crs(dem_path):
    """
    Checks the CRS of the input DEM.
    - If already projected, prints a message and returns None.
    - If geographic, determines the best UTM CRS and returns its EPSG code as "EPSG:xxxxx".
    """
    with rasterio.open(dem_path) as src:
        src_crs = src.crs

        if src_crs.is_projected:
            print(f"DEM is already projected in {src_crs}")
            return None

        # Geographic CRS - find centroid to determine UTM zone
        bounds = src.bounds
        lon = (bounds.left + bounds.right) / 2
        lat = (bounds.top + bounds.bottom) / 2

        zone = int((lon + 180) / 6) + 1
        hemisphere = "N" if lat >= 0 else "S"
        epsg_code = (32600 if lat >= 0 else 32700) + zone

        target_crs = f"EPSG:{epsg_code}"
        print(f"Chosen CRS for reprojection is {target_crs} UTM/{zone}{hemisphere}")

        return target_crs



def create_pour_point_shp(lat, lon, project_crs, output_path):
    """
    Create a pour point shapefile from lat/lon coordinates.

    Parameters:
        lat (float): Latitude in decimal degrees (WGS84)
        lon (float): Longitude in decimal degrees (WGS84)
        project_crs (str): Target CRS in "EPSG:xxxxx" format 
                            (should match your streams raster's CRS)
        output_path (str): Path to save the output shapefile, e.g. "pour_points.shp"

    Returns:
        GeoDataFrame of the saved pour point (already in project_crs)
    """
    gdf = gpd.GeoDataFrame(
        [{"id": 1}],
        geometry=[Point(lon, lat)],   # note: (lon, lat) order for Point()
        crs="EPSG:4326"               # input assumed to be WGS84 lat/lon
    ).to_crs(project_crs)

    gdf.to_file(output_path)
    print(f"Saved pour point to {output_path} in {project_crs}")
    return gdf

#To set crs to vector file. As  the whiteboxtools raster to vector conversion misses 
# to proguce .prj file which cause errors in clipping operations.
def fix_missing_prj(shp_path, target_crs, output_path=None):
    gdf = gpd.read_file(shp_path)
    if gdf.crs is None:
        gdf = gdf.set_crs(target_crs, allow_override=True)
        gdf.to_file(output_path or shp_path)   # <-- HERE
    ...