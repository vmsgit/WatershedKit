"""
gis_map_utils.py
------------------
Reusable engine for producing publication-style catchment maps from vector
layers (polygon / line / point), all already in a projected CRS.

Shared map chrome handled once here:
  - Title              -> top-left
  - North arrow         -> top-right
  - Legend              -> bottom-left  (or colorbar for value-based layers)
  - Scale bar (m / km)  -> bottom-right
  - X/Y ticks in DMS (degrees-minutes-seconds), computed from the projected
    coordinates via pyproj, while the plot itself stays in the projected CRS.

Each individual map is then just a short list of "layer specs" (see
make_all_maps.py) describing which file to draw and how -- no repeated
plotting boilerplate.

Requirements:
    pip install geopandas matplotlib matplotlib-scalebar pyproj shapely
"""

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib_scalebar.scalebar import ScaleBar
from pyproj import Transformer
import sys
import csv
from pathlib import Path
import numpy as np
import pandas as pd



# ============================== DMS AXES =================================

def dms_string(deg: float, is_lat: bool) -> str:
    """Convert a decimal degree value to a DMS string, e.g. 19°58'12"N."""
    hemisphere = ("N" if deg >= 0 else "S") if is_lat else ("E" if deg >= 0 else "W")
    deg = abs(deg)
    d = int(deg)
    m_float = (deg - d) * 60
    m = int(m_float)
    s = (m_float - m) * 60
    return f"{d}\u00b0{m:02d}'{s:04.1f}\"{hemisphere}"


def _make_dms_formatter(transformer, fixed_coord, axis):
    def _formatter(value, _pos):
        if axis == "x":
            lon, lat = transformer.transform(value, fixed_coord)
            return dms_string(lon, is_lat=False)
        else:
            lon, lat = transformer.transform(fixed_coord, value)
            return dms_string(lat, is_lat=True)
    return FuncFormatter(_formatter)


def apply_dms_axes(ax, crs):
    """Reformat existing projected-CRS tick locations into DMS lon/lat labels."""
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    x_center = (xlim[0] + xlim[1]) / 2
    y_center = (ylim[0] + ylim[1]) / 2

    ax.xaxis.set_major_formatter(_make_dms_formatter(transformer, y_center, "x"))
    ax.yaxis.set_major_formatter(_make_dms_formatter(transformer, x_center, "y"))
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=8)
    plt.setp(ax.get_yticklabels(), fontsize=8)
    ax.set_xlabel("Longitude", fontsize=10)
    ax.set_ylabel("Latitude", fontsize=10)


# ============================ MAP CHROME ==================================

def add_north_arrow(ax, x=0.94, y=0.94, size=0.06):
    ax.annotate(
        "N",
        xy=(x, y), xycoords="axes fraction",
        xytext=(x, y - size), textcoords="axes fraction",
        ha="center", va="center",
        fontsize=14, fontweight="bold",
        arrowprops=dict(arrowstyle="-|>", color="black", lw=2),
    )


def add_scale_bar(ax):
    """Scale bar assuming projected-CRS units of metres; auto m <-> km."""
    scalebar = ScaleBar(
        dx=1, units="m", dimension="si-length",
        location="lower right", box_alpha=0.7,
        pad=0.5, border_pad=0.5, scale_loc="top",
    )
    ax.add_artist(scalebar)


# ============================ LAYER DRAWING ================================

def load_layer(path, target_crs):
    """Read a vector layer and reproject to target_crs if needed."""
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        raise ValueError(f"Layer '{path}' has no CRS defined.")
    if gdf.crs != target_crs:
        gdf = gdf.to_crs(target_crs)
    return gdf


def draw_layer(ax, spec, target_crs):
    """
    Draw one layer according to its spec and return:
      (legend_handle_or_None, mappable_or_None)
    mappable is returned only for column-colored layers (-> colorbar).

    spec keys:
      path         : file path (required)
      geom         : "polygon" | "line" | "point"           (required)
      label        : legend label                            (optional)
      color        : matplotlib color                        (default "black")
      linewidth    : for polygon/line                        (default 1.5)
      marker       : for point                                (default "o")
      markersize   : for point (points^2 area)                (default 8)
      fill         : bool, for polygon -> filled vs boundary  (default False)
      alpha        : transparency                             (default 1.0)
      value_column : column name -> color by value (cmap)     (optional)
      cmap         : colormap name if value_column is set     (default "terrain")
      zorder       : draw order                                (default 2)
      label_column : column name -> annotate each feature      (optional)
      label_fontsize: fontsize for label_column annotations     (default 7)
    """
    gdf = load_layer(spec["path"], target_crs)
    geom = spec["geom"]
    color = spec.get("color", "black")
    lw = spec.get("linewidth", 1.5)
    alpha = spec.get("alpha", 1.0)
    zorder = spec.get("zorder", 2)
    label = spec.get("label")
    value_col = spec.get("value_column")
    cmap = spec.get("cmap", "terrain")

    mappable = None
    handle = None

    if geom == "polygon":
        if spec.get("fill", False):
            gdf.plot(ax=ax, color=color, alpha=alpha, edgecolor=spec.get("edgecolor", "black"),
                      linewidth=lw, zorder=zorder)
            handle = Patch(facecolor=color, edgecolor=spec.get("edgecolor", "black"), label=label)
        else:
            gdf.boundary.plot(ax=ax, edgecolor=color, linewidth=lw, zorder=zorder)
            handle = Line2D([0], [0], color=color, lw=lw, label=label)

    elif geom == "line":
        if value_col:
            plot_out = gdf.plot(ax=ax, column=value_col, cmap=cmap, linewidth=lw,
                                  alpha=alpha, zorder=zorder)
            mappable = plot_out.collections[-1] if plot_out.collections else None
        else:
            gdf.plot(ax=ax, color=color, linewidth=lw, alpha=alpha, zorder=zorder)
            handle = Line2D([0], [0], color=color, lw=lw, label=label)

    elif geom == "point":
        marker = spec.get("marker", "o")
        markersize = spec.get("markersize", 8)
        gdf.plot(ax=ax, color=color, marker=marker, markersize=markersize ** 2,
                  alpha=alpha, zorder=zorder)
        handle = Line2D([0], [0], marker=marker, color="w", markerfacecolor=color,
                          markersize=markersize, label=label)
    else:
        raise ValueError(f"Unknown geom type: {geom}")

    # Optional per-feature labels (e.g. contour elevations)
    if spec.get("label_column"):
        fs = spec.get("label_fontsize", 7)
        for _, row in gdf.iterrows():
            pt = row.geometry.representative_point()
            ax.annotate(str(row[spec["label_column"]]), xy=(pt.x, pt.y),
                        fontsize=fs, color=color, zorder=zorder + 1)

    return handle, mappable


# ============================ MAP BUILDER ==================================

def build_map(layers, title, output_path, target_crs=None,
              figsize=(10, 8), dpi=300, colorbar_label=None):
    """
    layers       : list of layer spec dicts (see draw_layer docstring)
    title        : map title (top-left)
    output_path  : PNG output path
    target_crs   : CRS to plot in; defaults to the CRS of the first layer
    colorbar_label: if a layer uses value_column, label for the colorbar
    """
    if target_crs is None:
        target_crs = gpd.read_file(layers[0]["path"]).crs

    fig, ax = plt.subplots(figsize=figsize)

    handles = []
    mappable = None
    for spec in layers:
        h, m = draw_layer(ax, spec, target_crs)
        if h is not None:
            handles.append(h)
        if m is not None:
            mappable = m

    ax.set_aspect("equal")

    # Title (top-left)
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", pad=12)

    # North arrow (top-right)
    add_north_arrow(ax)

    # Legend (bottom-left) or colorbar for value-based layers
    if handles:
        ax.legend(handles=handles, loc="lower left", frameon=True, fontsize=9)
    if mappable is not None:
        cbar = fig.colorbar(mappable, ax=ax, shrink=0.5, pad=0.03, location="right")
        cbar.set_label(colorbar_label or "", fontsize=9)

    # Scale bar (bottom-right)
    add_scale_bar(ax)

    # DMS axes
    apply_dms_axes(ax, target_crs)

    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.5)

    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    print(f"Map saved to: {output_path}")
    plt.close(fig)


#=====================================================================================
#Export Hyspometric curve png - Start
#====================================================================================
def read_hypsometric_csv(path: Path):
    """Parse the metadata (# comment) lines and the data table separately."""
    metadata = {}
    data_start_line = 0
 
    with open(path, "r", newline="") as f:
        lines = f.readlines()
 
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            # Format: # key,value
            content = stripped.lstrip("#").strip()
            parts = content.split(",", 1)
            if len(parts) == 2:
                key, value = parts[0].strip(), parts[1].strip()
                # Try to cast numeric values to float
                try:
                    value = float(value)
                except ValueError:
                    pass
                metadata[key] = value
        else:
            data_start_line = i
            break
 
    df = pd.read_csv(path, skiprows=data_start_line)
    df.columns = [c.strip() for c in df.columns]
    return metadata, df
 
 
def classify_stage_color(stage_text: str) -> str:
    """Pick a curve color based on the erosional stage, if available."""
    if not stage_text:
        return "#2E5C8A"
    stage_text = stage_text.lower()
    if "young" in stage_text or "convex" in stage_text:
        return "#C0392B"   # red - young/convex
    if "mature" in stage_text or "equilibrium" in stage_text:
        return "#27AE60"   # green - mature/S-shaped
    if "old" in stage_text or "concave" in stage_text or "monadnock" in stage_text:
        return "#2E5C8A"   # blue - old/concave
    return "#2E5C8A"
 
 
def plot_hypsometric_curve(metadata: dict, df: pd.DataFrame, output_path: Path, projectname: str = None):
    x = df["relative_area"].to_numpy()
    y = df["relative_height"].to_numpy()
 
    stage = str(metadata.get("stage_classification", "")).strip()
    hi = metadata.get("HI_curve_integral", metadata.get("HI_relief_ratio", None))
    elev_min = metadata.get("elev_min_m")
    elev_max = metadata.get("elev_max_m")
    elev_mean = metadata.get("elev_mean_m")
 
    curve_color = classify_stage_color(stage)
 
    fig, ax = plt.subplots(figsize=(7, 7), dpi=150)
 
    # Hypsometric curve
    ax.plot(x, y, color=curve_color, linewidth=2.2, label="Hypsometric curve")
 
    # Fill under the curve to visually represent the hypsometric integral (area)
    ax.fill_between(x, y, 0, color=curve_color, alpha=0.15)
 
    # Reference 1:1 line (straight line from (0,1) to (1,0)) for comparison
    ax.plot([0, 1], [1, 0], color="gray", linestyle="--", linewidth=1, alpha=0.6,
             label="Equilibrium reference (1:1)")
 
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Relative area (a/A)", fontsize=12)
    ax.set_ylabel("Relative height (h/H)", fontsize=12)
 
    title = "Hypsometric Curve"
    if projectname:
        title += f" — {projectname}"
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
 
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.set_aspect("equal", adjustable="box")
 
    # Annotation box with key stats
    annotation_lines = []
    if hi is not None:
        annotation_lines.append(f"Hypsometric Integral (HI): {hi:.3f}")
    if elev_min is not None and elev_max is not None:
        annotation_lines.append(f"Elevation range: {elev_min:.1f} – {elev_max:.1f} m")
    if elev_mean is not None:
        annotation_lines.append(f"Mean elevation: {elev_mean:.1f} m")
    if stage:
        annotation_lines.append(f"Stage: {stage}")
 
    if annotation_lines:
        ax.text(
            0.97, 0.97, "\n".join(annotation_lines),
            transform=ax.transAxes,
            fontsize=9.5,
            va="top", ha="right",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor="gray", alpha=0.9),
        )
 
    ax.legend(loc="lower left", fontsize=9, frameon=True)
 
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved hypsometric curve plot to: {output_path}")
 
 
def generate_hypsometric_plot(input_csv, output_png=None, projectname=None):
    """
    Main entry point to call from your pipeline (e.g. main.py).
 
    Parameters
    ----------
    input_csv : str or Path
        Path to the hypsometric curve result CSV.
    output_png : str or Path, optional
        Path to save the PNG. If omitted, saves next to input_csv with
        the same base name (e.g. foo.csv -> foo.png).
 
    Returns
    -------
    Path
        The path to the saved PNG file.
    """
    input_csv = Path(input_csv)
    output_png = Path(output_png) if output_png else input_csv.with_suffix(".png")
 
    metadata, df = read_hypsometric_csv(input_csv)
    plot_hypsometric_curve(metadata, df, output_png, projectname=projectname)
    return output_png
 
 
def main():
    if len(sys.argv) < 2:
        print("Usage: python plot_hypsometric_curve.py <input_csv> [output_png]")
        sys.exit(1)
 
    input_csv = sys.argv[1]
    output_png = sys.argv[2] if len(sys.argv) >= 3 else None
    generate_hypsometric_plot(input_csv, output_png)
 
 
if __name__ == "__main__":
    main()
#=====================================================================================
#Export Hyspometric curve png - End
#====================================================================================