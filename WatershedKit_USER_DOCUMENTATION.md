# WatershedKit — User Documentation

WatershedKit is a Python-based hydrology and GIS workflow for processing a Digital Elevation Model (DEM), delineating a watershed, extracting a stream network, calculating catchment morphometric parameters, and generating maps and hydrology reports.

This guide is intended for users who obtain the project from GitHub and want to run it on their own DEM and outlet location.

> **Important:** WatershedKit is a technical hydrology/GIS workflow, not a substitute for engineering review. Parameter choices—especially DEM conditioning, stream threshold, outlet snapping, and design-parameter interpretation—should be checked against the characteristics of the study area and the applicable design standards.

---

## 1. What WatershedKit Does

The standard workflow is:

```text
User DEM
   │
   ├── Check/reproject DEM CRS
   │
   ├── Condition DEM
   │     └── Fill/breach depressions
   │
   ├── D8 flow direction
   │
   ├── D8 flow accumulation
   │
   ├── Stream extraction using a user-defined threshold
   │
   ├── Stream ordering
   │
   ├── Snap outlet/pour point to stream network
   │
   ├── Watershed delineation
   │
   ├── Longest flow-path and channel analysis
   │
   ├── Morphometric calculations
   │
   ├── Maps and figures
   │
   └── Hydrology report
              │
              └── Optional Gemini AI interpretation
```

The project uses WhiteboxTools for the principal hydrologic raster operations and Python geospatial libraries for raster, vector, geometry, calculation, mapping, and report generation.

---

## 2. Repository / GitHub Usage Model

The GitHub version is intended to contain **source code only**.

Do not expect the repository to contain:

- a sample DEM;
- generated watershed rasters;
- generated stream shapefiles;
- generated maps;
- generated reports;
- project-specific output data.

Keep your own input DEM and generated outputs locally.

A typical local arrangement is:

```text
WatershedKit/
├── gisops.py
├── requirements.txt
├── inputs/
│   └── your_dem.tif
└── ...
```

The exact repository structure may contain additional Python modules and supporting files.

---

## 3. Requirements

WatershedKit is built around the following categories of tools and libraries.

### GIS and DEM processing

- `rasterio` — raster reading, CRS, bounds and clipping.
- `pyproj` — coordinate reference system operations.
- `GDAL/OGR` — geospatial raster/vector support where required.
- `whitebox` — terrain and hydrologic processing.

### Hydrologic processing

The workflow uses WhiteboxTools operations including:

- `breach_depressions_least_cost`
- `d8_pointer`
- `d8_flow_accumulation`
- `extract_streams`
- `strahler_stream_order`
- `jenson_snap_pour_points`
- `watershed`
- `longest_flowpath`
- `contours_from_raster`

### Vector and geometry processing

- `geopandas`
- `shapely`
- `rasterstats`

### Mapping and reporting

- `matplotlib`
- `matplotlib_scalebar`
- `python-docx`

### Data and calculations

- `numpy`
- `pandas`
- `json`

### Optional AI report

- `google-genai`

Install the project dependencies with:

```bash
pip install -r requirements.txt
```

A virtual environment is strongly recommended.

---

# 4. Installation

## 4.1 Clone the repository

From a terminal:

```bash
git clone <YOUR-REPOSITORY-URL>
cd WatershedKit
```

Replace `<YOUR-REPOSITORY-URL>` with the repository URL shown on GitHub.

## 4.2 Create a virtual environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4.3 Install dependencies

```bash
pip install -r requirements.txt
```

If your environment requires additional GIS system packages, install those according to the operating system and the dependency installation guidance used by the project.

---

# 5. Prepare Your DEM

WatershedKit expects a DEM in GeoTIFF form (`.tif`).

Before running the workflow, check:

1. The DEM covers the area of interest.
2. Elevations are valid and not dominated by unexpected NoData gaps.
3. The DEM resolution is known.
4. The DEM CRS is known.
5. The outlet coordinates correspond to the DEM/catchment being analyzed.

The script checks the DEM CRS and reprojects it when necessary before processing.

### Projected CRS is especially important for slope calculations

The average basin slope calculation requires DEM cell dimensions in metres. The technical documentation notes that using a geographic CRS measured in degrees can produce silently incorrect slope values rather than an obvious error.

Therefore, use or allow the workflow to produce a projected DEM with metre-based units before relying on slope parameters.

---

# 6. Supplying the DEM

WatershedKit supports a local DEM path through the `WATERSHEDKIT_DEM` environment variable.

## Windows Command Prompt

```bat
set WATERSHEDKIT_DEM=C:\path\to\your\dem.tif
python gisops.py
```

## macOS / Linux

```bash
export WATERSHEDKIT_DEM="/path/to/your/dem.tif"
python gisops.py
```

If `WATERSHEDKIT_DEM` is not set, the project can look for a local DEM under:

```text
inputs/
```

if a suitable DEM is present there.

### Recommended practice

For GitHub-based use, keep large DEM files outside the repository or in a local ignored directory. Do not commit project-specific DEMs or generated results unless you intentionally want to distribute them.

---

# 7. Running the Workflow

Start the workflow with:

```bash
python gisops.py
```

The program is interactive and asks for several project-specific parameters.

The workflow then performs the hydrologic/GIS processing and generates the associated maps, parameter results, and hydrology report.

---

# 8. User Inputs

## 8.1 Project name

The project name identifies the analysis and is used in result files and reports.

Example:

```text
Damanganga_Catchment
```

Choose a short, meaningful name without unusual characters where possible.

---

## 8.2 Breach-search distance

This is the search distance supplied to:

```text
breach_depressions_least_cost
```

The value is expressed in **DEM cells**, not metres.

Example:

```text
20
```

### Why this parameter matters

DEM conditioning can create drainage connections when depressions are breached. If the search distance is too large, the algorithm may create an artificial connection between drainage systems that should remain separate.

A documented failure case demonstrated this clearly:

- `dist = 100` cells caused an artificial connection between the Damanganga River and an adjacent independent river system.
- The resulting catchment area became `2,533.95 km²`, compared with a reported reference value of `2,318 km²`.
- Reducing the value to `20` cells removed the artificial inter-basin connection.
- The resulting catchment area became `2,278.88 km²`, approximately 1.69% lower than the reported reference value.

The documentation therefore adopted `20` cells for that study area.

**Do not treat 20 cells as a universal value.** The appropriate breach distance depends on the study area, DEM resolution, terrain, and drainage structure.

The README also gives an important example for a 30 m DEM: a breach distance of 100 cells can permit connections across distances of roughly 3 km. This illustrates why a seemingly reasonable cell count can become a very large physical search distance.

### Practical recommendation

Start with a conservative value and inspect the resulting drainage network. If the value is increased, verify that separate rivers or basins have not been artificially connected.

---

## 8.3 Stream extraction threshold

The stream threshold determines how many contributing DEM cells are required for a location to be considered part of the extracted stream network.

In conceptual form:

```text
Flow accumulation
       │
       └── threshold
              │
              └── extracted stream raster
```

The threshold should be considered together with DEM resolution.

### Example guidance

For a 30 m DEM:

| Desired drainage density | Example threshold |
|---|---:|
| Dense | 100 cells |
| Medium | 500 cells |
| Sparse | 2,500 cells |

For a 12 m DEM:

| Desired drainage density | Example threshold |
|---|---:|
| Dense | 500 cells |
| Medium | 3,000 cells |
| Sparse | 15,000 cells |

These are **general starting points**, not universal hydrologic standards.

A lower threshold generally produces a denser extracted network; a higher threshold produces a sparser network.

---

## 8.4 Outlet latitude

Enter the outlet latitude in WGS84 / EPSG:4326.

Example:

```text
20.4116564
```

---

## 8.5 Outlet longitude

Enter the outlet longitude in WGS84 / EPSG:4326.

Example:

```text
72.8291320
```

The coordinates should represent the intended watershed outlet/pour point.

---

## 8.6 Contour interval

Enter the desired contour interval in metres.

Example:

```text
100
```

This is used when generating contour lines from the processed/clipped DEM.

---

# 9. Outlet Snapping

The supplied outlet coordinates may not fall exactly on an extracted stream cell.

WatershedKit uses WhiteboxTools:

```text
jenson_snap_pour_points
```

to move the pour point toward the stream network before watershed delineation.

The current script uses a default snap distance of:

```text
120 map units
```

For a DEM with metre-based projected coordinates, this corresponds to approximately 120 m.

### Why the snap distance matters

A snap distance that is too small may fail to connect an accurately intended outlet to the extracted stream.

A snap distance that is too large can move the outlet onto an inappropriate stream segment.

If the outlet is far from the extracted stream, increasing the snap distance may help, but the resulting snapped location should always be checked.

---

# 10. Processing Stages

## 10.1 DEM conditioning

The workflow first conditions the DEM by addressing depressions using WhiteboxTools.

The current workflow uses least-cost depression breaching.

This step is important because unconditioned DEM depressions can interrupt downstream flow.

However, excessive breaching can produce artificial drainage connections. The breach distance therefore requires study-area-specific validation.

---

## 10.2 D8 flow direction

The conditioned DEM is used to calculate D8 flow direction.

Each cell is assigned a flow direction toward one of its neighbouring cells under the D8 method.

This raster forms the basis for downstream flow-routing calculations.

---

## 10.3 D8 flow accumulation

Flow accumulation estimates the number of upstream contributing cells draining through each cell.

This raster is then used to identify potential stream channels.

---

## 10.4 Stream extraction

The flow accumulation raster is thresholded using the user-provided stream extraction threshold.

Conceptually:

```text
Flow accumulation ≥ threshold
             ↓
       Stream network
```

The selected threshold has a direct effect on the density and extent of the extracted stream network.

---

## 10.5 Stream ordering

The workflow uses Strahler stream ordering to describe the hierarchical structure of the extracted drainage network.

Stream order is a morphometric parameter used to characterize drainage development and network complexity.

---

## 10.6 Outlet snapping

The WGS84 outlet coordinates are converted into the working coordinate system as necessary, then snapped toward the extracted stream network using the configured snap distance.

---

## 10.7 Watershed delineation

The snapped pour point is used to delineate the contributing catchment.

The resulting catchment polygon is then used for subsequent morphometric and terrain calculations.

---

## 10.8 Longest flow path

The workflow identifies the longest flow path through the drainage system.

It is important to distinguish this from the main channel length:

- **Longest flow path:** includes the distance water needs to travel from the hydraulically distant part of the catchment toward the outlet, including the overland component described by the project's design-parameter documentation.
- **Main channel length:** length of the stream extending farthest upstream from the outlet; it does not include the overland distance before water reaches the stream.

This distinction matters when interpreting time-of-concentration and other hydrologic parameters.

---

# 11. Morphometric Parameters

The project calculates or supports parameters used to describe basin geometry, drainage characteristics, relief, and hydrologic response.

The accompanying design-parameter reference identifies these as important inputs for water-related structures such as dams, spillways, canals, culverts, bridges, check dams, weirs, and drainage systems.

## 11.1 Linear parameters

Examples include:

- stream order;
- stream length and mean stream length;
- stream length ratio;
- bifurcation ratio;
- sinuosity of the longest path;
- longest flow-path length;
- elevation at the outlet and distant catchment point;
- average slope of the longest flow path;
- time of concentration;
- main channel length.

The design reference notes that stream order describes drainage hierarchy and network complexity, while stream length characteristics reflect terrain slope and runoff behaviour.

---

## 11.2 Areal parameters

Examples include:

- drainage/catchment area;
- drainage density;
- stream frequency;
- drainage texture;
- basin length;
- form factor;
- shape factor / elongation ratio;
- circularity ratio;
- compactness coefficient;
- constant of channel maintenance;
- infiltration number.

The design reference describes drainage density as total stream length per unit basin area and stream frequency as the number of stream segments per unit area.

Basin length is described as the straight-line distance from the outlet to the furthest point on the watershed boundary. Form factor, elongation/shape ratio, circularity ratio and compactness coefficient are used to characterize basin shape and compactness.

---

## 11.3 Relief parameters

The workflow's design context includes:

- basin relief;
- relief ratio;
- ruggedness number;
- channel/longest-flow-path slope;
- true average basin slope;
- hypsometric curve/integral;
- time of concentration;
- basin perimeter;
- basin centroid;
- length to centroid.

The reference defines basin relief as the difference between the highest and lowest basin elevations and identifies relief ratio and ruggedness number as terrain/erosion-related indicators.

---

# 12. Average Basin Slope

The average basin slope is different from the slope of the longest flow path.

WatershedKit calculates average basin slope from the DEM using **Horn's Method** over a moving 3×3 neighbourhood. The resulting per-cell slopes are averaged across valid cells inside the catchment.

## 12.1 Horn's method

For a 3×3 elevation window:

```text
a  b  c
d  e  f
g  h  i
```

the method estimates the x and y elevation gradients using weighted neighbouring cells:

```text
dz/dx = [(c + 2f + i) - (a + 2d + g)] / (8 × cell_size_x)

dz/dy = [(g + 2h + i) - (a + 2b + c)] / (8 × cell_size_y)
```

The slope magnitude is:

```text
slope = sqrt((dz/dx)^2 + (dz/dy)^2)
```

and is converted to percentage by multiplying by 100.

The final basin value is the arithmetic mean of valid per-cell slope percentages. NoData/masked cells are excluded using NaN-aware averaging.

## 12.2 Important limitation

Boundary cells can be lost when their 3×3 neighbourhood touches NoData outside the catchment. This can exclude a meaningful fraction of the basin in small catchments and potentially bias the average toward interior terrain.

The technical documentation recommends logging the fraction of valid cells actually used, particularly for small catchments.

The DEM should be masked to the actual catchment polygon rather than merely clipped to a rectangular bounding box.

---

# 13. Longest Flow-Path / Channel Slope

WatershedKit separately calculates parameters describing the slope of the catchment's longest flow path.

This is intended to provide the `Sc` equivalent stream slope used in CWC Synthetic Unit Hydrograph relationships. The accompanying technical documentation specifically distinguishes this parameter from the general average basin slope.

## 13.1 Simple slope

The simple end-to-end slope is:

```text
S = H / L
```

where:

- `H` = elevation difference between upstream-most and downstream-most sampled points;
- `L` = total channel length.

It is always calculated and is useful as a sanity check.

## 13.2 Equivalent Taylor-Schwarz slope

For the equivalent slope, the workflow uses:

```text
Sc = [ ΣLi / Σ(Li / √Si) ]²
```

where:

- `Li` = length of segment `i`;
- `Si` = slope of segment `i`;
- `Si = hi / Li`;
- `hi` = elevation drop across the segment.

This equivalent slope accounts for the fact that long, flatter reaches have a disproportionate effect on travel time.

## 13.3 Segmentation

Two segmentation approaches are implemented:

1. **Equal elevation-drop segmentation**
   - divides total elevation fall into equal increments;
   - finds corresponding channel positions by interpolation.

2. **Equal-length segmentation**
   - divides total channel length into equal-length segments;
   - evaluates elevation drop within each segment.

The two approaches can differ in irregular or noisy terrain.

## 13.4 Automatic segment selection

The workflow does not simply maximize the number of segments.

Instead it:

1. smooths the sampled elevation profile;
2. estimates DEM vertical noise;
3. tests candidate segment counts, normally from 4 to 30 subject to available samples;
4. checks whether consecutive equivalent-slope estimates stabilize;
5. selects the smallest segment count meeting the convergence criterion;
6. skips invalid candidates rather than immediately failing.

The documented stabilization tolerance is 3% over several consecutive candidate counts.

---

# 14. Channel-Slope Method Selection

The channel-slope function changes its calculation strategy depending on catchment/channel characteristics.

| Condition | Method |
|---|---|
| Fewer than 10 elevation sample points | Simple end-to-end slope only |
| Catchment area > 100 km² | Equal-length equivalent slope only |
| Catchment area ≤ 100 km² and channel is sufficiently long | Equal-elevation-drop and equal-length equivalent slopes |
| Total relief below the estimated noise floor | Minimum slope floor with warning |

These rules are documented in the technical specification for the channel-slope calculation.

The returned result can include:

```text
catchment_area_km2
channel_length_km
method_used
simple_slope
equal_elevation_drop
equal_length
warnings
```

The function is designed to distinguish genuine input/data problems from expected hydrologic cases such as a flat catchment or very short channel.

---

# 15. Length to Centroid

Length to centroid (`L_ca`) is treated as a flow-path parameter rather than simply a straight-line distance.

The project documentation describes it as the distance along the main stream/flow path from the outlet to the point on the flow path closest to the catchment centroid.

The current approach snaps the centroid to the nearest stream-line vertex rather than calculating an exact perpendicular intersection on a line segment. For DEM-derived streams, whose vertices can occur at roughly 10–30 m intervals, the documentation considers this difference statistically negligible for hydrologic routing.

### Network topology warning

If a manually drawn stream network contains tiny gaps at tributary junctions, the graph used by the calculation can become disconnected and produce a `NetworkXNoPath` error.

In such a case, repair the stream topology in QGIS/ArcGIS—for example by snapping geometries—before rerunning the calculation.

---

# 16. Hydrologic Design Context

The project focuses on catchment parameters that can be used as inputs to broader hydrologic and water-structure design workflows.

The design-parameter reference groups relevant quantities into:

- morphometric/basin geometry parameters;
- hydrometeorological parameters;
- runoff and streamflow parameters;
- hydraulic parameters;
- soil and land-use parameters;
- groundwater parameters;
- sediment and erosion parameters;
- reservoir/structure-specific parameters;
- broader design considerations.

The first four pages of the supplied design-parameter reference specifically emphasize basin geometry, relief, channel slope, basin slope, time of concentration, perimeter, centroid and length-to-centroid parameters.

For example, the reference identifies:

- drainage area as a primary input for peak discharge and reservoir-capacity estimation;
- drainage density as an indicator related to runoff efficiency and flood response speed;
- basin relief as a control on stream gradient and flow velocity;
- time of concentration as central to peak-discharge calculations;
- channel slope as an input to CWC SUH applications;
- true average basin slope as a DEM-derived terrain parameter.

WatershedKit itself does **not** automatically turn the catchment parameters into a final structural design unless the relevant design calculations are explicitly implemented in the project.

---

# 17. Maps and Reports

The workflow generates map outputs and a hydrology report associated with the analyzed catchment.

Depending on the current version of the project, generated outputs can include products associated with:

- DEM/terrain;
- conditioned DEM;
- flow direction;
- flow accumulation;
- extracted streams;
- stream order;
- watershed boundary;
- longest flow path;
- contours;
- catchment statistics;
- morphometric parameters.

Because generated outputs are intentionally excluded from the GitHub sharing model, users should inspect the local output directory produced by their version of the script rather than assuming a fixed set of filenames.

---

# 18. Optional AI Insight Report

WatershedKit includes an optional experimental AI-assisted reporting step.

After the standard hydrology report is generated, the workflow can:

1. read the generated DOCX hydrology report;
2. collect associated map images;
3. send the report and images to Google Gemini;
4. request a hydrology-focused engineering interpretation;
5. write a second DOCX containing the AI-generated insights.

A valid Gemini API key is required.

The key is entered interactively at runtime using a secure prompt and is not intended to be stored in source code.

## AI output warning

The AI report is **experimental**.

AI-generated interpretations can hallucinate, misinterpret figures, or change actual catchment parameters in their narrative. Therefore:

> **Never treat the AI-generated report as the authoritative source of catchment parameters.**

Verify numerical values and engineering conclusions against the original generated results and source data before using them in engineering work.

---

# 19. Validation Checklist

Before accepting a watershed result, check the following.

## DEM

- [ ] DEM covers the full study area.
- [ ] DEM resolution is known.
- [ ] DEM CRS is appropriate.
- [ ] DEM elevations look reasonable.
- [ ] No unexpected NoData gaps affect the flow path.

## DEM conditioning

- [ ] Breach distance is appropriate for the terrain and DEM resolution.
- [ ] No artificial connections appear between neighbouring basins.
- [ ] Major rivers remain physically plausible.

## Stream extraction

- [ ] Stream threshold produces a plausible network.
- [ ] Main channels are represented.
- [ ] The network is not excessively dense or sparse.
- [ ] The outlet is connected to the expected stream.

## Outlet

- [ ] Latitude/longitude are correct.
- [ ] Outlet is in WGS84 / EPSG:4326 as expected.
- [ ] Snapped pour point is located on the intended stream.
- [ ] Snap distance has not moved the outlet to an inappropriate branch.

## Watershed

- [ ] Delineated boundary is hydrologically plausible.
- [ ] Catchment area is reasonable compared with available reference data.
- [ ] No neighbouring basin has been unintentionally incorporated.

## Slope parameters

- [ ] Basin slope and channel slope are not confused.
- [ ] Projected metre-based CRS is used for basin slope.
- [ ] Channel slope warnings are reviewed.
- [ ] Longest flow-path/channel data are complete.

## Report

- [ ] Numerical results in the report match the generated result data.
- [ ] Maps correspond to the analyzed catchment.
- [ ] AI-generated interpretation, if used, has been independently verified.

---

# 20. Troubleshooting

## 20.1 The watershed is much larger than expected

One important cause can be excessive DEM breach distance.

A documented example showed that a breach distance of 100 cells created an artificial connection to an adjacent independent river system and increased the catchment area to 2,533.95 km². Reducing the distance to 20 cells removed that connection and produced 2,278.88 km².

### What to do

1. Inspect the conditioned/breached DEM.
2. Inspect the extracted stream network.
3. Look for artificial connections across drainage divides.
4. Reduce the breach distance.
5. Rerun the workflow.
6. Compare the resulting catchment area with trusted reference information.

Do not assume that the documented value of 20 cells is correct for every catchment.

---

## 20.2 The stream network looks wrong

Possible causes include:

- stream threshold too low;
- stream threshold too high;
- inappropriate DEM resolution;
- DEM artefacts;
- excessive breach distance;
- outlet/snap configuration.

Try a different stream threshold and inspect the resulting network before proceeding with watershed delineation.

---

## 20.3 The outlet is not connected to the expected stream

Check:

1. outlet latitude and longitude;
2. outlet coordinate system;
3. extracted stream network;
4. snap distance;
5. DEM projection and units.

The current documented snap distance is 120 map units. Increasing it may help when the outlet is slightly displaced, but a large value can snap to an unintended stream.

---

## 20.4 Average basin slope looks suspicious

Check the DEM CRS.

The basin-slope implementation expects projected cell dimensions in metres. A geographic CRS in degrees can silently produce incorrect slope values.

Also check whether a large proportion of cells near the watershed boundary were excluded because their 3×3 neighbourhood touched NoData.

---

## 20.5 Channel-slope calculation fails

The channel-slope module intentionally raises exceptions for genuine data problems such as:

- missing/invalid CRS;
- empty inputs;
- NoData gaps along the flow path;
- large mismatch between stored stream length and actual geometry length.

The documented tolerance for the stream-length mismatch is 5%.

Check the source stream geometry, its CRS, length attribute, and DEM sampling coverage.

---

## 20.6 `NetworkXNoPath` occurs

This can happen when stream geometries are disconnected, particularly around manually drawn tributary junctions.

Repair the stream topology in QGIS/ArcGIS by snapping or otherwise fixing the geometry connections, then rerun the calculation.

---

## 20.7 The hydrology processing succeeds but DOCX generation fails

A documented failure occurred where the hydrologic calculations succeeded, but DOCX formatting attempted to access an equal-elevation-drop channel-slope result that was not applicable for a catchment larger than 100 km².

The fix was to handle unavailable optional values using `None`/`False` fallback logic during report formatting.

If you encounter a similar problem, distinguish between:

```text
Hydrologic calculation failure
```

and:

```text
Report-generation/formatting failure
```

The two stages can fail independently.

---

# 21. Understanding Common Parameters

| Parameter | What it represents | Main caution |
|---|---|---|
| Breach distance | Search distance in DEM cells for depression breaching | Too large can connect separate drainage systems |
| Stream threshold | Contributing-cell threshold for stream extraction | Strongly affects stream-network density |
| Snap distance | Maximum search distance for moving outlet toward stream | Too large can select the wrong stream |
| Basin area | Area draining to outlet | Check against known/reference basin boundaries |
| Basin length | Straight-line outlet-to-furthest-boundary distance | Do not confuse with channel length |
| Longest flow path | Longest hydrologic travel path toward outlet | Distinct from main channel length |
| Main channel length | Longest upstream stream length from outlet | Does not include overland distance to stream |
| Basin slope | Average terrain slope over catchment | Requires appropriate projected DEM |
| Channel slope (`Sc`) | Equivalent slope of longest flow path/main channel | Not interchangeable with basin slope |
| Length to centroid | Flow-path distance from outlet to stream location closest to centroid | Depends on stream-network connectivity |

---

# 22. Basin Slope vs. Channel Slope

These two parameters should **not** be substituted for one another.

### Basin slope

Describes the general steepness of the entire catchment and is calculated from DEM terrain using Horn's Method.

### Channel slope

Describes the longest flow path/main-channel profile and is calculated using channel elevations and equivalent-slope methods.

The design-parameter reference explicitly lists them separately, and the technical documentation states that they serve different roles in different formulas.

A useful conceptual comparison is:

```text
                CATCHMENT
        ┌─────────────────────┐
        │  /\      /\         │
        │ /  \____/  \        │
        │       \             │
        │        \  MAIN      │
        │         \ CHANNEL   │
        │          \          │
        └───────────\───●─────┘
                     OUTLET

Basin slope:
  Terrain steepness across the whole catchment

Channel slope:
  Longitudinal slope along the longest flow path
```

---

# 23. Reproducible Workflow

For a reproducible analysis, record at minimum:

```text
Project name
DEM filename
DEM resolution
DEM CRS
Breach distance
Stream extraction threshold
Outlet latitude
Outlet longitude
Contour interval
Snap distance
Software/environment version
Date of processing
```

Also preserve the generated results and maps used to make engineering decisions.

If a result is being compared against a published or government reference catchment, record the reference source and the comparison value.

---

# 24. Recommended Workflow for a New Catchment

A practical sequence is:

### Step 1 — Prepare the DEM

Obtain the best available DEM for the study area and confirm its resolution and CRS.

### Step 2 — Define the outlet

Obtain reliable outlet coordinates in WGS84.

### Step 3 — Start with conservative DEM conditioning

Choose a breach distance appropriate to the DEM and terrain.

### Step 4 — Test stream extraction

Use a reasonable starting threshold based on DEM resolution, then visually inspect the network.

### Step 5 — Check the outlet snap

Confirm that the snapped outlet is on the intended stream.

### Step 6 — Delineate the watershed

Inspect the boundary and compare its area and shape with known information where available.

### Step 7 — Review morphometric parameters

Check area, lengths, slopes, relief, drainage characteristics and centroid-related quantities.

### Step 8 — Review warnings

Do not ignore warnings from channel-slope or other parameter calculations.

### Step 9 — Inspect maps

Use the generated maps to verify that the numerical results correspond to physically plausible terrain and drainage.

### Step 10 — Use the report

Review the standard hydrology report first.

### Step 11 — Optionally generate AI insights

If desired, generate the experimental AI report only after the standard results have been checked.

### Step 12 — Independently verify engineering conclusions

Use applicable hydrologic/hydraulic design standards, authoritative data and engineering judgment before using results for design.

---

# 25. Technical References Included with the Project

The supplied technical documentation identifies the following methodological references:

### Horn slope method

Horn, B. K. P. (1981), *Hill Shading and the Reflectance Map*, Proceedings of the IEEE, 69(1), 14–47.

The project documentation identifies this as the source of the weighted 3×3 neighbourhood gradient method used for basin-slope calculation.

### Taylor-Schwarz equivalent slope

Taylor, A. B. and Schwarz, H. E. (1952), *Unit Hydrograph Lag and Peak Flow Related to Basin Characteristics*, Transactions, American Geophysical Union, 33(2).

The project documentation identifies this as the source of the equivalent-slope formulation used for the channel/longest-flow-path analysis and relates it to CWC Synthetic Unit Hydrograph applications.

---

# 26. Quick Start

For experienced users, the minimum workflow is:

```bash
git clone <YOUR-REPOSITORY-URL>
cd WatershedKit

python -m venv .venv
```

Activate the environment:

### Windows

```bat
.venv\Scripts\activate
```

### macOS / Linux

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Set the DEM:

### Windows

```bat
set WATERSHEDKIT_DEM=C:\path\to\your\dem.tif
```

### macOS / Linux

```bash
export WATERSHEDKIT_DEM="/path/to/your/dem.tif"
```

Run:

```bash
python gisops.py
```

Then provide:

```text
Project name
Breach-search distance
Stream extraction threshold
Outlet latitude
Outlet longitude
Contour interval
```

Finally, inspect the generated watershed, streams, maps, parameters and report before accepting the result.

---

# 27. Final Warning

WatershedKit automates a substantial portion of DEM-based watershed analysis, but automation does not remove the need for hydrologic quality control.

In particular:

- **DEM conditioning can change drainage structure.**
- **Stream thresholds can materially change extracted networks.**
- **Outlet snapping can change the delineated basin if configured poorly.**
- **Basin slope and channel slope are different parameters.**
- **NoData and CRS problems can affect slope calculations.**
- **Reference catchment areas should be used where available to validate results.**
- **AI-generated interpretations must be treated as experimental and verified.**

The most important rule is:

> **Always inspect the drainage network and watershed boundary before using calculated parameters for engineering or design decisions.**
