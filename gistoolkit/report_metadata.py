PARAMETER_METADATA = {

    # ========================================================
    # CATCHMENT CHARACTERISTICS
    # ========================================================

    "catchment_area_m2": {
        "name": "Catchment Area",
        "symbol": "A",
        "unit": "km²",
        "description": (
            "Area enclosed by the catchment boundary."
        ),
        "section": "Catchment Characteristics",
        "formatter": "area_km2",
    },

    "catchment_perimeter_m": {
        "name": "Catchment Perimeter",
        "symbol": "P",
        "unit": "km",
        "description": (
            "Total length of the catchment boundary."
        ),
        "section": "Catchment Characteristics",
        "formatter": "km_from_m",
    },

    "basin_length": {
        "name": "Basin Length",
        "symbol": "Lb",
        "unit": "km",
        "description": (
            "Length of the basin measured along the principal "
            "basin direction."
        ),
        "section": "Catchment Characteristics",
        "formatter": "km_from_m",
    },

    "length_to_centroid_m": {
        "name": "Length to Centroid",
        "symbol": "Lc",
        "unit": "km",
        "description": (
            "Distance from the outlet to the catchment centroid."
        ),
        "section": "Catchment Characteristics",
        "formatter": "km_from_m",
    },


    # ========================================================
    # DRAINAGE NETWORK
    # ========================================================

    "outlet_stream_order": {
        "name": "Maximum Stream Order",
        "symbol": "Ω",
        "unit": "",
        "description": (
            "Highest stream order identified within the drainage network."
        ),
        "section": "Drainage Network",
        "formatter": "integer",
    },

    "all_streams_length": {
        "name": "Total Stream Length",
        "symbol": "Lu",
        "unit": "km",
        "description": (
            "Total length of the identified stream network."
        ),
        "section": "Drainage Network",
        "formatter": "km_from_m",
    },

    "drainage_density_km": {
        "name": "Drainage Density",
        "symbol": "Dd",
        "unit": "km/km²",
        "description": (
            "Ratio of total stream length to catchment area."
        ),
        "section": "Drainage Network",
        "formatter": "decimal_3",
    },

    "stream_frequency_km2": {
        "name": "Stream Frequency",
        "symbol": "Fs",
        "unit": "streams/km²",
        "description": (
            "Number of stream segments per unit catchment area."
        ),
        "section": "Drainage Network",
        "formatter": "decimal_3",
    },

    "constant_channel_maintenance_km": {
        "name": "Constant of Channel Maintenance",
        "symbol": "C",
        "unit": "km²/km",
        "description": (
            "Inverse of drainage density."
        ),
        "section": "Drainage Network",
        "formatter": "decimal_3",
    },

    "infiltration_number_km": {
        "name": "Infiltration Number",
        "symbol": "If",
        "unit": "",
        "description": (
            "Morphometric parameter derived from drainage density "
            "and stream frequency."
        ),
        "section": "Drainage Network",
        "formatter": "decimal_3",
    },


    # ========================================================
    # RELIEF
    # ========================================================

    "watershed_max_elev": {
        "name": "Maximum Catchment Elevation",
        "symbol": "Hmax",
        "unit": "m",
        "description": "Maximum elevation within the catchment.",
        "section": "Relief Characteristics",
        "formatter": "decimal_2",
    },

    "watershed_min_elev": {
        "name": "Minimum Catchment Elevation",
        "symbol": "Hmin",
        "unit": "m",
        "description": "Minimum elevation within the catchment.",
        "section": "Relief Characteristics",
        "formatter": "decimal_2",
    },

    "basin_relief_m": {
        "name": "Basin Relief",
        "symbol": "R",
        "unit": "m",
        "description": (
            "Difference between the maximum and minimum "
            "elevation of the catchment."
        ),
        "section": "Relief Characteristics",
        "formatter": "decimal_2",
    },

    "relief_ratio_m": {
        "name": "Relief Ratio",
        "symbol": "Rh",
        "unit": "",
        "description": (
            "Ratio relating basin relief to basin length."
        ),
        "section": "Relief Characteristics",
        "formatter": "decimal_4",
    },

    "ruggedness_number_km": {
        "name": "Ruggedness Number",
        "symbol": "Rn",
        "unit": "",
        "description": (
            "Morphometric parameter combining basin relief "
            "and drainage density."
        ),
        "section": "Relief Characteristics",
        "formatter": "decimal_4",
    },

    "true_basin_slope_percent": {
        "name": "True Average Basin Slope",
        "symbol": "S",
        "unit": "%",
        "description": (
            "Average basin slope calculated using the implemented "
            "terrain-slope method."
        ),
        "section": "Relief Characteristics",
        "formatter": "percent",
    },


    # ========================================================
    # MORPHOMETRIC PARAMETERS
    # ========================================================

    "form_factor": {
        "name": "Form Factor",
        "symbol": "F",
        "unit": "",
        "description": (
            "Ratio relating catchment area and basin length."
        ),
        "section": "Morphometric Analysis",
        "formatter": "decimal_4",
    },

    "elongation_ratio": {
        "name": "Elongation Ratio",
        "symbol": "Re",
        "unit": "",
        "description": (
            "Ratio describing the shape of the catchment."
        ),
        "section": "Morphometric Analysis",
        "formatter": "decimal_4",
    },

    "circulatory_ratio": {
        "name": "Circulatory Ratio",
        "symbol": "Rc",
        "unit": "",
        "description": (
            "Ratio describing the circularity of the catchment."
        ),
        "section": "Morphometric Analysis",
        "formatter": "decimal_4",
    },

    "compactness_coefficient": {
        "name": "Compactness Coefficient",
        "symbol": "Cc",
        "unit": "",
        "description": (
            "Parameter describing the compactness of the catchment."
        ),
        "section": "Morphometric Analysis",
        "formatter": "decimal_4",
    },
}