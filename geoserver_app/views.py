from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests

BASE_URL = "http://localhost:8080/geoserver/rest/layergroups"
AUTH = ("admin", "geoserver")  # Replace with your credentials
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

@api_view(["GET", "POST"])
def layergroup_list(request):
    """
    GET: Fetch all layer groups from GeoServer
    POST: Create a new layer group in GeoServer
    """
    if request.method == "GET":
        try:
            response = requests.get(BASE_URL, headers=HEADERS, auth=AUTH)
            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            return Response({"error": response.text}, status=response.status_code)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == "POST":
        try:
            response = requests.post(BASE_URL, json=request.data, headers=HEADERS, auth=AUTH)
            if response.status_code in (200, 201):
                return Response({"message": "Layer group created successfully."}, status=status.HTTP_201_CREATED)
            return Response({"error": response.text}, status=response.status_code)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            response = requests.put(url, json=request.data, headers=HEADERS, auth=AUTH)
            if response.status_code in (200, 201):
                return Response({"message": "Layer group updated successfully."}, status=status.HTTP_200_OK)
            return Response({"error": response.text}, status=response.status_code)

        elif request.method == "DELETE":
            response = requests.delete(url, headers=HEADERS, auth=AUTH)
            if response.status_code in (200, 204):
                return Response({"message": "Layer group deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
            return Response({"error": response.text}, status=response.status_code)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)