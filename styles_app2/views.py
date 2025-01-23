import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .utils import (
    list_styles,
    get_style,
    create_geoserver_style,
    update_style,
    delete_style
)

@api_view(["GET", "POST"])
def styles_list_create_view(request):
    """
    GET  -> List all styles
    POST -> Create a new style
    """
    if request.method == "GET":
        # List all styles
        try:
            data = list_styles()
            return Response(data)
        except requests.exceptions.HTTPError as err:
            return Response({"error": str(err)}, status=500)

    elif request.method == "POST":
        """
        Create a new style in GeoServer.
        """
        style_data = request.data  # Expecting JSON with style details
        try:
            geoserver_response = create_geoserver_style(style_data)
            if geoserver_response['success']:
                return Response(
                    {"message": "Style created successfully in GeoServer."},
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {"error": geoserver_response['message']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET", "PUT", "DELETE"])
def style_detail_view(request, style_name):
    """
    GET    -> Retrieve details of a style
    PUT    -> Update style (SLD body)
    DELETE -> Delete style
    """
    
    
    if request.method == "GET":
        try:
            data = get_style(style_name)
            return Response(data)
        except requests.exceptions.HTTPError as err:
            return Response({"error": str(err)}, status=500)

    elif request.method == "PUT":
        sld_body = request.data.get("sld_body", None)
        if not sld_body:
            return Response({"error": "Missing 'sld_body' to update style."}, status=400)

        try:
            update_style(style_name, sld_body)
            return Response({"message": "Style updated successfully"})
        except requests.exceptions.HTTPError as err:
            return Response({"error": str(err)}, status=500)

    elif request.method == "DELETE":
        try:
            delete_style(style_name)
            return Response({"message": "Style deleted successfully"})
        except requests.exceptions.HTTPError as err:
            return Response({"error": str(err)}, status=500)
