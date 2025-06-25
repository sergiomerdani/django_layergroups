from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests

AUTH = ("admin", "geoserver")
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


GEOSERVER_SETTINGS = {
    "url": "http://localhost:8080/geoserver",
    "workspace": "roles_test",  # Replace with your actual workspace
    "datastore": "postgres",
    "auth": ("admin", "geoserver"),  # Replace with your credentials
}

def construct_base_layer_url(workspace, datastore):
    """
    Construct the base URL for GeoServer featuretypes.
    """
    return f"http://localhost:8080/geoserver/rest/workspaces/{workspace}/datastores/{datastore}/featuretypes"





@api_view(["GET", "POST"])
def layer_list(request, workspace, datastore):
    """
    GET: Fetch all layers (feature types) from a specific datastore in a workspace with their geometry types.
    POST: Create a new feature type (layer) in a specific datastore.
    """
    BASE_LAYER_URL = construct_base_layer_url(workspace, datastore)

    if request.method == "GET":
        try:
            # Fetch all feature types from the datastore
            response = requests.get(BASE_LAYER_URL + ".json", headers=HEADERS, auth=AUTH)
            response.raise_for_status()
            feature_types = response.json().get("featureTypes", {}).get("featureType", [])

            layers_with_geometry = []

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
                        "org.locationtech.jts.geom.Geometry": "Geometry",
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
            # Debug received payload
            print("Received Payload:", request.data)

            # Extract feature type details from the request payload
            feature_data = request.data
            if not feature_data:
                return Response({"error": "Feature type data is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Ensure required fields are present
            required_fields = ["name", "geometry"]
            missing_fields = [field for field in required_fields if field not in feature_data]
            if missing_fields:
                return Response(
                    {"error": f"Missing required fields: {', '.join(missing_fields)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Map geometry type to GeoServer-compatible bindings
            geometry_mapping = {
                "Point": "org.locationtech.jts.geom.Point",
                "LineString": "org.locationtech.jts.geom.LineString",
                "Polygon": "org.locationtech.jts.geom.Polygon",
                "MultiPoint": "org.locationtech.jts.geom.MultiPoint",
                "MultiLineString": "org.locationtech.jts.geom.MultiLineString",
                "MultiPolygon": "org.locationtech.jts.geom.MultiPolygon",
                "Geometry": "org.locationtech.jts.geom.Geometry",
                
                
            }

            geometry_binding = geometry_mapping.get(feature_data["geometry"])
            if not geometry_binding:
                return Response(
                    {"error": f"Invalid geometry type: {feature_data['geometry']}. Allowed types are: {', '.join(geometry_mapping.keys())}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Construct dynamic payload
            payload = {
                "featureType": {
                    "name": feature_data["name"],
                    "nativeBoundingBox": {
                        "minx": -180,
                        "maxx": 180,
                        "miny": -85.06,
                        "maxy": 85.06,
                        "crs": "EPSG:3857"
                    },
                    "srs": "EPSG:3857",
                    "attributes": {
                        "attribute": [
                            {"name": "id", "binding": "java.lang.Integer"},
                            {"name": "geom", "binding": geometry_binding}
                        ]
                    }
                }
            }

            # Debug the payload to be sent
            print("Payload for GeoServer:", payload)

            # Send POST request to GeoServer
            response = requests.post(BASE_LAYER_URL, json=payload, headers=HEADERS, auth=AUTH)

            # Debug response
            print("Response Status Code:", response.status_code)
            print("Response Text:", response.text)
            if response.status_code in (200, 201):
                return Response({"message": "Feature type created successfully."}, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"error": response.json() if response.headers.get("Content-Type") == "application/json" else response.text},
                    status=response.status_code
                )

        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(["GET", "PUT"])
def layer_detail(request, workspace, datastore, layer_name):
    """
    GET: Fetch detailed information about a specific layer (feature type) from a datastore in a workspace.
    PUT: Add new attributes (fields) to an existing layer while preserving id and geometry.
    """
    BASE_LAYER_URL = construct_base_layer_url(workspace, datastore)

    if request.method == "GET":
        try:
            # Construct the URL for the specific feature type
            feature_url = f"{BASE_LAYER_URL}/{layer_name}.json"

            # Fetch the feature type details
            response = requests.get(feature_url, headers=HEADERS, auth=AUTH)
            response.raise_for_status()

            # Return the detailed JSON response
            feature_details = response.json()
            return Response(feature_details, status=status.HTTP_200_OK)

        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == "PUT":
        try:
            # Extract the modification details from the request payload
            modification_data = request.data

            if not modification_data:
                return Response({"error": "The request payload is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Extract fields from the payload
            new_name = modification_data.get("name")
            new_title = modification_data.get("title")
            updated_attributes = modification_data.get("attributes", [])

            if not new_name:
                return Response({"error": "The 'name' field is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Construct the URL for the specific feature type
            feature_url = f"{BASE_LAYER_URL}/{layer_name}.json"

            # Fetch the current layer details
            response = requests.get(feature_url, headers=HEADERS, auth=AUTH)
            response.raise_for_status()
            current_feature_type = response.json()["featureType"]

            # Get existing attributes
            existing_attributes = current_feature_type.get("attributes", {}).get("attribute", [])
            if isinstance(existing_attributes, dict):
                existing_attributes = [existing_attributes]

            # Prepare the attributes for the update
            updated_attribute_list = []
            for attr in existing_attributes:
                # Check if the attribute needs to be updated
                updated_attr = next((a for a in updated_attributes if a["name"] == attr["name"]), None)
                if updated_attr:
                    # Update the attribute's type or other fields if specified
                    updated_attribute_list.append({
                        "name": updated_attr.get("new_name", attr["name"]),  # Use the new name if provided
                        "binding": updated_attr.get("binding", attr["binding"]),  # Use the new type if provided
                        "minOccurs": attr.get("minOccurs", 0),
                        "maxOccurs": attr.get("maxOccurs", 1),
                        "nillable": attr.get("nillable", True),
                    })
                else:
                    # Keep the attribute unchanged
                    updated_attribute_list.append(attr)

            # Add any completely new attributes from the payload
            for new_attr in updated_attributes:
                if new_attr["name"] not in [attr["name"] for attr in existing_attributes]:
                    updated_attribute_list.append({
                        "name": new_attr["name"],
                        "binding": new_attr["binding"],
                        "minOccurs": new_attr.get("minOccurs", 0),
                        "maxOccurs": new_attr.get("maxOccurs", 1),
                        "nillable": new_attr.get("nillable", True),
                    })

            # Construct the updated payload
            updated_feature_type = {
                "featureType": {
                    "name": new_name,
                    "nativeName": current_feature_type["nativeName"],  # Keep nativeName unchanged
                    "title": new_title if new_title else current_feature_type.get("title", new_name),  # Update title if provided
                    "srs": current_feature_type["srs"],
                    "nativeBoundingBox": current_feature_type["nativeBoundingBox"],
                    "latLonBoundingBox": current_feature_type["latLonBoundingBox"],
                    "attributes": {"attribute": updated_attribute_list},  # Add or update attributes
                }
            }

            # Send PUT request to update the layer
            update_response = requests.put(feature_url, json=updated_feature_type, headers=HEADERS, auth=AUTH)
            if update_response.status_code in (200, 204):
                return Response({"message": "Layer updated successfully."}, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": update_response.json() if update_response.headers.get("Content-Type") == "application/json" else update_response.text},
                    status=update_response.status_code,
                )

        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





