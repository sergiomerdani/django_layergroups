import json
import math
import sys

from django.conf import settings
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .agent_config import (
    ACTION_SCHEMAS,
    ALLOWED_ACTION_TYPES,
    RESPONSE_JSON_CONTRACT,
    WEBGIS_AGENT_INSTRUCTIONS,
    WEBGIS_AGENT_NAME,
)


def get_action_schema(action_type):
    return next(
        (action for action in ACTION_SCHEMAS if action["type"] == action_type),
        {},
    )


def get_agent_tool_parameters(action):
    properties = {}

    if "layer" in action.get("required", []):
        properties["layer"] = {
            "type": "string",
            "description": "Exact layer title or layer name from the map context.",
        }

    if "base_layer" in action.get("required", []):
        properties["base_layer"] = {
            "type": "string",
            "description": "Exact base layer title from the map context.",
        }

    if "value" in action.get("required", []):
        properties["value"] = {
            "type": "boolean",
            "description": "True to enable/show, false to disable/hide.",
        }

    if "mode" in action.get("required", []):
        properties["mode"] = {
            "type": "string",
            "enum": ["2d", "3d"],
            "description": "Use 3d for Cesium globe/terrain mode or 2d for OpenLayers map mode.",
        }

    if "scale" in action.get("required", []):
        properties["scale"] = {
            "type": "number",
            "minimum": 1,
            "description": "Scale denominator. Use 5000 for a map scale of 1:5000.",
        }

    if "limit" in action.get("required", []):
        properties["limit"] = {
            "type": "integer",
            "minimum": 1,
            "maximum": 20,
            "description": "Maximum number of ranked records to return.",
        }

    if "query" in action.get("required", []):
        properties["query"] = {
            "type": "string",
            "description": "Search text or attribute query requested by the user.",
        }

    if "style" in action.get("required", []):
        properties["style"] = {
            "type": "string",
            "description": "Exact style name from the map context.",
        }

    if "parameters" in action.get("required", []):
        properties["parameters"] = {
            "type": "object",
            "description": "Validated tool parameters.",
            "additionalProperties": True,
        }

    return {
        "type": "object",
        "properties": properties,
        "required": action.get("required", []),
        "additionalProperties": False,
    }


def get_agent_tools():
    return [
        {
            "type": "function",
            "name": action["type"],
            "description": action["description"],
            "parameters": get_agent_tool_parameters(action),
        }
        for action in ACTION_SCHEMAS
    ]


def get_response_output_items(response):
    output = getattr(response, "output", None)
    return output or []


def get_function_calls(response):
    return [
        item
        for item in get_response_output_items(response)
        if getattr(item, "type", None) == "function_call"
    ]


def coerce_tool_arguments(raw_arguments):
    if isinstance(raw_arguments, dict):
        return raw_arguments

    if not raw_arguments:
        return {}

    try:
        parsed = json.loads(raw_arguments)
    except (TypeError, json.JSONDecodeError):
        return {}

    return parsed if isinstance(parsed, dict) else {}


def make_frontend_action(action_type, arguments):
    action_schema = get_action_schema(action_type)
    required = set(action_schema.get("required", []))

    action = {"type": action_type}

    if "layer" in required:
        layer = str(arguments.get("layer", "")).strip()
        if not layer:
            raise ValueError(f"{action_type} requires a layer.")
        action["layer"] = layer

    if "base_layer" in required:
        base_layer = str(arguments.get("base_layer", "")).strip()
        if not base_layer:
            raise ValueError(f"{action_type} requires a base_layer.")
        action["base_layer"] = base_layer

    if "value" in required:
        action["value"] = bool(arguments.get("value"))

    if "mode" in required:
        mode = str(arguments.get("mode", "")).strip().lower()
        if mode not in {"2d", "3d"}:
            raise ValueError(f"{action_type} requires mode to be 2d or 3d.")
        action["mode"] = mode

    if "scale" in required:
        try:
            scale = float(arguments.get("scale"))
        except (TypeError, ValueError):
            raise ValueError(f"{action_type} requires a numeric scale.")
        if scale <= 0:
            raise ValueError(f"{action_type} requires a positive scale.")
        action["scale"] = scale

    if "limit" in required:
        try:
            limit = int(arguments.get("limit"))
        except (TypeError, ValueError):
            raise ValueError(f"{action_type} requires a numeric limit.")
        action["limit"] = max(1, min(limit, 20))

    if "query" in required:
        query = str(arguments.get("query", "")).strip()
        if not query:
            raise ValueError(f"{action_type} requires a query.")
        action["query"] = query

    if "style" in required:
        style = str(arguments.get("style", "")).strip()
        if not style:
            raise ValueError(f"{action_type} requires a style.")
        action["style"] = style

    if "parameters" in required:
        parameters = arguments.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ValueError(f"{action_type} requires parameters.")
        action["parameters"] = parameters

    return action


def quote_identifier(identifier):
    return connection.ops.quote_name(identifier)


def get_reference_zone_tables():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
              AND table_schema NOT IN ('pg_catalog', 'information_schema')
              AND (
                table_name ILIKE 'reference_zones_2025'
                OR table_name ILIKE '%reference%zone%2025%'
                OR table_name ILIKE '%reference%zones%2025%'
                OR table_name ILIKE '%reference_zones%'
              )
            ORDER BY
              CASE WHEN table_name ILIKE 'reference_zones_2025' THEN 0 ELSE 1 END,
              table_schema,
              table_name
            """
        )
        return cursor.fetchall()


def get_table_columns(schema_name, table_name):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            [schema_name, table_name],
        )
        return cursor.fetchall()


def choose_reference_zone_columns(columns):
    name_patterns = ("name", "emri", "zone", "zona", "label")
    text_types = ("character", "text")

    name_column = next(
        (
            column_name
            for column_name, data_type in columns
            if any(pattern in column_name.lower() for pattern in name_patterns)
            and any(text_type in data_type for text_type in text_types)
        ),
        None,
    )
    if not name_column:
        name_column = next(
            (
                column_name
                for column_name, data_type in columns
                if any(text_type in data_type for text_type in text_types)
            ),
            None,
        )

    value_column = next(
        (
            column_name
            for column_name, _data_type in columns
            if "2025" in column_name.lower()
        ),
        None,
    )

    return name_column, value_column


def normalize_field_name(field_name):
    return str(field_name or "").strip().lower()


def get_non_geometry_columns(columns):
    return [
        (column_name, data_type)
        for column_name, data_type in columns
        if column_name.lower() not in {"geom", "the_geom", "geometry", "wkb_geometry"}
        and "geometry" not in data_type.lower()
    ]


def resolve_reference_zone_field(requested_field, columns, name_column=None, value_column=None):
    normalized_field = normalize_field_name(requested_field)
    if not normalized_field:
        return None

    if normalized_field in {"name", "zone", "zona", "emri"} and name_column:
        return name_column
    if normalized_field in {"value_2025", "price_2025", "2025"} and value_column:
        return value_column

    for column_name, _data_type in columns:
        if column_name.lower() == normalized_field:
            return column_name

    for column_name, _data_type in columns:
        if normalized_field in column_name.lower():
            return column_name

    return None


def normalize_reference_zone_query_parameters(parameters):
    if not isinstance(parameters, dict):
        parameters = {}

    raw_fields = parameters.get("fields", [])
    if isinstance(raw_fields, str):
        raw_fields = [field.strip() for field in raw_fields.split(",")]
    if not isinstance(raw_fields, list):
        raw_fields = []

    try:
        limit = int(parameters.get("limit", 10))
    except (TypeError, ValueError):
        limit = 10

    sort_direction = str(parameters.get("sort_direction", "desc")).lower()
    if sort_direction not in {"asc", "desc"}:
        sort_direction = "desc"

    return {
        "fields": [str(field).strip() for field in raw_fields if str(field).strip()],
        "sort_by": str(parameters.get("sort_by", "")).strip(),
        "sort_direction": sort_direction,
        "limit": max(1, min(limit, 200)),
        "name_contains": str(parameters.get("name_contains", "")).strip(),
    }


def get_reference_zone_database_query(parameters):
    normalized_parameters = normalize_reference_zone_query_parameters(parameters)

    for schema_name, table_name in get_reference_zone_tables():
        columns = get_table_columns(schema_name, table_name)
        non_geometry_columns = get_non_geometry_columns(columns)
        name_column, value_column = choose_reference_zone_columns(columns)
        requested_fields = normalized_parameters["fields"]

        selected_columns = []
        if requested_fields:
            for field in requested_fields:
                resolved_column = resolve_reference_zone_field(
                    field,
                    non_geometry_columns,
                    name_column,
                    value_column,
                )
                if resolved_column and resolved_column not in selected_columns:
                    selected_columns.append(resolved_column)
        else:
            selected_columns = [column_name for column_name, _ in non_geometry_columns[:30]]

        if not selected_columns:
            continue

        sort_column = resolve_reference_zone_field(
            normalized_parameters["sort_by"],
            non_geometry_columns,
            name_column,
            value_column,
        )
        if not sort_column:
            sort_column = value_column or selected_columns[0]

        where_clauses = []
        query_values = []
        if normalized_parameters["name_contains"] and name_column:
            where_clauses.append(f"{quote_identifier(name_column)}::text ILIKE %s")
            query_values.append(f"%{normalized_parameters['name_contains']}%")

        table_ref = f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"
        select_clause = ", ".join(
            f"{quote_identifier(column)} AS {quote_identifier(column)}"
            for column in selected_columns
        )
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        order_direction = "ASC" if normalized_parameters["sort_direction"] == "asc" else "DESC"
        query_values.append(normalized_parameters["limit"])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {select_clause}
                FROM {table_ref}
                {where_clause}
                ORDER BY {quote_identifier(sort_column)} {order_direction} NULLS LAST
                LIMIT %s
                """,
                query_values,
            )
            rows = cursor.fetchall()

        return {
            "ok": True,
            "source": f"{schema_name}.{table_name}",
            "available_fields": [column_name for column_name, _ in non_geometry_columns],
            "fields": selected_columns,
            "sort_by": sort_column,
            "sort_direction": normalized_parameters["sort_direction"],
            "records": [
                dict(zip(selected_columns, row))
                for row in rows
            ],
        }

    return {
        "ok": False,
        "source": None,
        "records": [],
        "fields": [],
        "available_fields": [],
        "message": (
            "No backend database table for reference_zones_2025 was found. "
            "Import/publish the full dataset to PostGIS if you want full-data queries."
        ),
    }


def get_highest_reference_zones_from_database(limit):
    for schema_name, table_name in get_reference_zone_tables():
        columns = get_table_columns(schema_name, table_name)
        name_column, value_column = choose_reference_zone_columns(columns)
        if not value_column:
            continue

        table_ref = (
            f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"
        )
        name_expr = (
            f"{quote_identifier(name_column)}::text"
            if name_column
            else "'Unnamed zone'"
        )
        value_expr = (
            "CASE WHEN replace(NULLIF("
            f"{quote_identifier(value_column)}::text, ''), ',', '.') "
            "~ '^-?[0-9]+(\\.[0-9]+)?$' THEN replace(NULLIF("
            f"{quote_identifier(value_column)}::text, ''), ',', '.')::double precision "
            "ELSE NULL END"
        )

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT ranked.zone_name AS name, ranked.value_2025
                FROM (
                    SELECT {name_expr} AS zone_name, {value_expr} AS value_2025
                    FROM {table_ref}
                ) ranked
                WHERE ranked.value_2025 IS NOT NULL
                ORDER BY ranked.value_2025 DESC
                LIMIT %s
                """,
                [limit],
            )
            rows = cursor.fetchall()

        if rows:
            return {
                "source": f"{schema_name}.{table_name}",
                "value_column": value_column,
                "name_column": name_column,
                "records": [
                    {"name": row[0] or "Unnamed zone", "value_2025": row[1]}
                    for row in rows
                ],
            }

    return {
        "source": None,
        "records": [],
        "message": (
            "No readable reference_zones_2025 table with a 2025 value column "
            "was found in the configured database."
        ),
    }


def format_backend_price(value):
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return "n/a"


def normalize_reference_zone_number(value):
    if value is None:
        return None

    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None

    return number if math.isfinite(number) else None


def get_reference_zone_property_value(properties, patterns):
    for key, value in properties.items():
        normalized_key = str(key).lower()
        if any(pattern in normalized_key for pattern in patterns):
            return value
    return None


def get_reference_zone_record_from_properties(properties):
    value_2025 = normalize_reference_zone_number(
        get_reference_zone_property_value(properties, ["2025"])
    )
    if value_2025 is None:
        return None

    name = get_reference_zone_property_value(
        properties,
        ["name", "emri", "zone", "zona", "label"],
    )
    return {
        "name": str(name or "Unnamed zone"),
        "value_2025": value_2025,
    }


def get_reference_zone_context_query(map_context, parameters):
    normalized_parameters = normalize_reference_zone_query_parameters(parameters)
    records = map_context.get("reference_zones_2025_records", [])
    if not isinstance(records, list):
        records = []

    normalized_records = []
    available_fields = set()
    for record in records:
        if not isinstance(record, dict):
            continue

        properties = record.get("properties")
        if not isinstance(properties, dict):
            properties = record

        cleaned = {
            str(key): value
            for key, value in properties.items()
            if key not in {"geometry"} and not isinstance(value, (dict, list))
        }
        if "name" not in cleaned and record.get("name"):
            cleaned["name"] = record.get("name")
        if "value_2025" not in cleaned and record.get("value_2025") is not None:
            cleaned["value_2025"] = record.get("value_2025")
        if "value_2023" not in cleaned and record.get("value_2023") is not None:
            cleaned["value_2023"] = record.get("value_2023")
        if "value_2019" not in cleaned and record.get("value_2019") is not None:
            cleaned["value_2019"] = record.get("value_2019")

        if normalized_parameters["name_contains"]:
            text = " ".join(str(value) for value in cleaned.values())
            if normalized_parameters["name_contains"].lower() not in text.lower():
                continue

        available_fields.update(cleaned.keys())
        normalized_records.append(cleaned)

    available_fields = sorted(available_fields)
    fields = normalized_parameters["fields"] or available_fields[:30]
    resolved_fields = []
    for field in fields:
        resolved_field = next(
            (
                available_field
                for available_field in available_fields
                if available_field.lower() == field.lower()
                or field.lower() in available_field.lower()
            ),
            None,
        )
        if resolved_field and resolved_field not in resolved_fields:
            resolved_fields.append(resolved_field)

    sort_by = normalized_parameters["sort_by"]
    resolved_sort = next(
        (
            available_field
            for available_field in available_fields
            if available_field.lower() == sort_by.lower()
            or sort_by.lower() in available_field.lower()
        ),
        None,
    )
    if not resolved_sort:
        resolved_sort = "value_2025" if "value_2025" in available_fields else None

    if resolved_sort:
        normalized_records.sort(
            key=lambda record: (
                (
                    0,
                    normalize_reference_zone_number(record.get(resolved_sort)),
                )
                if normalize_reference_zone_number(record.get(resolved_sort)) is not None
                else (1, str(record.get(resolved_sort, "")))
            ),
            reverse=normalized_parameters["sort_direction"] == "desc",
        )

    limited_records = normalized_records[: normalized_parameters["limit"]]

    return {
        "ok": bool(limited_records),
        "source": "loaded reference_zones_2025 map context",
        "available_fields": available_fields,
        "fields": resolved_fields,
        "sort_by": resolved_sort,
        "sort_direction": normalized_parameters["sort_direction"],
        "records": [
            {field: record.get(field) for field in resolved_fields}
            for record in limited_records
        ],
        "message": (
            "Loaded reference_zones_2025 records were queried from the map context."
            if limited_records
            else "No loaded reference_zones_2025 records were available in the map context."
        ),
    }


def lonlat_to_tile(lon, lat, zoom):
    lat = max(min(lat, 85.05112878), -85.05112878)
    zoom_factor = 2**zoom
    x_tile = int((lon + 180.0) / 360.0 * zoom_factor)
    lat_rad = math.radians(lat)
    y_tile = int(
        (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi)
        / 2.0
        * zoom_factor
    )
    max_tile = zoom_factor - 1
    return max(0, min(x_tile, max_tile)), max(0, min(y_tile, max_tile))


def get_tile_coords_for_extent(extent_4326, zoom, max_tiles=24):
    if not isinstance(extent_4326, list) or len(extent_4326) != 4:
        return []

    min_lon, min_lat, max_lon, max_lat = [float(value) for value in extent_4326]
    x_min, y_max = lonlat_to_tile(min_lon, min_lat, zoom)
    x_max, y_min = lonlat_to_tile(max_lon, max_lat, zoom)

    if x_min > x_max:
        x_min, x_max = x_max, x_min
    if y_min > y_max:
        y_min, y_max = y_max, y_min

    coords = [
        (zoom, x, y)
        for x in range(x_min, x_max + 1)
        for y in range(y_min, y_max + 1)
    ]
    return coords[:max_tiles]


def get_highest_reference_zones_from_vector_tiles(map_context, limit):
    try:
        import requests
        from mapbox_vector_tile import decode
        from urllib3.exceptions import InsecureRequestWarning
    except ImportError as exc:
        return {
            "source": "https://tiles.kaktu.al/data/reference_zones_2025/{z}/{x}/{y}.pbf",
            "records": [],
            "message": (
                "The backend needs mapbox-vector-tile installed to read "
                f"reference_zones_2025 vector tiles. Import error: {exc}"
            ),
        }

    zoom = int(round(float(map_context.get("zoom") or 12)))
    zoom = max(8, min(zoom, 14))
    tile_coords = get_tile_coords_for_extent(map_context.get("extent_4326"), zoom)
    records = []

    for z, x, y in tile_coords:
        url = f"https://tiles.kaktu.al/data/reference_zones_2025/{z}/{x}/{y}.pbf"
        try:
            requests.packages.urllib3.disable_warnings(
                category=InsecureRequestWarning
            )
            response = requests.get(url, timeout=12, verify=False)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            decoded_tile = decode(response.content)
        except Exception:
            continue

        for layer_data in decoded_tile.values():
            for feature in layer_data.get("features", []):
                properties = feature.get("properties", {})
                record = get_reference_zone_record_from_properties(properties)
                if record:
                    records.append(record)

    deduped = {}
    for record in records:
        key = f"{record['name']}:{record['value_2025']}"
        deduped[key] = record

    ranked = sorted(
        deduped.values(),
        key=lambda record: record["value_2025"],
        reverse=True,
    )[:limit]

    return {
        "source": "reference_zones_2025 vector tiles in current map extent",
        "records": ranked,
        "message": (
            "No readable reference_zones_2025 vector-tile features were found "
            "in the current map extent."
        ),
    }


def get_highest_reference_zones_from_context(map_context, limit):
    records = map_context.get("reference_zones_2025_records", [])
    if not isinstance(records, list):
        records = []

    normalized_records = []
    for record in records:
        if not isinstance(record, dict):
            continue
        value_2025 = normalize_reference_zone_number(
            record.get("value_2025") or record.get("value2025")
        )
        if value_2025 is None:
            continue
        normalized_records.append(
            {
                "name": str(record.get("name") or "Unnamed zone"),
                "value_2025": value_2025,
            }
        )

    deduped = {}
    for record in normalized_records:
        deduped[f"{record['name']}:{record['value_2025']}"] = record

    ranked = sorted(
        deduped.values(),
        key=lambda record: record["value_2025"],
        reverse=True,
    )[:limit]

    return {
        "source": "loaded reference_zones_2025 map context",
        "records": ranked,
        "message": (
            "No loaded reference_zones_2025 records were available in the "
            "current map context. Turn on the layer, zoom to the area, and ask again."
        ),
    }


def execute_backend_agent_tool(tool_name, arguments, map_context=None):
    if tool_name == "query_reference_zones":
        parameters = arguments.get("parameters", {})
        result = get_reference_zone_database_query(parameters)
        if not result.get("records"):
            result = get_reference_zone_context_query(map_context or {}, parameters)
        return result

    if tool_name == "get_highest_reference_zones":
        limit = max(1, min(int(arguments.get("limit", 5)), 20))
        result = get_highest_reference_zones_from_database(limit)
        if not result.get("records"):
            result = get_highest_reference_zones_from_context(
                map_context or {},
                limit,
            )
        if not result.get("records"):
            result = get_highest_reference_zones_from_vector_tiles(
                map_context or {},
                limit,
            )
        records = result.get("records", [])

        if not records:
            return {
                "ok": False,
                "message": result.get("message", "No reference zones were found."),
                "records": [],
            }

        ranked_lines = [
            f"{index}. {record['name']}: {format_backend_price(record['value_2025'])} / m2"
            for index, record in enumerate(records, start=1)
        ]

        return {
            "ok": True,
            "source": result.get("source"),
            "records": records,
            "message": (
                "Highest 2025 reference zone prices from "
                f"{result.get('source')}:\n" + "\n".join(ranked_lines)
            ),
        }

    raise ValueError(f"{tool_name} is not a backend WebGIS action.")


def execute_agent_tool(tool_name, arguments, map_context=None):
    if tool_name not in ALLOWED_ACTION_TYPES:
        raise ValueError(f"{tool_name} is not an allowed WebGIS action.")

    action_schema = get_action_schema(tool_name)
    if not action_schema.get("frontend_only", True):
        return {
            "action": None,
            "output": execute_backend_agent_tool(tool_name, arguments, map_context),
        }

    action = make_frontend_action(tool_name, arguments)
    return {
        "action": action,
        "output": {
            "ok": True,
            "action": action,
            "message": f"Queued frontend action: {tool_name}",
        },
    }


@api_view(["GET"])
def health_check(request):
    return Response({"message": "Custom API is working"})


@api_view(["GET"])
def openai_key_status(request):
    api_key = settings.OPENAI_API_KEY
    is_configured = bool(api_key and api_key != "put_your_openai_api_key_here")

    return Response({"openai_api_key_configured": is_configured})


@api_view(["GET"])
def agent_manifest(request):
    return Response(
        {
            "name": WEBGIS_AGENT_NAME,
            "model": settings.OPENAI_MODEL,
            "actions": ACTION_SCHEMAS,
            "chat_endpoint": "/api/custom/chat/",
        }
    )


def normalize_ai_payload(raw_text):
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return {"reply": raw_text, "actions": []}

    reply = str(payload.get("reply", "")).strip()
    actions = []

    for action in payload.get("actions", []):
        if not isinstance(action, dict):
            continue

        action_type = action.get("type")
        if action_type not in ALLOWED_ACTION_TYPES:
            continue

        actions.append(
            {
                "type": action_type,
                "layer": str(action.get("layer", "")).strip(),
                "value": action.get("value"),
                "query": str(action.get("query", "")).strip(),
                "style": str(action.get("style", "")).strip(),
                "parameters": action.get("parameters", {}),
            }
        )

    return {"reply": reply or "Done.", "actions": actions}


@csrf_exempt
@api_view(["POST"])
def chat(request):
    message = str(request.data.get("message", "")).strip()
    map_context = request.data.get("map_context", {})

    if not message:
        return Response({"error": "Message is required"}, status=400)

    api_key = settings.OPENAI_API_KEY
    if not api_key or api_key == "put_your_openai_api_key_here":
        return Response(
            {"error": "OPENAI_API_KEY is not configured on the backend"},
            status=503,
        )

    try:
        from openai import APIStatusError, OpenAI
    except ImportError as exc:
        return Response(
            {
                "error": (
                    "The OpenAI package could not be imported by the Python "
                    f"environment running Django. Python: {sys.executable}. "
                    f"Import error: {exc}"
                )
            },
            status=503,
        )

    client = OpenAI(api_key=api_key)
    model = settings.OPENAI_MODEL

    instructions = f"{WEBGIS_AGENT_INSTRUCTIONS} {RESPONSE_JSON_CONTRACT}"
    input_messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        f"Map context JSON: {json.dumps(map_context)}\n\n"
                        f"User message: {message}"
                    ),
                }
            ],
        }
    ]
    actions = []

    try:
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=input_messages,
            tools=get_agent_tools(),
        )

        function_calls = get_function_calls(response)
        if function_calls:
            tool_outputs = []

            for function_call in function_calls:
                tool_name = getattr(function_call, "name", "")
                call_id = getattr(function_call, "call_id", "")
                arguments = coerce_tool_arguments(
                    getattr(function_call, "arguments", {})
                )
                tool_result = execute_agent_tool(tool_name, arguments, map_context)
                if tool_result.get("action"):
                    actions.append(tool_result["action"])
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(tool_result["output"]),
                    }
                )

            response = client.responses.create(
                model=model,
                instructions=instructions,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=get_agent_tools(),
            )
    except APIStatusError as exc:
        message = str(exc)
        if exc.status_code == 401:
            message = (
                "OpenAI rejected the backend API key. Check OPENAI_API_KEY in "
                "the Django .env file, make sure the key is active, and restart "
                "the Django server after changing it."
            )
        return Response({"error": message}, status=exc.status_code)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)
    except Exception as exc:
        return Response({"error": str(exc)}, status=502)

    reply = str(getattr(response, "output_text", "") or "").strip()
    if not reply:
        reply = "Done." if actions else "I could not create an action for that request."

    return Response({"reply": reply, "actions": actions})
