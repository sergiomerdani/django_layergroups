from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests

BASE_URL = "http://localhost:8080/geoserver/rest/layergroups"
BASE_URL2 = "http://localhost:8080/geoserver/rest/layers"
AUTH = ("admin", "geoserver")  # Replace with your credentials
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

@api_view(["GET", "POST"])
def layergroup_list(request):
    """
    GET: Fetch all layer groups.
    POST: Create a new layer group with parameters (name, layer, style).
    """
    if request.method == "GET":
        # Fetch all layer groups
        response = requests.get(BASE_URL, headers=HEADERS, auth=AUTH)
        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        return Response({"error": response.text}, status=response.status_code)

    elif request.method == "POST":
        # Extract parameters from the request data
        name = request.data.get("name")
        layer = request.data.get("layer")

        # Validate the required parameters
        if not all([name, layer]):
            return Response(
                {"error": "Missing required parameters: 'name' or 'layer'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch the layer details to get the associated style
        layer_url = f"{BASE_URL2}/{layer}.json"  # URL to fetch layer details
        layer_response = requests.get(layer_url, headers=HEADERS, auth=AUTH)
        print(layer_url)
        if layer_response.status_code != 200:
            return Response(
                {"error": f"Failed to fetch layer details for '{layer}'."},
                status=layer_response.status_code
            )

        # Extract the default style from the layer details
        layer_data = layer_response.json()
        default_style = layer_data.get("layer", {}).get("defaultStyle", {}).get("name")

        if not default_style:
            return Response(
                {"error": f"Layer '{layer}' does not have an associated default style."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build the payload for GeoServer
        payload = {
            "layerGroup": {
                "name": name,
                "layers": {
                    "layer": [layer]
                },
                "styles": {
                    "style": [default_style]  # Automatically fetched style
                },
                "bounds": {
                    "minx": 126530.81806662556,
                    "maxx": 4427129.1730813645,
                    "miny": 699492.3966753744,
                    "maxy": 4701182.713534636,
                    "crs": "EPSG:6870"
                }
            }
        }

        # Send the payload to GeoServer
        response = requests.post(BASE_URL, json=payload, headers=HEADERS, auth=AUTH)
        if response.status_code in (200, 201):
            return Response({"message": "Layer group created successfully."}, status=status.HTTP_201_CREATED)
        return Response({"error": response.text}, status=response.status_code)



@api_view(["GET", "PUT", "DELETE"])
def layergroup_detail(request, name):
    """
    GET: Fetch a single layer group by name from GeoServer
    PUT: Update an existing layer group in GeoServer
    DELETE: Delete a layer group from GeoServer
    """
    url = f"{BASE_URL}/{name}"

    try:
        if request.method == "GET":
            response = requests.get(url, headers=HEADERS, auth=AUTH)
            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            return Response({"error": response.text}, status=response.status_code)

        elif request.method == "PUT":
            print("Request Data:", request.data)  # Debug incoming request

            # Fetch the current layer group configuration
            response = requests.get(url, headers=HEADERS, auth=AUTH)
            if response.status_code != 200:
                return Response({"error": "Layer group not found."}, status=status.HTTP_404_NOT_FOUND)

            current_config = response.json()["layerGroup"]
            print("Current Config:", current_config)  # Debug existing config

            # Extract and fallback for optional fields
            title = request.data.get("title", current_config.get("title"))
            single_layer = request.data.get("layer")
            single_style = request.data.get("style")

            # Handle layers and styles
            layers = {"layer": [single_layer]} if single_layer else current_config.get("layers", {}).get("layer", [])
            styles = {"style": [single_style]} if single_style else current_config.get("styles", {}).get("style", [])

            # Build the updated payload
            updated_payload = {
                "layerGroup": {
                    "name": current_config["name"],  # Name remains unchanged
                    "title": title,
                    "mode": current_config["mode"],  # Mode remains unchanged
                    "layers": layers,
                    "styles": styles,
                    "bounds": current_config["bounds"]  # Bounds remain unchanged
                }
            }

            # Debug updated payload
            print("Updated Payload:", updated_payload)

            # Send the PUT request to GeoServer
            update_response = requests.put(url, json=updated_payload, headers=HEADERS, auth=AUTH)
            if update_response.status_code in (200, 201):
                return Response({"message": "Layer group updated successfully."}, status=status.HTTP_200_OK)
            return Response({"error": update_response.text}, status=update_response.status_code)


        elif request.method == "DELETE":
            response = requests.delete(url, headers=HEADERS, auth=AUTH)
            if response.status_code in (200, 204):
                return Response({"message": "Layer group deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
            return Response({"error": response.text}, status=response.status_code)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)