import whitebox
wbt = whitebox.WhiteboxTools()
import geopandas as gpd
import networkx as nx
import numpy as np
from shapely.geometry import Point, LineString
from shapely.ops import linemerge
import rasterio


#help(wbt.clip_raster_to_polygon)

#ALL Functions
def clip_streams_to_watershed(streams_file, watershed_file, output_file):
    import geopandas as gpd

    streams = gpd.read_file(streams_file)
    watershed = gpd.read_file(watershed_file)

    clipped = gpd.clip(streams, watershed)

    clipped.to_file(output_file)
    print(f"Saved {len(clipped)} stream features to {output_file}")


# ==========================================
# 1. Shared Helper Function
# ==========================================
def _get_nearest_node(graph, point_geom):
    """Helper function to find the nearest graph node to a given Shapely Point."""
    nodes = list(graph.nodes)
    nodes_arr = np.array(nodes)
    pt_arr = np.array([point_geom.x, point_geom.y])
    dists = np.linalg.norm(nodes_arr - pt_arr, axis=1)
    return nodes[np.argmin(dists)]
def _get_nearest_node(graph, point_geom):
    """Helper function to find the nearest graph node to a given Shapely Point."""
    nodes = list(graph.nodes)
    nodes_arr = np.array(nodes)
    pt_arr = np.array([point_geom.x, point_geom.y])
    
    # Vectorized Euclidean distance for speed
    dists = np.linalg.norm(nodes_arr - pt_arr, axis=1)
    nearest_idx = np.argmin(dists)
    return nodes[nearest_idx]

# ==========================================
# 2. Length to Centroid (L_ca)
# ==========================================
def calculate_length_to_centroid(streams_shp, outlet_shp, centroid_shp, output_shp):
    """
    Calculates the hydrologic length to centroid (L_ca) along a stream network 
    and exports the routed path as a shapefile.
    
    Parameters:
    -----------
    streams_shp : str
        File path to the stream network shapefile.
    outlet_shp : str
        File path to the watershed outlet point shapefile.
    centroid_shp : str
        File path to the watershed centroid point shapefile.
    output_shp : str
        File path where the resulting path shapefile will be saved.
        
    Returns:
    --------
    float or None
        The calculated length in the units of the input CRS, or None if no path is found.
    """
    print("Loading shapefiles...")
    streams_gdf = gpd.read_file(streams_shp)
    outlet_gdf = gpd.read_file(outlet_shp)
    centroid_gdf = gpd.read_file(centroid_shp)

    # Extract the Point geometries
    outlet_pt = outlet_gdf.geometry.iloc[0]
    centroid_pt = centroid_gdf.geometry.iloc[0]

    # Ensure streams are single-part LineStrings
    streams_gdf = streams_gdf.explode(index_parts=False).reset_index(drop=True)

    print("Building routing graph...")
    G = nx.Graph()

    for _, row in streams_gdf.iterrows():
        geom = row.geometry
        if geom.geom_type == 'LineString':
            coords = list(geom.coords)
            # Create an edge for every line segment between vertices
            for i in range(len(coords) - 1):
                pt1 = coords[i]
                pt2 = coords[i + 1]
                
                # Calculate Euclidean distance for the edge weight
                length = Point(pt1).distance(Point(pt2))
                G.add_edge(pt1, pt2, weight=length, geom=LineString([pt1, pt2]))

    print("Snapping points to network...")
    outlet_node = _get_nearest_node(G, outlet_pt)
    centroid_node = _get_nearest_node(G, centroid_pt)

    print("Calculating shortest path...")
    try:
        # Calculate path and length
        path_nodes = nx.shortest_path(G, source=outlet_node, target=centroid_node, weight='weight')
        path_length = nx.shortest_path_length(G, source=outlet_node, target=centroid_node, weight='weight')
        
        # Reconstruct the path geometry
        path_lines = []
        for i in range(len(path_nodes) - 1):
            u = path_nodes[i]
            v = path_nodes[i + 1]
            path_lines.append(G[u][v]['geom'])

        merged_path = linemerge(path_lines)

        # Export to Shapefile
        output_gdf = gpd.GeoDataFrame(
            {'L_ca': [path_length]},
            geometry=[merged_path],
            crs=streams_gdf.crs 
        )
        
        output_gdf.to_file(output_shp)
        
        print(f"Success! Length to centroid (L_ca): {path_length:.2f} units.")
        print(f"Path saved to: {output_shp}\n")
        
        return path_length

    except nx.NetworkXNoPath:
        print("\n[ERROR] No path found between the outlet and the centroid.")
        print("Ensure your stream network is topologically connected (no micro-gaps between lines).")
        return None

# ==========================================
# 3. Main Channel Length (L)
# ==========================================
def calculate_main_channel_length(streams_shp, outlet_shp, output_shp):
    """
    Calculates the Main Channel Length (L) by finding the longest flow path
    from the outlet to the furthest point in the stream network.
    Also stores the outlet and most-upstream point coordinates
    (in the SAME projected CRS as the input) as attributes in the output shapefile.
    """
    print("Loading shapefiles...")
    streams_gdf = gpd.read_file(streams_shp)
    outlet_gdf = gpd.read_file(outlet_shp)
    outlet_pt = outlet_gdf.geometry.iloc[0]

    # Ensure streams are single-part LineStrings
    streams_gdf = streams_gdf.explode(index_parts=False).reset_index(drop=True)

    print("Building routing graph...")
    G = nx.Graph()

    for _, row in streams_gdf.iterrows():
        geom = row.geometry
        if geom.geom_type == 'LineString':
            coords = list(geom.coords)
            for i in range(len(coords) - 1):
                pt1 = coords[i]
                pt2 = coords[i + 1]
                length = Point(pt1).distance(Point(pt2))
                G.add_edge(pt1, pt2, weight=length, geom=LineString([pt1, pt2]))

    print("Snapping outlet to network...")
    outlet_node = _get_nearest_node(G, outlet_pt)

    print("Finding the longest path...")
    path_lengths = nx.single_source_dijkstra_path_length(G, outlet_node, weight='weight')
    furthest_node = max(path_lengths, key=path_lengths.get)
    max_length = path_lengths[furthest_node]

    longest_path_nodes = nx.shortest_path(G, source=outlet_node, target=furthest_node, weight='weight')

    print("Reconstructing geometry...")
    path_lines = []
    for i in range(len(longest_path_nodes) - 1):
        u = longest_path_nodes[i]
        v = longest_path_nodes[i + 1]
        path_lines.append(G[u][v]['geom'])

    merged_path = linemerge(path_lines)

    # Native projected coordinates (same CRS/units as the input streams)
    out_x, out_y = outlet_pt.x, outlet_pt.y          # outlet point
    up_x, up_y = furthest_node[0], furthest_node[1]  # most-upstream point (raw coord tuple)

    # Export to Shapefile
    output_gdf = gpd.GeoDataFrame(
        {
            'Length_L': [max_length],
            'Out_X':    [out_x],
            'Out_Y':    [out_y],
            'Up_X':     [up_x],
            'Up_Y':     [up_y],
        },
        geometry=[merged_path],
        crs=streams_gdf.crs
    )

    output_gdf.to_file(output_shp)

    print(f"Success! Main Channel Length (L): {max_length:.2f} units.")
    print(f"Path saved to: {output_shp}\n")

    return max_length


# ==========================================
# Calculating Basin Length Lb
# ==========================================
def calculate_basin_length(watershed_shp, outlet_shp, output_shp):
    """
    Calculates the Basin Length (Lb) as a straight line from the outlet 
    to the furthest point on the watershed boundary.
    """
    print("Loading shapefiles...")
    watershed_gdf = gpd.read_file(watershed_shp)
    outlet_gdf = gpd.read_file(outlet_shp)
    
    outlet_pt = outlet_gdf.geometry.iloc[0]

    print("Extracting watershed boundary vertices...")
    coords = []
    # Loop through geometries to handle both Polygons and MultiPolygons
    for geom in watershed_gdf.geometry:
        if geom.geom_type == 'Polygon':
            coords.extend(list(geom.exterior.coords))
        elif geom.geom_type == 'MultiPolygon':
            for part in geom.geoms:
                coords.extend(list(part.exterior.coords))
                
    # Convert coordinates to a numpy array for fast, vectorized math
    coords_arr = np.array(coords)
    outlet_coords = np.array([outlet_pt.x, outlet_pt.y])

    print("Calculating furthest boundary point...")
    # Calculate Euclidean distance from the outlet to ALL boundary vertices at once
    dists = np.linalg.norm(coords_arr - outlet_coords, axis=1)
    
    # Find the maximum distance and the exact coordinates of that point
    furthest_idx = np.argmax(dists)
    max_dist = dists[furthest_idx]
    furthest_pt = coords_arr[furthest_idx]

    print("Creating Basin Length geometry...")
    # Create a straight line between the outlet and the furthest point
    lb_line = LineString([outlet_pt, Point(furthest_pt)])

    # Export to Shapefile
    output_gdf = gpd.GeoDataFrame(
        {'Basin_Lb': [max_dist]},
        geometry=[lb_line],
        crs=watershed_gdf.crs 
    )
    
    output_gdf.to_file(output_shp)
    
    print(f"Success! Basin Length (Lb): {max_dist:.2f} units.")
    print(f"Straight-line path saved to: {output_shp}\n")
    
    return max_dist



# ==========================================
# Calculating True Basin slope of catchment - Need DEM file clipped to basin boundary
# ==========================================
def calculate_average_basin_slope(dem_path):
    """
    Calculates the average basin slope (%) from a DEM using Horn's Method.
    
    Args:
        dem_path (str): The file path to the clipped DEM (.tif).
        
    Returns:
        float: The average slope of the basin in percent.
    """
    # 1. Load the DEM
    with rasterio.open(dem_path) as src:
        Z = src.read(1)
        nodata = src.nodata
        cell_size_x = src.res[0]
        cell_size_y = src.res[1]

    # Convert to float and mask NoData values with NaN
    Z = Z.astype(float)
    if nodata is not None:
        Z[Z == nodata] = np.nan

    # 2. Set up the 3x3 moving window slices
    a = Z[:-2, :-2]
    b = Z[:-2, 1:-1]
    c = Z[:-2, 2:]
    d = Z[1:-1, :-2]
    f = Z[1:-1, 2:]
    g = Z[2:, :-2]
    h = Z[2:, 1:-1]
    i = Z[2:, 2:]

    # 3. Apply Horn's Method formula
    dzdx = ((c + 2*f + i) - (a + 2*d + g)) / (8 * cell_size_x)
    dzdy = ((g + 2*h + i) - (a + 2*b + c)) / (8 * cell_size_y)

    slope = np.sqrt(dzdx**2 + dzdy**2)
    slope_percent = slope * 100

    # 4. Calculate the true average, ignoring the NaN (NoData) values
    average_slope = np.nanmean(slope_percent)
    
    return float(average_slope)



#-------------------------------------------------------------------
# Calculate slope of longest flow path - function STARTS here
#-------------------------------------------------------------------
# Tunable constants (override via function kwargs if needed)
SHORT_CHANNEL_MIN_POINTS = 10       # below this many sample points -> simple slope only
LARGE_CATCHMENT_THRESHOLD_KM2 = 100.0
MIN_RELIEF_M = 2.0                  # below this total relief -> flat-catchment floor
SLOPE_FLOOR_FRACTION = 1e-4
LENGTH_MISMATCH_TOLERANCE = 0.05    # 5% allowed diff between attribute vs geometry length
DEFAULT_N_CANDIDATES = range(4, 31)
CONVERGENCE_TOL = 0.03
CONVERGENCE_RUN = 3

# Internal helpers
def _require_projected(gdf, label):
    if gdf.crs is None:
        raise ValueError(f"{label} has no CRS defined.")
    if gdf.crs.is_geographic:
        raise ValueError(
            f"{label} is in a geographic CRS (degrees). "
            "Reproject to a projected CRS in metres before running this module."
        )
 
 
def _load_catchment_area_km2(catchment_shp_path):
    gdf = gpd.read_file(catchment_shp_path)
    _require_projected(gdf, "Catchment boundary shapefile")
    if gdf.empty:
        raise ValueError("Catchment boundary shapefile has no features.")
    area_km2 = float(gdf.geometry.area.sum()) / 1e6
    if area_km2 <= 0:
        raise ValueError(f"Computed catchment area is not positive ({area_km2} km^2).")
    return area_km2
 
 
def _load_channel_with_attr(stream_shp_path):
    gdf = gpd.read_file(stream_shp_path)
    _require_projected(gdf, "Stream shapefile")
    if gdf.empty:
        raise ValueError("Stream shapefile has no features.")
 
    attr_cols = [c for c in gdf.columns if c != gdf.geometry.name]
    attr_length_m = None
    if attr_cols:
        try:
            attr_length_m = float(gdf[attr_cols[0]].sum())
        except (TypeError, ValueError):
            attr_length_m = None
 
    geom = linemerge(gdf.geometry.unary_union) if len(gdf) > 1 else gdf.geometry.iloc[0]
    if geom.geom_type != "LineString":
        raise ValueError(
            f"Merged channel geometry is {geom.geom_type}, not a single LineString. "
            "Check the stream shapefile represents one continuous flow path."
        )
    return geom, attr_length_m
 
 
def _sample_profile(line, dem_path, interval_m, edge_snap_max_cells=5):
    """
    Samples elevation along `line` at `interval_m` spacing.
 
    Handles a common, expected edge case: the line's endpoints (especially
    the outlet) sit exactly on the catchment boundary, which can fall just
    outside the valid (non-NoData) mask of a DEM clipped to that same
    boundary due to vector/raster edge mismatch. When this happens ONLY at
    the start/end of the profile, the affected point is nudged inward
    along the line in DEM-cell-sized steps (up to `edge_snap_max_cells`)
    until a valid value is found.
 
    A genuine gap anywhere in the INTERIOR of the profile is still a hard
    failure - that indicates a real problem with the DEM/clip, not an
    expected boundary artifact.
    """
    warnings = []
    with rasterio.open(dem_path) as dem:
        nodata = dem.nodata
        cell_size = abs(dem.transform.a)
        length = line.length
        n_pts = max(int(length // interval_m) + 1, 2)
        distances = np.linspace(0, length, n_pts)
 
        def sample_at(d):
            pt = line.interpolate(d)
            val = list(dem.sample([(pt.x, pt.y)]))[0][0]
            if nodata is not None and val == nodata:
                return np.nan
            return float(val)
 
        elevations = np.array([sample_at(d) for d in distances], dtype=float)
 
        bad_idx = np.where(~np.isfinite(elevations))[0]
        interior_bad = [i for i in bad_idx if 0 < i < n_pts - 1]
        if interior_bad:
            raise ValueError(
                f"DEM sampling returned NoData at {len(interior_bad)} interior point(s) "
                "along the channel (not at the endpoints). This indicates a real gap in "
                "DEM coverage, not a boundary-edge artifact - check the clipped DEM."
            )
 
        # Repair endpoint NoData by nudging inward along the line
        for i in bad_idx:
            direction = 1 if i == 0 else -1
            fixed = False
            for step in range(1, edge_snap_max_cells + 1):
                d_new = distances[i] + direction * step * cell_size
                d_new = min(max(d_new, 0), length)
                val = sample_at(d_new)
                if np.isfinite(val):
                    elevations[i] = val
                    warnings.append(
                        f"Endpoint at chainage {distances[i]:.1f} m was NoData "
                        f"(boundary/clip edge mismatch) - used value {step} cell(s) "
                        "inward instead."
                    )
                    fixed = True
                    break
            if not fixed:
                raise ValueError(
                    f"Endpoint at chainage {distances[i]:.1f} m is NoData and could not "
                    f"be resolved within {edge_snap_max_cells} cells inward. Check DEM "
                    "clip extent/mask near this location."
                )
 
    return distances, elevations, warnings
 
 
def _simple_slope(distances, elevations):
    L_m = distances[-1] - distances[0]
    H_m = elevations[0] - elevations[-1]
    if L_m <= 0:
        raise ValueError("Channel length is not positive - cannot compute slope.")
    return {
        "H_m": H_m,
        "L_m": L_m,
        "slope_m_per_km": H_m / (L_m / 1000),
        "slope_fraction": H_m / L_m,
    }
 
 
def _smooth_profile(elevations, window=5):
    window = min(window, max(len(elevations) // 3, 1))
    if window < 3:
        return elevations.copy()
    if window % 2 == 0:
        window += 1
    kernel = np.ones(window) / window
    pad = window // 2
    padded = np.pad(elevations, pad, mode="edge")
    return np.convolve(padded, kernel, mode="valid")
 
 
def _noise_sigma(elevations, smoothed):
    return float(np.std(elevations - smoothed))
 
 
def _equal_elevation_segments_slope(distances, elev_monotonic, n_segments):
    elev_start, elev_end = elev_monotonic[0], elev_monotonic[-1]
    total_fall = elev_start - elev_end
    fall_breaks = np.linspace(elev_start, elev_end, n_segments + 1)
    dist_at_break = np.interp(fall_breaks[::-1], elev_monotonic[::-1], distances[::-1])[::-1]
 
    seg_L = np.diff(dist_at_break)
    if np.any(seg_L <= 0):
        return None
    seg_H = total_fall / n_segments
    seg_S = seg_H / seg_L
    denom = np.sum(seg_L / np.sqrt(seg_S))
    if denom <= 0 or not np.isfinite(denom):
        return None
    return float((np.sum(seg_L) / denom) ** 2)
 
 
def _equal_length_segments_slope(distances, elev_monotonic, n_segments):
    seg_edges = np.linspace(distances[0], distances[-1], n_segments + 1)
    elev_at_edges = np.interp(seg_edges, distances, elev_monotonic)
    seg_L = np.diff(seg_edges)
    seg_H = -np.diff(elev_at_edges)  # positive: elevation decreases downstream
    if np.any(seg_L <= 0) or np.any(seg_H <= 0):
        return None  # a flat/rising sub-segment at this N - skip this candidate
    seg_S = seg_H / seg_L
    denom = np.sum(seg_L / np.sqrt(seg_S))
    if denom <= 0 or not np.isfinite(denom):
        return None
    return float((np.sum(seg_L) / denom) ** 2)
 
 
def _auto_select_equivalent_slope(segment_func, distances, elev_monotonic,
                                   candidates=DEFAULT_N_CANDIDATES,
                                   tol=CONVERGENCE_TOL, run=CONVERGENCE_RUN):
    n_pts = len(distances)
    valid_ns = [n for n in candidates if n <= n_pts // 3]
 
    results = []
    for n in valid_ns:
        Sc = segment_func(distances, elev_monotonic, n)
        if Sc is not None and np.isfinite(Sc) and Sc > 0:
            results.append((n, Sc))
 
    if len(results) < 2:
        raise ValueError(
            f"'{segment_func.__name__}' could not produce enough valid segment "
            "candidates to determine equivalent slope - profile may be too short, "
            "too noisy, or too irregular for this method."
        )
 
    chosen_n, chosen_Sc = results[-1]
    converged = False
    stable_run = 0
    for i in range(1, len(results)):
        n_prev, Sc_prev = results[i - 1]
        n_curr, Sc_curr = results[i]
        rel_change = abs(Sc_curr - Sc_prev) / Sc_prev
        if rel_change <= tol:
            stable_run += 1
            if stable_run >= run:
                chosen_n, chosen_Sc = results[i - run + 1]
                converged = True
                break
        else:
            stable_run = 0
 
    return {
        "Sc_fraction": chosen_Sc,
        "Sc_m_per_km": chosen_Sc * 1000,
        "n_segments": chosen_n,
        "converged": converged,
        "candidates_tested": results,
    }

# ---------------------------------------------------------------------
# Public function
def compute_channel_slope_parameters(
    stream_shp_path: str,
    catchment_shp_path: str,
    dem_clipped_path: str,
    sample_interval_m: float = None,
    short_channel_min_points: int = SHORT_CHANNEL_MIN_POINTS,
    large_catchment_threshold_km2: float = LARGE_CATCHMENT_THRESHOLD_KM2,
    min_relief_m: float = MIN_RELIEF_M,
) -> dict:
    """
    Compute simple and equivalent (Taylor-Schwarz) slope of the longest
    flow path, with method selection based on catchment area and channel
    length as specified.
 
    Returns a dict:
        {
            "catchment_area_km2": float,
            "channel_length_km": float,        # from shapefile attribute (authoritative)
            "channel_length_geom_km": float,    # from geometry, cross-check
            "dem_cell_size_m": float,
            "sample_points": int,
            "dem_noise_sigma_m": float,
            "total_relief_m": float,
            "simple_slope": {...},
            "equal_elevation_drop": {...} or None,
            "equal_length": {...} or None,
            "method_used": str,
            "warnings": [str, ...],
        }
 
    Raises:
        Any exception encountered is printed with context and re-raised,
        halting the caller's script. Catch this exception in main.py only
        if you deliberately want to handle/log it there instead of letting
        the program stop.
    """
    try:
        catchment_area_km2 = _load_catchment_area_km2(catchment_shp_path)
 
        line, attr_length_m = _load_channel_with_attr(stream_shp_path)
        geom_length_m = line.length
 
        if attr_length_m is not None and geom_length_m > 0:
            rel_diff = abs(attr_length_m - geom_length_m) / geom_length_m
            if rel_diff > LENGTH_MISMATCH_TOLERANCE:
                raise ValueError(
                    f"Channel length mismatch: shapefile attribute = {attr_length_m:.1f} m, "
                    f"geometry length = {geom_length_m:.1f} m ({rel_diff*100:.1f}% difference). "
                    "This suggests the attribute is stale or the geometry was edited after "
                    "the attribute was written - check the input data before proceeding."
                )
            L_m = attr_length_m
        else:
            L_m = geom_length_m
 
        with rasterio.open(dem_clipped_path) as dem:
            cell_size = abs(dem.transform.a)
        interval = sample_interval_m or cell_size
 
        distances, elevations, sample_warnings = _sample_profile(line, dem_clipped_path, interval)
        n_pts = len(distances)
 
        simple = _simple_slope(distances, elevations)
 
        smoothed = _smooth_profile(elevations)
        sigma = _noise_sigma(elevations, smoothed)
        elev_monotonic = np.minimum.accumulate(smoothed)
        H = float(elev_monotonic[0] - elev_monotonic[-1])
 
        result = {
            "catchment_area_km2": catchment_area_km2,
            "channel_length_km": L_m / 1000,
            "channel_length_geom_km": geom_length_m / 1000,
            "dem_cell_size_m": cell_size,
            "sample_points": n_pts,
            "dem_noise_sigma_m": sigma,
            "total_relief_m": H,
            "simple_slope": simple,
            "equal_elevation_drop": None,
            "equal_length": None,
            "method_used": None,
            "warnings": list(sample_warnings),
        }
 
        # --- Degenerate case: effectively flat catchment ---
        if H < max(min_relief_m, 3 * sigma):
            result["method_used"] = "flat_catchment_slope_floor"
            result["warnings"].append(
                f"Total relief ({H:.2f} m) is small relative to DEM noise "
                f"(sigma={sigma:.2f} m). Using slope floor ({SLOPE_FLOOR_FRACTION}) "
                "for both equivalent-slope fields."
            )
            floor = {"Sc_fraction": SLOPE_FLOOR_FRACTION,
                     "Sc_m_per_km": SLOPE_FLOOR_FRACTION * 1000,
                     "n_segments": None, "converged": None}
            result["equal_elevation_drop"] = floor
            result["equal_length"] = floor
            return result
 
        # --- Degenerate case: channel too short for segmentation ---
        if n_pts < short_channel_min_points:
            result["method_used"] = "simple_end_to_end_only"
            result["warnings"].append(
                f"Only {n_pts} sample points along the channel (< {short_channel_min_points}) "
                "- too short for reliable segmentation. Using simple end-to-end slope only."
            )
            return result
 
        # --- Method selection by catchment area ---
        if catchment_area_km2 > large_catchment_threshold_km2:
            result["method_used"] = "equal_length_only"
            result["equal_length"] = _auto_select_equivalent_slope(
                _equal_length_segments_slope, distances, elev_monotonic
            )
        else:
            result["method_used"] = "both_equal_elevation_and_equal_length"
            result["equal_elevation_drop"] = _auto_select_equivalent_slope(
                _equal_elevation_segments_slope, distances, elev_monotonic
            )
            result["equal_length"] = _auto_select_equivalent_slope(
                _equal_length_segments_slope, distances, elev_monotonic
            )
 
        return result
 
    except Exception as e:
        print(f"ERROR in compute_channel_slope_parameters: {e}")
        raise

#-------------------------------------------------------------------
# Calculate slope of longest flow path - function ENDS here
#-------------------------------------------------------------------



#-------------------------------------------------------------------
# Hypsometric Curve function - 
#-------------------------------------------------------------------
"""Calculates the hypsometric curve and hypsometric integral (HI) for a
catchment, indicating its relative erosional life-stage (youthful,
mature, or old-age/peneplain)."""
def calculate_hypsometric_parameters(dem_path: str, n_bins: int = 100,
                                      min_relief_m: float = 2.0,
                                      cross_check_tol: float = 0.05) -> dict:
    """
    Returns a dict:
        {
            "elev_min_m", "elev_max_m", "elev_mean_m", "total_relief_m",
            "HI_relief_ratio": float or None,
            "HI_curve_integral": float or None,
            "HI_difference": float or None,
            "stage_classification": str,
            "curve_relative_area": list[float],   # for plotting
            "curve_relative_height": list[float],  # for plotting
            "n_bins": int,
            "warnings": [str, ...],
        }
 
    Raises ValueError (printed, then re-raised) on genuine data problems:
    missing/empty DEM, or no valid (non-NoData) elevation cells found.
    """
    try:
        with rasterio.open(dem_path) as dem:
            Z = dem.read(1).astype(float)
            nodata = dem.nodata
        if nodata is not None:
            Z[Z == nodata] = np.nan
 
        valid = Z[np.isfinite(Z)]
        if valid.size == 0:
            raise ValueError(
                "No valid elevation cells found in the DEM - check that the "
                "raster is actually clipped/masked to the catchment and has "
                "a correctly set NoData value."
            )
 
        elev_min = float(np.min(valid))
        elev_max = float(np.max(valid))
        elev_mean = float(np.mean(valid))
        total_relief = elev_max - elev_min
 
        result = {
            "elev_min_m": elev_min,
            "elev_max_m": elev_max,
            "elev_mean_m": elev_mean,
            "total_relief_m": total_relief,
            "HI_relief_ratio": None,
            "HI_curve_integral": None,
            "HI_difference": None,
            "stage_classification": None,
            "curve_relative_area": [],
            "curve_relative_height": [],
            "n_bins": n_bins,
            "warnings": [],
        }
 
        # --- Degenerate case: effectively flat catchment ---
        if total_relief < min_relief_m:
            result["warnings"].append(
                f"Total relief ({total_relief:.2f} m) is below the minimum "
                f"meaningful threshold ({min_relief_m} m) - hypsometric "
                "integral is not meaningful for a near-flat catchment. "
                "HI fields left as None."
            )
            result["stage_classification"] = "not applicable (flat catchment)"
            return result
 
        # --- Method 1: elevation-relief ratio (Pike & Wilson, 1971) ---
        HI_relief_ratio = (elev_mean - elev_min) / total_relief
        result["HI_relief_ratio"] = HI_relief_ratio
 
        # --- Method 2: numerical integration of area-elevation curve ---
        h_rel = np.linspace(0, 1, n_bins + 1)
        elev_thresholds = elev_min + h_rel * total_relief
        a_rel = np.array([
            np.sum(valid >= thresh) / valid.size for thresh in elev_thresholds
        ])
        # a_rel decreases as h_rel increases; sort ascending by a_rel for trapz
        order = np.argsort(a_rel)
        HI_curve_integral = float(np.trapezoid(h_rel[order], a_rel[order]))
        result["HI_curve_integral"] = HI_curve_integral
        result["curve_relative_area"] = a_rel.tolist()
        result["curve_relative_height"] = h_rel.tolist()
 
        # --- Cross-check ---
        diff = abs(HI_relief_ratio - HI_curve_integral)
        result["HI_difference"] = diff
        if diff > cross_check_tol:
            result["warnings"].append(
                f"HI methods disagree by {diff:.3f} (> tolerance {cross_check_tol}). "
                f"Consider increasing n_bins (currently {n_bins}) for a smoother "
                "area-elevation curve, especially if the DEM has a large elevation range."
            )
 
        # --- Classification (use the relief-ratio value as primary) ---
        HI = HI_relief_ratio
        if HI > 0.6:
            stage = "youth (convex)"
        elif HI >= 0.35:
            stage = "mature (S-shaped)"
        else:
            stage = "old age (concave)"
        result["stage_classification"] = stage
 
        return result
 
    except Exception as e:
        print(f"ERROR in calculate_hypsometric_parameters: {e}")
        raise
 
 
import csv
 
 
def save_hypsometric_curve_csv(result: dict, output_csv_path: str) -> None:
    """
    Writes the hypsometric curve (relative_area, relative_height) to a CSV
    file, along with the summary statistics as header comment lines, so the
    file is self-describing when opened later or handed to someone else.
 
    Raises ValueError (printed, then re-raised) if the result dict has no
    curve data to write (e.g. it came from a flat-catchment case where HI
    was not computed).
    """
    try:
        area = result.get("curve_relative_area", [])
        height = result.get("curve_relative_height", [])
 
        if not area or not height:
            raise ValueError(
                "No curve data available to write - this result dict likely "
                "came from a flat/degenerate catchment where the hypsometric "
                "curve was not computed."
            )
 
        with open(output_csv_path, "w", newline="") as f:
            f.write(f"# elev_min_m,{result['elev_min_m']}\n")
            f.write(f"# elev_max_m,{result['elev_max_m']}\n")
            f.write(f"# elev_mean_m,{result['elev_mean_m']}\n")
            f.write(f"# HI_relief_ratio,{result['HI_relief_ratio']}\n")
            f.write(f"# HI_curve_integral,{result['HI_curve_integral']}\n")
            f.write(f"# stage_classification,{result['stage_classification']}\n")
 
            writer = csv.writer(f)
            writer.writerow(["relative_area", "relative_height"])
            writer.writerows(zip(area, height))
 
        print(f"Hypsometric curve saved to {output_csv_path}")
 
    except Exception as e:
        print(f"ERROR in save_hypsometric_curve_csv: {e}")
        raise
 

## DEM Fill Depressions
"""
breach_depressions_least_cost(
    dem,
    output,
    dist,
    max_cost=None,
    min_dist=True,
    flat_increment=None,
    fill=True,
    callback=None
) method of whitebox.whitebox_tools.WhiteboxTools instance
    Breaches the depressions in a DEM using a least-cost pathway method.                            
                                                                                                    
    Keyword arguments:                                                                              
                                                                                                    
    dem -- Input raster DEM file.                                                                   
    output -- Output raster file.                                                                   
    dist -- Maximum search distance for breach paths in cells. Chatgpt suggest - 50-150 value for 30m dem                                
    max_cost -- Optional maximum breach cost (default is Inf).                                      
    min_dist -- Optional flag indicating whether to minimize breach distances.                      
    flat_increment -- Optional elevation increment applied to flat areas.                           
    fill -- Optional flag indicating whether to fill any remaining unbreached depressions.          
    callback -- Custom function for handling tool text outputs.
"""

"""
dem_void_filling
fill_burn
fill_depressions
fill_depressions_planchon_and_darboux
fill_depressions_wang_and_liu - fast and reliable 
fill_missing_data
fill_single_cell_pits

breach_depressions
breach_depressions_least_cost - USe this one to preserve topography better
breach_single_cell_pits
"""


##DEM - FLow Direction 

"""for name in dir(wbt):
    if "d8" in name.lower():
        print(name)
"""

"""
d8_pointer(dem, output, esri_pntr=False, callback=None) method of whitebox.whitebox_tools.WhiteboxTools instance
    Calculates a D8 flow pointer raster from an input DEM.

    Keyword arguments:

    dem -- Input raster DEM file.
    output -- Output raster file.
    esri_pntr -- D8 pointer uses the ESRI style scheme.
    callback -- Custom function for handling tool text outputs.
"""

##DEM - Flow Accumulation
"""
d8_flow_accumulation(
    i,
    output,
    out_type='cells',
    log=False,
    clip=False,
    pntr=False,
    esri_pntr=False,
    callback=None
) method of whitebox.whitebox_tools.WhiteboxTools instance
    Calculates a D8 flow accumulation raster from an input DEM or flow pointer.                                                               
                                                                                                                                              
    Keyword arguments:                                                                                                                        
                                                                                                                                              
    i -- Input raster DEM or D8 pointer file.                                                                                                 
    output -- Output raster file.                                                                                                             
    out_type -- Output type; one of 'cells' (default), 'catchment area', and 'specific contributing area'.                                    
    log -- Optional flag to request the output be log-transformed.                                                                            
    clip -- Optional flag to request clipping the display max by 1%.                                                                          
    pntr -- Is the input raster a D8 flow pointer rather than a DEM?.                                                                         
    esri_pntr -- Input D8 pointer uses the ESRI style scheme.                                                                                 
    callback -- Custom function for handling tool text outputs.

extract_streams(
    flow_accum,
    output,
    threshold,
    zero_background=False,
    callback=None
) method of whitebox.whitebox_tools.WhiteboxTools instance
    Extracts stream grid cells from a flow accumulation raster.

    Keyword arguments:

    flow_accum -- Input raster D8 flow accumulation file.                                           
    output -- Output raster file.                                                                   
    threshold -- Threshold in flow accumulation values for channelization.                          
    zero_background -- Flag indicating whether a background value of zero should be used.           
    callback -- Custom function for handling tool text outputs. 

strahler_stream_order(
    d8_pntr,
    streams,
    output,
    esri_pntr=False,
    zero_background=False,
    callback=None
) method of whitebox.whitebox_tools.WhiteboxTools instance
    Assigns the Strahler stream order to each link in a stream network.

    Keyword arguments:
                                                                                                    
    d8_pntr -- Input raster D8 pointer file.                                                        
    streams -- Input raster streams file.                                                           
    output -- Output raster file.                                                                   
    esri_pntr -- D8 pointer uses the ESRI style scheme.                                             
    zero_background -- Flag indicating whether a background value of zero should be used.           
    callback -- Custom function for handling tool text outputs.

raster_streams_to_vector(
    streams,
    d8_pntr,
    output,
    esri_pntr=False,
    callback=None
) method of whitebox.whitebox_tools.WhiteboxTools instance
    Converts a raster stream file into a vector file.

    Keyword arguments:

    streams -- Input raster streams file.                                                           
    d8_pntr -- Input raster D8 pointer file.                                                        
    output -- Output vector file.                                                                   
    esri_pntr -- D8 pointer uses the ESRI style scheme.                                             
    callback -- Custom function for handling tool text outputs.  

jenson_snap_pour_points(pour_pts, streams, output, snap_dist, callback=None) 
    Keyword arguments:

    pour_pts -- Input vector pour points (outlet) file.
    streams -- Input raster streams file.
    output -- Output vector file.
    snap_dist -- Maximum snap distance in map units.
    callback -- Custom function for handling tool text outputs. 
    

    watershed(d8_pntr, pour_pts, output, esri_pntr=False, callback=None) 
    Keyword arguments:

    d8_pntr -- Input D8 pointer raster file.
    pour_pts -- Input pour points (outlet) file.
    output -- Output raster file.
    esri_pntr -- D8 pointer uses the ESRI style scheme.
    callback -- Custom function for handling tool text outputs.

raster_to_vector_polygons(i, output, callback=None) 
    Keyword arguments:

    i -- Input raster file.
    output -- Output vector polygons file.
    callback -- Custom function for handling tool text outputs.

clip(i, clip, output, callback=None) 
    Keyword arguments:

    i -- Input vector file.
    clip -- Input clip polygon vector file.
    output -- Output vector file.
    callback -- Custom function for handling tool text outputs.
"""

