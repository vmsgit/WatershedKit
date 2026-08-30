"""
catchment_maps.py
-------------------
One function per map type, each with an explicit, self-documenting
signature -- built on top of the generic engine in gis_map_utils.py.

Import these directly into main.py:

    from catchment_maps import (
        generate_outlet_map,
        generate_stream_map,
        generate_longest_flow_path_map,
        generate_main_channel_map,
        generate_centroid_map,
        generate_contour_map,
    )

    generate_stream_map("catchment.shp", "streams.shp", "outputs/map2_streams.png")

Every function returns the output path on success.
"""

from .gis_maps_utils import build_map


def _catchment_layer(catchment_boundary, label="Catchment Boundary"):
    return dict(path=catchment_boundary, geom="polygon", label=label,
                color="black", linewidth=1.5, zorder=1)


def generate_outlet_map(catchment_boundary, outlet_shp, output_path,
                          title="Catchment Boundary and Outlet Point"):
    """Map 1: catchment boundary + outlet point."""
    build_map(
        layers=[
            _catchment_layer(catchment_boundary),
            dict(path=outlet_shp, geom="point", label="Outlet Point",
                  color="red", marker="^", markersize=10, zorder=3),
        ],
        title=title,
        output_path=output_path,
    )
    return output_path


def generate_stream_map(catchment_boundary, stream_shp, output_path,
                          title="Catchment and Stream Network",
                          stream_order_col=None, stream_color="blue"):
    """
    Map 2: catchment boundary + stream network.

    stream_order_col : optional attribute column name (e.g. "stream_ord")
                        to color streams by order using a colorbar.
                        If None, all streams are drawn in a single color.
    """
    if stream_order_col:
        stream_layer = dict(path=stream_shp, geom="line",
                              value_column=stream_order_col, cmap="Blues",
                              linewidth=2, zorder=2)
        colorbar_label = "Stream Order"
    else:
        stream_layer = dict(path=stream_shp, geom="line", label="Stream Network",
                              color=stream_color, linewidth=1.5, zorder=2)
        colorbar_label = None

    build_map(
        layers=[_catchment_layer(catchment_boundary), stream_layer],
        title=title,
        output_path=output_path,
        colorbar_label=colorbar_label,
    )
    return output_path


def generate_longest_flow_path_map(catchment_boundary, lfp_shp, output_path,
                                     title="Catchment Boundary and Longest Flow Path"):
    """Map 3: catchment boundary + longest flow path."""
    build_map(
        layers=[
            _catchment_layer(catchment_boundary),
            dict(path=lfp_shp, geom="line", label="Longest Flow Path",
                  color="blue", linewidth=2, zorder=2),
        ],
        title=title,
        output_path=output_path,
    )
    return output_path


def generate_main_channel_map(catchment_boundary, main_channel_shp, output_path,
                                title="Catchment Boundary and Main Channel"):
    """Map 4: catchment boundary + main channel."""
    build_map(
        layers=[
            _catchment_layer(catchment_boundary),
            dict(path=main_channel_shp, geom="line", label="Main Channel",
                  color="navy", linewidth=2, zorder=2),
        ],
        title=title,
        output_path=output_path,
    )
    return output_path


def generate_centroid_map(catchment_boundary, centroid_stream_shp, centroid_shp, output_path,
                            title="Catchment Boundary and Length to Centroid"):
    """Map 5: catchment boundary + length-to-centroid stream + centroid point."""
    build_map(
        layers=[
            _catchment_layer(catchment_boundary),
            dict(path=centroid_stream_shp, geom="line", label="Length to Centroid",
                  color="green", linewidth=2, zorder=2),
            dict(path=centroid_shp, geom="point", label="Centroid",
                  color="orange", marker="o", markersize=9, zorder=3),
        ],
        title=title,
        output_path=output_path,
    )
    return output_path


def generate_contour_map(catchment_boundary, contour_shp, output_path,
                           title="Catchment Boundary and Contours",
                           elevation_col="elev", label_contours=True,
                           cmap="terrain"):
    """
    Map 6: catchment boundary + contour lines, colored by elevation.

    elevation_col   : attribute column holding elevation values.
    label_contours  : if True, annotate each contour line with its value.
    """
    contour_layer = dict(path=contour_shp, geom="line", value_column=elevation_col,
                           cmap=cmap, linewidth=1, zorder=2)
    if label_contours:
        contour_layer["label_column"] = elevation_col
        contour_layer["label_fontsize"] = 6

    build_map(
        layers=[_catchment_layer(catchment_boundary), contour_layer],
        title=title,
        output_path=output_path,
        colorbar_label="Elevation (m)",
    )
    return output_path