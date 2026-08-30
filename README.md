# WatershedKit

WatershedKit is a Python-based hydrology and GIS workflow for DEM processing, watershed delineation, stream network extraction, morphometric analysis, and map/report generation.

## What this project does

This project analyzes a DEM to:

- fill or breach depressions in the terrain
- compute flow direction and flow accumulation
- extract stream networks using a threshold
- snap an outlet pour point to the stream network
- delineate the contributing watershed
- calculate catchment metrics such as area, perimeter, drainage density, stream frequency, basin length, relief, slope, and centroid-related parameters
- generate map outputs and a hydrology report for the analyzed catchment

The project is built around GIS and hydrologic processing libraries such as WhiteboxTools, rasterio, geopandas, shapely, and matplotlib.

## GitHub sharing model

This repository is intended to share the source code only. No sample DEM or generated output files are included in the GitHub version.

Users should keep their own DEM and output files locally on their machine.

## Local setup

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Place your DEM locally in a folder like `inputs/` on your machine.
5. Run the analysis:

   ```bash
   python gisops.py
   ```

## DEM configuration

The script can use a DEM from a local path by setting an environment variable before running:

```bash
set WATERSHEDKIT_DEM=C:\path\to\your\dem.tif
python gisops.py
```

On macOS/Linux:

```bash
export WATERSHEDKIT_DEM="/path/to/your/dem.tif"
python gisops.py
```

If no environment variable is set, the project will look for a local DEM file in the repository under `inputs/` if one exists.

## Typical workflow

Raw DEM -> depressions are removed -> D8 flow direction -> flow accumulation -> stream extraction -> stream ordering -> snap pour point -> delineate watershed -> compute morphometric parameters -> generate maps and reports.

## Optional AI insight report

The workflow also includes an optional AI-assisted report step. After the standard GIS report is generated, the script can send the DOCX report and the related maps/images to Google Gemini for an additional engineering interpretation.

What this function does:

- reads the generated hydrology report produced by the project
- collects the associated map outputs created during the analysis
- sends both the report and images to the Gemini API
- asks the AI to provide a hydrology-focused engineering interpretation using the generated catchment results and figures
- writes a second DOCX output file containing the AI-generated insights

This step is optional and requires a valid Gemini API key. The key is entered interactively at runtime using a secure prompt, so it is not stored in the source code.

This is just for experimentation. The outputs from AI always need to be verified as the AI models can hallucinate and change actual catchment parameters producing wrong insights.

## Inputs the script asks from the user

The workflow is interactive and expects the following inputs during execution:

1. Project name
   - Used as the identifier in result files and reports.
2. Breach-search distance in DEM cells
   - Example: `100`
   - Used for `breach_depressions_least_cost`.
   - Choose this according to your catchment. example - A higher value in some specific cases produce wrong stream network. For example - a breach dist of 100 cells can join two separate rivers if distance between them at any point along the path is less than 100 cells (Approx. 3km for 30m DEM)
3. Stream extraction threshold
   - Number of contributing cells used to define stream channels from the flow accumulation raster.
4. Outlet latitude in WGS84 (EPSG:4326)
   - Example: `20.4116564`
5. Outlet longitude in WGS84 (EPSG:4326)
   - Example: `72.8291320`
6. Contour interval in meters
   - Example: `100`
   - Used to generate contour lines from the clipped DEM.

## Important operational notes

- The script uses WhiteboxTools for the main hydrologic raster operations.
- The pour point is snapped to the nearest stream cell using Whitebox's `jenson_snap_pour_points` tool.
- In the current script, the snap distance is set to a default of `120` map units.
- This value is important because it controls how close the outlet point is moved to the stream before watershed delineation.
- If the outlet is far from a stream, increasing the snap distance may improve the connection, but it may also snap to a less appropriate stream segment.
- The DEM is checked for CRS and reprojected if needed before processing.

## Tools and libraries used by operation

### DEM and CRS handling
- `rasterio` - reading rasters, bounds, CRS, and clipping
- `pyproj` - coordinate reference system work
- `GDAL/OGR` - geospatial raster/vector support when needed
- `whitebox` - terrain processing and hydrologic analysis tools

### Flow and hydrology processing
- `whitebox.WhiteboxTools()`
- `breach_depressions_least_cost`
- `d8_pointer`
- `d8_flow_accumulation`
- `extract_streams`
- `strahler_stream_order`
- `jenson_snap_pour_points`
- `watershed`
- `longest_flowpath`
- `contours_from_raster`

### Vector and geometry operations
- `geopandas` - shapefile reading/writing and vector analysis
- `shapely` - geometry operations such as points, lines, polygons, and buffering
- `rasterstats` - zonal statistics for DEM metrics

### Mapping and reporting
- `matplotlib` - generating charts and plots
- `matplotlib_scalebar` - scale bar rendering on maps
- `python-docx` - report generation in DOCX format
- `google-genai` - optional AI-based hydrology report generation

### Data handling and calculations
- `numpy` - raster and numeric calculations
- `pandas` - summary tables and statistics
- `json` - result export to JSON files

## Example threshold guidance for stream extraction through Flow Accumulation Raster

You can use a threshold of your choice, but here is general guidance:

For a 30 m DEM:

- Dense: 100 cells
- Medium: 500 cells
- Sparse: 2500 cells

For a 12 m DEM:

- Dense: 500 cells
- Medium: 3000 cells
- Sparse: 15000 cells
