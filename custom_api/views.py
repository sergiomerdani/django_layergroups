import json
import sys

from django.conf import settings
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

    if "value" in action.get("required", []):
        properties["value"] = {
            "type": "boolean",
            "description": "True to enable/show, false to disable/hide.",
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

    if "value" in required:
        action["value"] = bool(arguments.get("value"))

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


def execute_agent_tool(tool_name, arguments):
    if tool_name not in ALLOWED_ACTION_TYPES:
        raise ValueError(f"{tool_name} is not an allowed WebGIS action.")

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
                tool_result = execute_agent_tool(tool_name, arguments)
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
