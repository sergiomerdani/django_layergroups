WEBGIS_AGENT_NAME = "WebGIS Agent"

WEBGIS_AGENT_INSTRUCTIONS = (
    "You are a concise GIS agent inside a WebGIS application. "
    "You help users inspect layers, layer groups, styles, features, map navigation, "
    "and spatial analysis workflows. When the user asks for a map operation, call "
    "one of the available tools. Do not invent layer names. Use only layer names, "
    "style names, and app capabilities that appear in the provided map context. "
    "If a request is unclear or unsafe, ask for the missing detail instead of "
    "calling a tool."
)

ACTION_SCHEMAS = [
    {
        "type": "zoom_to_tirana",
        "description": "Zoom the map to the center of Tirana.",
        "frontend_only": True,
    },
    {
        "type": "zoom_to_layer",
        "description": "Zoom the map to the extent of a named layer.",
        "frontend_only": True,
        "required": ["layer"],
    },
    {
        "type": "zoom_to_place",
        "description": "Search a place name with Nominatim and zoom the map to that place.",
        "frontend_only": True,
        "required": ["query"],
    },
    {
        "type": "toggle_layer_visibility",
        "description": "Turn a named layer on or off.",
        "frontend_only": True,
        "required": ["layer", "value"],
    },
    {
        "type": "set_map_mode",
        "description": "Switch the map display mode between 2D OpenLayers and 3D Cesium.",
        "frontend_only": True,
        "required": ["mode"],
    },
    {
        "type": "set_base_layer",
        "description": "Change the active base layer, for example OSM, CartoDarkAll, Satellite Imagery, or Ortofoto 2015 20cm.",
        "frontend_only": True,
        "required": ["base_layer"],
    },
    {
        "type": "set_elevation_tool",
        "description": "Turn the 3D terrain elevation cursor readout on or off.",
        "frontend_only": True,
        "required": ["value"],
    },
    {
        "type": "set_terrain",
        "description": "Turn Cesium 3D world terrain on or off.",
        "frontend_only": True,
        "required": ["value"],
    },
    {
        "type": "set_map_scale",
        "description": "Set the OpenLayers map scale denominator, for example 5000 for 1:5000.",
        "frontend_only": True,
        "required": ["scale"],
    },
    {
        "type": "select_layer",
        "description": "Make a named layer the active layer in the frontend.",
        "frontend_only": True,
        "required": ["layer"],
    },
    {
        "type": "search_layer_features",
        "description": "Ask the frontend to search features in a layer.",
        "frontend_only": True,
        "required": ["layer", "query"],
    },
    {
        "type": "set_layer_style",
        "description": "Apply a named style to a named layer.",
        "frontend_only": True,
        "required": ["layer", "style"],
    },
    {
        "type": "run_site_selection",
        "description": "Run the existing site-selection workflow with validated parameters.",
        "frontend_only": False,
        "required": ["parameters"],
    },
]

ALLOWED_ACTION_TYPES = {action["type"] for action in ACTION_SCHEMAS}

RESPONSE_JSON_CONTRACT = (
    "Return a short user-facing message. Tool calls are converted to frontend "
    "actions by the backend, so do not print raw JSON unless the user asks for it."
)
