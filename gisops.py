from gistoolkit.reprojections import reproject_raster, check_and_choose_crs, create_pour_point_shp, fix_missing_prj
from gistoolkit.gistools import clip_streams_to_watershed, calculate_length_to_centroid, calculate_main_channel_length, calculate_basin_length
from gistoolkit.gistools import calculate_average_basin_slope, compute_channel_slope_parameters, calculate_hypsometric_parameters
from gistoolkit.gistools import save_hypsometric_curve_csv
from gistoolkit.maps import generate_outlet_map, generate_centroid_map, generate_contour_map, generate_longest_flow_path_map, generate_main_channel_map, generate_stream_map
from gistoolkit.gis_maps_utils import generate_hypsometric_plot
from config import PROJECT_DIR, OUTPUT_DIR, get_demo_dem_path
import whitebox
from pathlib import Path
import rasterio
import geopandas as gpd
from shapely.geometry import Point, shape 
from rasterio.features import shapes
import numpy as np
from rasterio.mask import mask
import math
from rasterstats import zonal_stats
from osgeo import gdal, ogr, osr
from gistoolkit.report_generator import generate_report
from gistoolkit.hydrology_ai_agent import generate_hydrology_report
import getpass # For secure API key input
import os
import json



wbt = whitebox.WhiteboxTools()
results = {}
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
dem = str(get_demo_dem_path())
dem_reprojected = OUTPUT_DIR / "dem_reprojected.tif"
breached_dem = OUTPUT_DIR / "breached_dem.tif"
project_crs = None
d8pointer = OUTPUT_DIR / "d8pointer.tif"
d8flowaccum = OUTPUT_DIR / "d8flowaccum.tif"
streamsraster = OUTPUT_DIR / "streamsraster.tif"
strahlerstreams = OUTPUT_DIR / "strahlerstreams.tif"
streamsvector = OUTPUT_DIR / "streamsvector.shp"
pourpoint = OUTPUT_DIR / "user_pourpoint_wgs84.shp"
pourpoint_snapped = OUTPUT_DIR / "pourpoint_snapped.shp"
watershedraster = OUTPUT_DIR / "watershedraster.tif"
watershedvector = OUTPUT_DIR / "watershedvector.shp"
watershedstreams_vector = OUTPUT_DIR / "watershedstreams.shp"
watershed_dem_clipped = OUTPUT_DIR / "watershed_dem_clipped.tif"
longest_flow_path = OUTPUT_DIR / "longest_flow_path.shp"
catchment_centroid = OUTPUT_DIR / "catchment_centroid.shp"
length_to_centroid_path = OUTPUT_DIR / "length_to_centroid_path.shp"
main_channel_length = OUTPUT_DIR / "main_channel_length.shp"
basin_length_line = OUTPUT_DIR / "basin_length_line.shp"
hypsometric_result = OUTPUT_DIR / "hypsometric_curve_result.csv"
catchment_contours = OUTPUT_DIR / "catchment_contours.shp"
#Saving maps
catchment_outlet_map = OUTPUT_DIR / "catchment_outlet_map.png"
catchment_streams_map = OUTPUT_DIR / "catchment_streams_map.png"
catchment_centroid_map = OUTPUT_DIR / "catchment_centroid_map.png"
catchment_longestflowpath_map = OUTPUT_DIR / "catchment_longestflowpath_map.png"
catchment_contour_map =  OUTPUT_DIR / "catchment_contour_map.png"
catchment_mainchannel_map = OUTPUT_DIR / "catchment_mainchannel_map.png"
hypsometric_curve_map = OUTPUT_DIR / "hypsometric_curve_map.png"
input_report_file = OUTPUT_DIR / "detailed_hydrology_report.docx"
output_ai_file = OUTPUT_DIR / "ai_insights_report.docx"
results_json_file = OUTPUT_DIR / "results.json"
avg_channel_slop_param_json = OUTPUT_DIR / "avg_channel_slope_parameters.json"


while True:
    project_name = input("Enter Project Name (3-35 Characters): ")
    if 3<len(project_name)<36:
        break
    else:
        print("Enter name strictly from 3 to 35 character length")

results["project_name"] = project_name

#Check CRS of provided DEM file
with rasterio.open(dem) as src:
        project_crs = src.crs

p = Path(dem_reprojected)
if p.exists():
    p.unlink()
#----------------------DEM CRS and Reprojection---------------------------
# Checking if DEM projected, if not choosing correct EPSG Code for reprojection
crscheck = check_and_choose_crs(dem)

#Reprojecting if DEM not projected
if crscheck is None:
    dem_reprojected=dem
else:
    project_crs=crscheck
    reproject_raster(dem, dem_reprojected, project_crs)

results["dem_crs"] = str(project_crs) #Result Saved to dictionary
#----------Raster+Vector operations to delineate catchment and derive drainage --------

#DEM - Breach Depressions to remove sinks and ensure proper flow routing
print("Breaching depressions in DEM to remove sinks and ensure proper flow routing")
print("The function takes distance parameter which is\nmaximum breach-search distance in DEM cells, not metres")
while True:
    try:
        breach_distance = int(input("Enter maximum breach-search distance in DEM cells (recommended 100): "))
        if breach_distance > 0:
            break
        else:
            print("Enter breach-search distance greater than zero")
    except ValueError:
        print("That's not a valid integer. Please try again.")
p = Path(breached_dem)
if p.exists():
    p.unlink()
wbt.breach_depressions_least_cost(dem_reprojected,breached_dem, breach_distance, callback=None)

#DEM - Flow Direction - D8_pointer
p = Path(d8pointer)
if p.exists():
    p.unlink()
wbt.d8_pointer(breached_dem, d8pointer, callback=None)

#DEM - Flow Accumulation - d8_flow_accumulation - feeding d8_pointer
p = Path(d8flowaccum)
if p.exists():
    p.unlink()
wbt.d8_flow_accumulation(d8pointer, d8flowaccum, pntr=True, callback=None)

#Asking Threshold for raster stream extraction
#Check input dem CRS and Resolution
with rasterio.open(dem_reprojected) as src:
    print("Your DEM Resolution is : ", src.res)
    xres, yres = src.res

if (28<= xres <=31):
    print("use the following threshold to generate stream network: \nDense: 100 cells\nMedium: 500 cells\nSparse: 2500 cells")
elif (10<= xres <=13):
    print("use the following threshold to generate stream network: \nDense: 500 cells\nMedium: 3000 cells\nSparse: 15000 cells")

thresh = int(input("Enter your threshold for deriving stream network: "))
results["streams_threshold"]=int(thresh) #Result Saved to dictionary

#Extract streams (binary raster) from flow accumulation
p = Path(streamsraster)
if p.exists():
    p.unlink()
wbt.extract_streams(d8flowaccum, streamsraster, thresh, callback=None)

#Strahler streams
p = Path(strahlerstreams)
if p.exists():
    p.unlink()
wbt.strahler_stream_order(d8pointer, streamsraster, strahlerstreams, callback=None)

#strahler stream to vector
p = Path(streamsvector)
if p.exists():
    p.unlink()
wbt.raster_streams_to_vector(strahlerstreams, d8pointer, streamsvector, callback=None)

#Fixing missing prj issue in raster_streams_to_vector
fix_missing_prj(streamsvector, project_crs)


print("You need to provide Lat-Longs of your pour point for catchment delineation"
"\n---PROVIDE STRICTLY GEOGRAPHICAL CRS (WGS84 - EPSG:4326) LAT-LONGS ")
print("MAKE SURE YOUR LAT-LONGS ARE IN WGS84 - EPSG:4326")

lat = float(input("ENTER COORDINATE - LATITUDE: "))
long = float(input("ENTER COORDINATE - LONGITUDE: "))
results["outlet_latitude_wgs84"] = lat     #Saving result
results["outlet_longitude_wgs84"] = long   #Saving result

#Creating pour point shapefile
p = Path(pourpoint)
if p.exists():
    p.unlink()
create_pour_point_shp(lat, long, project_crs, pourpoint)

#Snap pour point on stream 
p = Path(pourpoint_snapped)
if p.exists():
    p.unlink()
wbt.jenson_snap_pour_points(pourpoint, streamsraster, pourpoint_snapped, 120, callback=None)

#Delineate watershed to pour point
p = Path(watershedraster)
if p.exists():
    p.unlink()
wbt.watershed(d8pointer, pourpoint_snapped, watershedraster, callback=None)


#convert watershed raster to vector
p = Path(watershedvector)
if p.exists():
    p.unlink()
with rasterio.open(watershedraster) as src:
    data = src.read(1)

    polyresult = (
        {"geometry": shape(geom), "value": value}
        for geom, value in shapes(data, transform=src.transform)
        if value > 0
    )

    gdf = gpd.GeoDataFrame(list(polyresult), crs=src.crs)

watershed_boundary = gdf.dissolve()   # Merge all watershed polygons
watershed_boundary["geometry"] = watershed_boundary.buffer(0)    # Fix geometry if needed
watershed_boundary.to_file(watershedvector)  #Save watershed vector boundary to file.
"""

"""
#Clip vector streams to watershed boundary
p = Path(watershedstreams_vector)
if p.exists():
    p.unlink()
clip_streams_to_watershed(streamsvector, watershedvector, watershedstreams_vector)


#Clipping Raw Projected DEM by catchment/watershed boundary.
p =Path(watershed_dem_clipped)
if p.exists():
    p.unlink()

gdf = gpd.read_file(watershedvector)
with rasterio.open(dem_reprojected) as src:
    clipped, transform = mask(
        src,
        gdf.geometry,
        crop=True
    )

    meta = src.meta.copy()
    meta.update({
        "height": clipped.shape[1],
        "width": clipped.shape[2],
        "transform": transform
    })

    with rasterio.open(watershed_dem_clipped, "w", **meta) as dst:
        dst.write(clipped)




#--------------------1. Morphometric Parameters-----------------------------
#--------------------1.1 Linear Aspects-------------------------------
#--------------------1.1.A - Stream Order at outlet point-----------
gdf = gpd.read_file(pourpoint_snapped)
point = gdf.geometry.iloc[0]
pourx = point.x
poury = point.y
results["outlet_latitude"] = float(poury) #Saving result to dictionary
results["outlet_longitude"] = float(pourx) #Saving result to dictionary

with rasterio.open(strahlerstreams) as src:
    generator = src.sample([(pourx,poury)])
    for val in generator:
        pour_stream_order = val[0]
        print(f"Your catchment outlet is on stream order No.: {pour_stream_order}")

results["outlet_stream_order"] = int(pour_stream_order) #Saving result to dictionary

#-------------------1.1.B - Stream Length and Mean stream Length----
gdf_streams = gpd.read_file(watershedstreams_vector)
gdf_streams["length_m"] = gdf_streams.geometry.length

#Total Length of all streams
total_length = gdf_streams["length_m"].sum()
print(f"Total stream length: {total_length:,.2f} m ({total_length/1000:,.2f} km)")
results["all_streams_length"] = float(total_length) #Saving result to dictionary

summary = (
    gdf_streams
    .groupby("STRM_VAL")
    .agg(
        n_streams=("STRM_VAL", "size"),
        total_length_m=("length_m", "sum"),
        mean_length_m=("length_m", "mean")
    )
    .reset_index()
    .sort_values("STRM_VAL")
)
results["streams_summary"] = summary.set_index("STRM_VAL").to_dict("index")
print(summary)

#-------------------1.1.C - Bifurcation Ratio-----------------------
#Bifurcation Ratio
summary["Rb"] = (
    summary["n_streams"] /
    summary["n_streams"].shift(-1)
)
results["streams_summary"] = summary.set_index("STRM_VAL").to_dict("index") #Saving in results
print(summary[["STRM_VAL", "Rb"]])

#-------------------1.1.D - Stream Length Ratio---------------------
summary["Rl"] = (
    summary["mean_length_m"].shift(-1) /
    summary["mean_length_m"]
)
results["streams_summary"] = summary.set_index("STRM_VAL").to_dict("index") #Saving in results
print(summary[["STRM_VAL", "Rl"]])



#--------------1.1.E - EXTRACT LENGTH, ELEVATION DROP, AND SLOPE FOR Tc FORMULA-------------
#Generating Shp for longest flow path
p = Path(longest_flow_path)
if p.exists():
    p.unlink()
wbt.longest_flowpath(breached_dem, watershedraster, longest_flow_path)
#The resulting shp attribute table contains values of - UP_ELEV, DN_ELEV, LENGTH & AVG_SLOPE(%)


#Calculate Time of Concentration Tc - Kirpich Formula in SI Units
lfp = gpd.read_file(longest_flow_path)
print(lfp[["FID", "BASIN", "UP_ELEV", "DN_ELEV", "LENGTH", "AVG_SLOPE"]])
row = lfp.iloc[0]
results["longest_path_up_elevation"] = row["UP_ELEV"]  #saving result
results["longest_path_down_elevation"] = row["DN_ELEV"]  #saving result
results["length_longest_path"] = row["LENGTH"]  #saving result
results["longest_path_avgslope_percent"] = row["AVG_SLOPE"]  #saving result
# ============================================================
# COMPUTE TIME OF CONCENTRATION (Kirpich, SI form)
# Tc (min) = 0.0195 * L^0.77 * S^-0.385
#   L = flow length in meters
#   S = slope in m/m (dimensionless fraction)
# ============================================================
lfp["S_frac"] = lfp["AVG_SLOPE"] / 100.0   # convert percent -> m/m

lfp["Tc_min"] = 0.0195 * (lfp["LENGTH"] ** 0.77) * (lfp["S_frac"] ** -0.385)
lfp["Tc_hr"]  = lfp["Tc_min"] / 60

print(lfp[["BASIN", "LENGTH", "AVG_SLOPE", "Tc_min", "Tc_hr"]])
row = lfp.iloc[0]
results["timeof_concentration_kirpich_min"] = row["Tc_min"]  #saving result

#--------------1.1.F - Sinuosity index for the Longest flow path -------------
lfp = gpd.read_file(longest_flow_path)
line = lfp.geometry.iloc[0]
start = Point(line.coords[0])
end = Point(line.coords[-1])
distance = start.distance(end)
sinuosity = lfp["LENGTH"].iloc[0]/distance
print(f"Direct distance: {distance:.2f}")
print(f"Sinuosity Index for the Longest flow path is:{sinuosity:.2f}")


#--------------1.1.G - Main Channel Length of catchment (meters) and saving channel to shp-------------
p = Path(main_channel_length)
if p.exists():
    p.unlink()
MCL = calculate_main_channel_length(watershedstreams_vector, pourpoint_snapped, main_channel_length)
results["main_channel_length"] = MCL
print(f"Length of main channel in catchment is: {MCL:.2f} meters or {(MCL/1000):.3f} KM")

#saving coordinated of main channel outlet and upstream point
gdf_main_channel = gpd.read_file(main_channel_length)
outlet_x = gdf_main_channel['Out_X'].iloc[0]
outlet_y = gdf_main_channel['Out_Y'].iloc[0]
upstream_x = gdf_main_channel['Up_X'].iloc[0]
upstream_y = gdf_main_channel['Up_Y'].iloc[0]
results["main_channel_outlet_x"] = outlet_x  #Saving result
results["main_channel_outlet_y"] = outlet_y   #Saving result
results["main_channel_upstream_x"] = upstream_x   #Saving result
results["main_channel_upstream_y"] = upstream_y    #Saving result

#Saving elevation values of both ends of main channel from DEM
main_channel = gpd.read_file(main_channel_length)
with rasterio.open(dem_reprojected) as dem:
    if dem.crs != main_channel.crs:
        raise ValueError(
            f"CRS mismatch: DEM is {dem.crs}, shapefile is {main_channel.crs}. "
            "Reproject one to match the other before sampling."
        )

    coords = [(outlet_x, outlet_y), (upstream_x, upstream_y)]
    samples = list(dem.sample(coords))

    out_elev = samples[0][0]
    up_elev = samples[1][0]

    nodata = dem.nodata
    if nodata is not None:
        out_elev = None if out_elev == nodata else out_elev
        up_elev = None if up_elev == nodata else up_elev

results["main_outlet_elevation"] = out_elev
results["main_upstream_elevation"] = up_elev

#Slope of main channel 
main_channel_slope = ((results["main_upstream_elevation"]-results["main_outlet_elevation"])/results["main_channel_length"])*100
results["main_channel_slope_percent"] = main_channel_slope
"""

"""
#============================================================================
#--------------------1. Morphometric Parameters-----------------------------
#--------------------1.2 Areal Aspects-------------------------------
#--------------------1.2.A Catchment/Watershed Area & Perimeter-----------
catchment = gpd.read_file(watershedvector)
catchment_area = catchment.geometry.area.iloc[0]
catchment_perimeter = catchment.geometry.length.iloc[0]
catch_centorid = catchment.geometry.centroid.iloc[0]
centroidx = catch_centorid.x
centroidy = catch_centorid.y
p = Path(catchment_centroid)
if p.exists():
    p.unlink()
centroid_gdf = gpd.GeoDataFrame(
    {
        "X_proj": [centroidx],
        "Y_proj": [centroidy]
    },
    geometry=[catch_centorid],
    crs=catchment.crs
)
centroid_gdf.to_file(catchment_centroid)
results["catchment_centroid_latitude"] = float(centroidy)
results["catchment_centroid_longitude"] = float(centroidx)
results["catchment_area_m2"] = catchment_area    #Saving results
results["catchment_perimeter_m"] = catchment_perimeter   #Saving results
print(f"The catchment area is: {catchment_area/10000} Hectares")
print(f"The perimeter of catchment is: {catchment_perimeter} meters")



#----1.2.B - Drainage Density (km/km2)--- 
drainage_density = (results["all_streams_length"]/1000) / (results["catchment_area_m2"]/1e6)
results["drainage_density_km"] = drainage_density #Saving results
print(f"Drainage Density of catchment is: {drainage_density} km/km2")

#----1.2.C - Stream Frequency Nos/km2---
total_streams_nos = sum(
    order_data["n_streams"]
    for order_data in results["streams_summary"].values()
)
results["nos_streamsof_catchment"] = total_streams_nos   #Saving results
stream_frequency = (total_streams_nos/(results["catchment_area_m2"]/1e6))
results["stream_frequency_km2"] = stream_frequency
print(f"Stream Frequency of catchment is: {stream_frequency} streams per km2")
 

#----1.2.D - Basin Length Lb---
lb = calculate_basin_length(watershedvector, pourpoint_snapped, basin_length_line)
results["basin_length"] = float(lb)
print(f"Basin Length is: {lb:.2f} meters or {(lb/1000):.3f} KM")



#----1.E. - Form Factor---
ff = (results["catchment_area_m2"]/(results["basin_length"]**2))
results["form_factor"] = float(ff)
print(f"Form Factor for Catchment is: {ff:.2f}")


#----1.F. - Shape Factor / Elongation Ratio---
er = ((2*(math.sqrt(results["catchment_area_m2"]/(math.pi))))/results["basin_length"])
results["elongation_ratio"] = float(er)
print(f"Elongation Ratio / Shape Factor for Catchment is: {er:.2f}")

#----1.G. - Circulatory Ratio---
cr = ((4*(math.pi)*results["catchment_area_m2"])/(results["catchment_perimeter_m"]**2))
results["circulatory_ratio"] = float(cr)
print(f"Circulatory Ratio for Catchment is: {cr:.2f}")

#----1.2.H - Compactness coefficient---
cc = (0.2821*(results["catchment_perimeter_m"]/(math.sqrt(results["catchment_area_m2"]))))
results["compactness_coefficient"] = float(cc)
print(f"Compactness Coefficient for Catchment is: {cc:.2f}")

#----1.2. - Constant of Channel Maintenance (inverse of drainage density)---
ccm = (1/results["drainage_density_km"])
results["constant_channel_maintenance_km"] = float(ccm)
print(f"Constant of channel maintenance for Catchment is: {ccm:.2f}")

#----1.2. - Infiltration Number----------
ifn = (results["drainage_density_km"]*results["stream_frequency_km2"])
results["infiltration_number_km"] = float(ifn)
print(f"Infiltration Number for Catchment is: {ifn:.2f}")



#=========================================================================
#-------------------1.3 Relief Aspects-------------------------------------
#----1.3.A - Basin Relief-------
watershed_dem = zonal_stats(watershedvector, watershed_dem_clipped)
watershed_max_elev = watershed_dem[0]['max']
watershed_min_elev = watershed_dem[0]['min']
basin_relief = watershed_max_elev - watershed_min_elev
results["watershed_max_elev"] = watershed_max_elev
results["watershed_min_elev"] = watershed_min_elev
results["basin_relief_m"] = float(basin_relief)
print(f"Basin Relief of catchment: {basin_relief:.2f}")

#----1.3.B - Relief Ratio-------
rr = (results["basin_relief_m"]/results["basin_length"])
results["relief_ratio_m"] = float(rr)  
print(f"Relief Ratio of catchment: {rr:.2f}")      

#----1.3.C - Ruggedness Number (Basin relief x drainage Density)-------
rgn = ((results["basin_relief_m"]/1000)*results["drainage_density_km"])
results["ruggedness_number_km"] = float(rgn)
print(f"Ruggedness Number of Catchment is: {rgn:.2f}")


#----1.3.D - Slope of channel/Average channel slope/ equilibrium slope of longest flow path-------
#If the channel is too short (only upto 10 points of stream) the function only calculate simple end to end slope and not 
#equal elevation drop slope and equal length slope.
#always use equal elevation slope for further calculations and equal length for validation check
avg_channel_slop_parameters = compute_channel_slope_parameters(
    stream_shp_path=main_channel_length,
    catchment_shp_path=watershedvector,
    dem_clipped_path=watershed_dem_clipped,
)
print(avg_channel_slop_parameters)  #this is results as a dictionary



#----1.3.E - Hypsometric curve/integral-------
p = Path(hypsometric_result)
if p.exists():
    p.unlink()
hypsometric_curve = calculate_hypsometric_parameters(watershed_dem_clipped)
print(hypsometric_curve)
save_hypsometric_curve_csv(hypsometric_curve, hypsometric_result)


#----1.3.F - Slope of Basin (True Average Basin slope)-------
true_basin_slope = calculate_average_basin_slope(watershed_dem_clipped)
results["true_basin_slope_percent"] = float(true_basin_slope)
print(f"The average basin slope is: {true_basin_slope:.2f}%")

#----1.3. - Centroid/Length to centroid-------
p = Path(length_to_centroid_path)
if p.exists():
    p.unlink()
L_ca = calculate_length_to_centroid(watershedstreams_vector, pourpoint_snapped, catchment_centroid, length_to_centroid_path)
print(f"Length to centoid is: {L_ca:.2f} meters or {(L_ca/1000):.3f} KM")
results["length_to_centroid_m"] = L_ca


#Generating contours for catchment
while True:
    try:
        contour_interval = float(input("Enter Contour interval in Meters above zero: "))
        if contour_interval > 0:
            break
        else:
            print("Enter contour interval greater than zero")
    except ValueError:
        print("That's not a valid integer. Please try again.")

results["user_selected_contour_interval"] = contour_interval  #Saving results
p = Path(catchment_contours)
if p.exists():
    p.unlink()
wbt.contours_from_raster(watershed_dem_clipped, catchment_contours, interval=contour_interval)

#===============================================
# Generate and save different maps

#1. Outlet Map with catchment boundary
p = Path(catchment_outlet_map)
if p.exists():
    p.unlink()
generate_outlet_map(watershedvector, pourpoint_snapped, catchment_outlet_map, title="Catchment Boundary with Outlet")


#2. stream network map with catchment boundary
p = Path(catchment_streams_map)
if p.exists():
    p.unlink()
generate_stream_map(watershedvector, watershedstreams_vector, catchment_streams_map)

#3. centroid map with catchment boundary
p = Path(catchment_centroid_map)
if p.exists():
    p.unlink()
generate_centroid_map(watershedvector, length_to_centroid_path, catchment_centroid, catchment_centroid_map, title="Length to Centroid")

#4. longest flow path map with catchment boundary
p = Path(catchment_longestflowpath_map)
if p.exists():
    p.unlink()
generate_longest_flow_path_map(watershedvector, longest_flow_path, catchment_longestflowpath_map, title="Catchment Longest Flow Path")

#5. main channel map with catchment boundary
p = Path(catchment_mainchannel_map)
if p.exists():
    p.unlink()
generate_main_channel_map(watershedvector, main_channel_length, catchment_mainchannel_map, title="Catchment Main Channel")


#6. contour path map with catchment boundary
p = Path(catchment_contour_map)
if p.exists():
    p.unlink()
generate_contour_map(watershedvector, catchment_contours, catchment_contour_map, title="Contour Map of Catchment", elevation_col="HEIGHT")


#7. hypsometric curve plot
p = Path(hypsometric_curve_map)
if p.exists():
    p.unlink()
generate_hypsometric_plot(input_csv=hypsometric_result, output_png=hypsometric_curve_map, projectname=project_name)

#Printing Results and Saving to JSON file
p = Path(results_json_file)
if p.exists():
    p.unlink()  

p = Path(avg_channel_slop_param_json)
if p.exists():  
    p.unlink()

print("All Stored Results : ")
print(results)
print(avg_channel_slop_parameters)

with open(results_json_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, default=str)

with open(avg_channel_slop_param_json, "w", encoding="utf-8") as f:
    json.dump(avg_channel_slop_parameters, f, indent=4, default=str)

p = Path(input_report_file)
if p.exists():
    p.unlink()
#Generating Final report
maps = {
    "outlet": catchment_outlet_map,
    "stream_network": catchment_streams_map,
    "centroid": catchment_centroid_map,
    "longest_flow_path": catchment_longestflowpath_map,
    "main_channel": catchment_mainchannel_map,
    "contour_path": catchment_contour_map,
    "hypsometric_curve": hypsometric_curve_map
}

generate_report(
    results=results,
    slope_results=avg_channel_slop_parameters,
    maps=maps,
    output_docx=input_report_file
)



#=========================================
#Generate Final Report using Gemini API
#===========================================
p = Path(output_ai_file)
if p.exists():
    p.unlink()
def main():
    # Prompt the user for the API key securely (keystrokes will be hidden)
    user_api_key = getpass.getpass("Please enter your Gemini API Key: ")
    
    # Pass the key into your function
    generate_hydrology_report(
        input_docx_path=input_report_file,
        output_docx_path=output_ai_file,
        api_key=user_api_key
    )

if __name__ == "__main__":
    main()
