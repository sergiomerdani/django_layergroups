from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests

BASE_LAYER_URL = "http://localhost:8080/geoserver/rest/workspaces/finiq_ws/datastores/finiqi_data/featuretypes"
AUTH = ("admin", "geoserver")
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
workspace = "finiq_ws"
datastore = "finiqi_data"


@api_view(["GET", "POST"])
def layer_list(request, workspace, datastore):
    """
    GET: Fetch all layers (feature types) from a specific datastore in a workspace with their geometry types.
    POST: Create a new feature type (layer) in a specific datastore.
    """
    

    if request.method == "GET":
        try:
            # Fetch all feature types from the datastore
            response = requests.get(BASE_LAYER_URL + ".json", headers=HEADERS, auth=AUTH)
            response.raise_for_status()
            feature_types = response.json().get("featureTypes", {}).get("featureType", [])

            layers_with_geometry = []

            # Loop through each feature type to fetch geometry type
            for feature in feature_types:
                layer_name = feature.get("name")
                feature_url = feature.get("href")

                if not feature_url:
                    layers_with_geometry.append({"name": layer_name, "geometry_type": "Unknown"})
                    continue

                # Fetch detailed feature type information
                feature_response = requests.get(feature_url, headers=HEADERS, auth=AUTH)
                if feature_response.status_code != 200:
                    layers_with_geometry.append({"name": layer_name, "geometry_type": "Unknown"})
                    continue

                feature_details = feature_response.json().get("featureType", {})
                attributes = feature_details.get("attributes", {}).get("attribute", [])

                # Ensure attributes is a list
                if isinstance(attributes, dict):
                    attributes = [attributes]

                # Extract geometry type
                geometry_attribute = next(
                    (attr for attr in attributes if attr.get("name") == "geom"),
                    None
                )

                if geometry_attribute:
                    geometry_binding = geometry_attribute.get("binding")
                    geometry_mapping = {
                        "org.locationtech.jts.geom.Point": "Point",
                        "org.locationtech.jts.geom.LineString": "Line",
                        "org.locationtech.jts.geom.Polygon": "Polygon",
                        "org.locationtech.jts.geom.MultiPoint": "MultiPoint",
                        "org.locationtech.jts.geom.MultiLineString": "MultiLine",
                        "org.locationtech.jts.geom.MultiPolygon": "MultiPolygon",
                    }
                    geometry_type = geometry_mapping.get(geometry_binding, "Unknown Geometry Type")
                else:
                    geometry_type = "Unknown"

                # Append the layer name and geometry type to the result list
                layers_with_geometry.append({"name": layer_name, "geometry_type": geometry_type})

            return Response(layers_with_geometry, status=status.HTTP_200_OK)

        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == "POST":
        try:
            # Extract feature type details from the request payload
            feature_data = request.data
            if not feature_data:
                return Response({"error": "Feature type data is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Ensure required fields are present
            required_fields = ["name", "nativeName", "srs", "nativeBoundingBox", "latLonBoundingBox"]
            missing_fields = [field for field in required_fields if field not in feature_data]
            if missing_fields:
                return Response(
                    {"error": f"Missing required fields: {', '.join(missing_fields)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Build payload for GeoServer
            payload = {
                "featureType": {
                    "name": feature_data["name"],
                    "nativeName": feature_data["nativeName"],
                    "title": feature_data.get("title", feature_data["name"]),
                    "srs": feature_data["srs"],
                    "nativeBoundingBox": feature_data["nativeBoundingBox"],
                    "latLonBoundingBox": feature_data["latLonBoundingBox"]
                }
            }

            # Send POST request to GeoServer
            response = requests.post(BASE_LAYER_URL, json=payload, headers=HEADERS, auth=AUTH)
            if response.status_code in (200, 201):
                return Response({"message": "Feature type created successfully."}, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"error": response.json() if response.headers.get("Content-Type") == "application/json" else response.text},
                    status=response.status_code
                )

        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    """
    Fetch all layers (feature types) from a specific datastore in a workspace with their geometry types.
    """

    try:
        # Fetch all feature types from the datastore
        response = requests.get(BASE_LAYER_URL, headers=HEADERS, auth=AUTH)
        response.raise_for_status()
        feature_types = response.json().get("featureTypes", {}).get("featureType", [])

        layers_with_geometry = []

        # Loop through each feature type to fetch geometry type
        for feature in feature_types:
            layer_name = feature.get("name")
            feature_url = feature.get("href")

            if not feature_url:
                layers_with_geometry.append({"name": layer_name, "geometry_type": "Unknown"})
                continue

            # Fetch detailed feature type information
            feature_response = requests.get(feature_url, headers=HEADERS, auth=AUTH)
            if feature_response.status_code != 200:
                layers_with_geometry.append({"name": layer_name, "geometry_type": "Unknown"})
                continue

            feature_details = feature_response.json().get("featureType", {})
            attributes = feature_details.get("attributes", {}).get("attribute", [])

            # Ensure attributes is a list
            if isinstance(attributes, dict):
                attributes = [attributes]

            # Extract geometry type
            geometry_attribute = next(
                (attr for attr in attributes if attr.get("name") == "geom"),
                None
            )

            if geometry_attribute:
                geometry_binding = geometry_attribute.get("binding")
                geometry_mapping = {
                    "org.locationtech.jts.geom.Point": "Point",
                    "org.locationtech.jts.geom.LineString": "Line",
                    "org.locationtech.jts.geom.Polygon": "Polygon",
                    "org.locationtech.jts.geom.MultiPoint": "MultiPoint",
                    "org.locationtech.jts.geom.MultiLineString": "MultiLine",
                    "org.locationtech.jts.geom.MultiPolygon": "MultiPolygon",
                }
                geometry_type = geometry_mapping.get(geometry_binding, "Unknown Geometry Type")
            else:
                geometry_type = "Unknown"

            # Append the layer name and geometry type to the result list
            layers_with_geometry.append({"name": layer_name, "geometry_type": geometry_type})

        return Response(layers_with_geometry, status=status.HTTP_200_OK)
    except requests.RequestException as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def layer_detail(request, workspace, datastore, layer_name):
    """
    Fetch detailed information about a specific layer (feature type) from a datastore in a workspace.
    """
    try:
        # Construct the URL for the specific feature type
        feature_url = f"http://localhost:8080/geoserver/rest/workspaces/{workspace}/datastores/{datastore}/featuretypes/{layer_name}.json"

        # Fetch the feature type details
        response = requests.get(feature_url, headers=HEADERS, auth=AUTH)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Return the detailed JSON response
        feature_details = response.json()
        return Response(feature_details, status=status.HTTP_200_OK)

    except requests.RequestException as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
