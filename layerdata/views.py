from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests

GEOSERVER_URL = "http://localhost:8080/geoserver"
AUTH = ("admin", "geoserver")  # Replace with actual credentials

@api_view(["GET"])
def get_layer_details(request, layer_name):
    """
    Fetch layer details including attributes and unique values for each attribute.
    """
    try:
        # GeoServer WFS GetFeature URL (fetch JSON data)
        wfs_url = f"{GEOSERVER_URL}/finiq_ws/ows?service=WFS&version=1.0.0&request=GetFeature&typeName={layer_name}&maxFeatures=1000&outputFormat=application/json"

        # Fetch JSON layer data from GeoServer
        response = requests.get(wfs_url, auth=AUTH)
        response.raise_for_status()
        data = response.json()

        # Extract attributes from first feature
        if "features" not in data or not data["features"]:
            return Response({"error": "No features found in the layer"}, status=status.HTTP_404_NOT_FOUND)

        first_feature = data["features"][0]["properties"]
        attributes = []

        # Extract attributes and get unique values
        for attr_name in first_feature.keys():
            unique_values = fetch_unique_values(wfs_url, attr_name)
            attributes.append({
                "name": attr_name,
                "unique_values": unique_values
            })

        return Response({
            "layer": layer_name,
            "attributes": attributes
        }, status=status.HTTP_200_OK)

    except requests.RequestException as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def fetch_unique_values(wfs_url, attribute):
    """
    Fetch unique values for a given attribute using WFS GetFeature JSON.
    """
    try:
        response = requests.get(wfs_url, auth=AUTH)
        response.raise_for_status()
        data = response.json()

        unique_values = set()
        for feature in data.get("features", []):
            value = feature["properties"].get(attribute)
            if value is not None:
                unique_values.add(value)

        return list(unique_values)
    
    except requests.RequestException:
        return []
